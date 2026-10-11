"""Session lifecycle business rules. No HTTP or FastAPI imports belong here."""
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from backend.models import (
    TERMINAL_STATUSES,
    Interruption,
    SessionStatus,
    utc_now,
)
from backend.models import Session as SessionModel
from backend.schemas import (
    HistoryResponse,
    HistorySummary,
    PauseRequest,
    SessionCreate,
    SessionHistoryItem,
)
from backend.services.exceptions import (
    InvalidTransitionError,
    PersistenceError,
    SessionNotFoundError,
    SessionServiceError,
)

# --- Business-rule constants -------------------------------------------------

# A session paused MORE than this many times is interrupted (the 4th pause crosses it).
INTERRUPTION_PAUSE_LIMIT: int = 3

# Overdue if elapsed time exceeds 110% of the scheduled duration (integer math, no floats).
OVERDUE_ALLOWANCE_NUMERATOR: int = 110
OVERDUE_ALLOWANCE_DENOMINATOR: int = 100

# A pause that stays unresumed this long is finalized as abandoned.
ABANDONMENT_TIMEOUT_ENV_VAR: str = "ABANDONMENT_TIMEOUT_MINUTES"
DEFAULT_ABANDONMENT_TIMEOUT_MINUTES: int = 30


def _read_abandonment_timeout() -> timedelta:
    raw_value = os.getenv(ABANDONMENT_TIMEOUT_ENV_VAR, str(DEFAULT_ABANDONMENT_TIMEOUT_MINUTES))
    try:
        minutes = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{ABANDONMENT_TIMEOUT_ENV_VAR} must be a positive integer, got {raw_value!r}."
        ) from exc
    if minutes <= 0:
        raise ValueError(f"{ABANDONMENT_TIMEOUT_ENV_VAR} must be positive, got {minutes}.")
    return timedelta(minutes=minutes)


ABANDONMENT_TIMEOUT: timedelta = _read_abandonment_timeout()

_ZERO: timedelta = timedelta(0)


# --- Pure rule helpers (unit-test these directly) ----------------------------


def overdue_threshold(scheduled_minutes: int) -> timedelta:
    """Maximum elapsed time that still counts as on time: scheduled duration x 110%."""
    return (
        timedelta(minutes=scheduled_minutes)
        * OVERDUE_ALLOWANCE_NUMERATOR
        // OVERDUE_ALLOWANCE_DENOMINATOR
    )


def is_overdue(scheduled_minutes: int, elapsed: timedelta) -> bool:
    """Strictly greater than the threshold: exactly 110% is still on time."""
    return elapsed > overdue_threshold(scheduled_minutes)


def abandonment_deadline(pause_time: datetime) -> datetime:
    return pause_time + ABANDONMENT_TIMEOUT


# --- Internal helpers --------------------------------------------------------


def _resolve_now(now: datetime | None) -> datetime:
    """Default to the current UTC time; reject naive datetimes passed by callers."""
    if now is None:
        return utc_now()
    if now.tzinfo is None:
        raise ValueError("`now` must be timezone-aware.")
    return now.astimezone(timezone.utc)


@contextmanager
def _transaction(db: DbSession) -> Iterator[None]:
    """Commit on success; roll back on any error. DB errors become PersistenceError."""
    try:
        yield
        db.commit()
    except SessionServiceError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise PersistenceError("A database error occurred while saving the session.") from exc
    except BaseException:
        db.rollback()
        raise


def _fetch_session(db: DbSession, session_id: int) -> SessionModel:
    """Load a session with its interruptions, always refreshing any cached copy."""
    statement = (
        select(SessionModel)
        .where(SessionModel.id == session_id)
        .options(selectinload(SessionModel.interruptions))
        .execution_options(populate_existing=True)
    )
    try:
        session = db.execute(statement).scalars().one_or_none()
    except SQLAlchemyError as exc:
        raise PersistenceError("A database error occurred while loading the session.") from exc
    if session is None:
        raise SessionNotFoundError(session_id)
    return session


def _open_interruption(session: SessionModel) -> Interruption | None:
    """The most recent pause that has not been resumed, if any."""
    for interruption in reversed(session.interruptions):
        if interruption.resume_time is None:
            return interruption
    return None


def _try_transition(
    db: DbSession,
    session_id: int,
    expected: SessionStatus,
    new_status: SessionStatus,
    **column_values: Any,
) -> bool:
    """Atomic compare-and-swap on status. Returns False if another request changed it first."""
    result = cast(
        CursorResult[Any],
        db.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id, SessionModel.status == expected)
            .values(status=new_status, **column_values)
            .execution_options(synchronize_session=False)
        ),
    )
    return result.rowcount == 1


def _transition_or_raise(
    db: DbSession,
    session_id: int,
    expected: SessionStatus,
    new_status: SessionStatus,
    action: str,
    **column_values: Any,
) -> None:
    if not _try_transition(db, session_id, expected, new_status, **column_values):
        raise InvalidTransitionError(
            f"Cannot {action} session {session_id}: it was modified by another request."
        )


def _require_status(session: SessionModel, expected: SessionStatus, action: str) -> None:
    """Reject the action unless the session is in the single status that permits it."""
    if session.status is expected:
        return
    if session.status in TERMINAL_STATUSES:
        raise InvalidTransitionError(
            f"Cannot {action} session {session.id}: it is in terminal state "
            f"'{session.status.value}'."
        )
    raise InvalidTransitionError(
        f"Cannot {action} session {session.id}: status is '{session.status.value}', "
        f"expected '{expected.value}'."
    )


def _finalize_abandonment_if_due(db: DbSession, session: SessionModel, now: datetime) -> bool:
    """Mark a timed-out paused session as abandoned. Returns True if finalization was attempted."""
    if session.status is not SessionStatus.PAUSED:
        return False
    open_pause = _open_interruption(session)
    if open_pause is None:
        return False
    deadline = abandonment_deadline(open_pause.pause_time)
    if now < deadline:
        return False
    with _transaction(db):
        _try_transition(
            db,
            session.id,
            SessionStatus.PAUSED,
            SessionStatus.ABANDONED,
            end_time=deadline,
        )
    return True


def _get_current_session(db: DbSession, session_id: int, now: datetime) -> SessionModel:
    """Fetch a session, first applying lazy abandonment so callers see its true state."""
    session = _fetch_session(db, session_id)
    if _finalize_abandonment_if_due(db, session, now):
        session = _fetch_session(db, session_id)
    return session


# --- Lifecycle operations ----------------------------------------------------


def create_session(
    db: DbSession, payload: SessionCreate, now: datetime | None = None
) -> SessionModel:
    created_at = _resolve_now(now)
    session = SessionModel(
        title=payload.title,
        goal=payload.goal,
        scheduled_duration=payload.duration,
        status=SessionStatus.SCHEDULED,
        created_at=created_at,
    )
    with _transaction(db):
        db.add(session)
        db.flush()
    return _fetch_session(db, session.id)


def start_session(db: DbSession, session_id: int, now: datetime | None = None) -> SessionModel:
    current_time = _resolve_now(now)
    session = _get_current_session(db, session_id, current_time)
    _require_status(session, SessionStatus.SCHEDULED, "start")
    with _transaction(db):
        _transition_or_raise(
            db,
            session_id,
            SessionStatus.SCHEDULED,
            SessionStatus.ACTIVE,
            "start",
            start_time=current_time,
        )
    return _fetch_session(db, session_id)


def pause_session(
    db: DbSession, session_id: int, payload: PauseRequest, now: datetime | None = None
) -> SessionModel:
    """Pause an active session. The 4th pause makes it `interrupted` (terminal)."""
    current_time = _resolve_now(now)
    session = _get_current_session(db, session_id, current_time)
    _require_status(session, SessionStatus.ACTIVE, "pause")
    with _transaction(db):
        # The status swap takes the write lock, so the count below cannot go stale.
        _transition_or_raise(
            db, session_id, SessionStatus.ACTIVE, SessionStatus.PAUSED, "pause"
        )
        db.add(
            Interruption(session_id=session_id, reason=payload.reason, pause_time=current_time)
        )
        db.flush()
        pause_count = db.scalar(
            select(func.count())
            .select_from(Interruption)
            .where(Interruption.session_id == session_id)
        )
        if pause_count is not None and pause_count > INTERRUPTION_PAUSE_LIMIT:
            _transition_or_raise(
                db,
                session_id,
                SessionStatus.PAUSED,
                SessionStatus.INTERRUPTED,
                "pause",
                end_time=current_time,
            )
    return _fetch_session(db, session_id)


def resume_session(db: DbSession, session_id: int, now: datetime | None = None) -> SessionModel:
    current_time = _resolve_now(now)
    session = _get_current_session(db, session_id, current_time)
    _require_status(session, SessionStatus.PAUSED, "resume")
    open_pause = _open_interruption(session)
    if open_pause is None:
        raise InvalidTransitionError(
            f"Cannot resume session {session_id}: no unresumed pause is recorded."
        )
    with _transaction(db):
        _transition_or_raise(
            db, session_id, SessionStatus.PAUSED, SessionStatus.ACTIVE, "resume"
        )
        result = cast(
            CursorResult[Any],
            db.execute(
                update(Interruption)
                .where(Interruption.id == open_pause.id, Interruption.resume_time.is_(None))
                .values(resume_time=current_time)
                .execution_options(synchronize_session=False)
            ),
        )
        if result.rowcount != 1:
            raise InvalidTransitionError(
                f"Cannot resume session {session_id}: the pause was modified by another request."
            )
    return _fetch_session(db, session_id)


def complete_session(db: DbSession, session_id: int, now: datetime | None = None) -> SessionModel:
    """Complete an active session as `completed`, or `overdue` if beyond 110% of its duration."""
    current_time = _resolve_now(now)
    session = _get_current_session(db, session_id, current_time)
    _require_status(session, SessionStatus.ACTIVE, "complete")
    if session.start_time is None:
        raise PersistenceError(f"Active session {session_id} has no start_time.")
    elapsed = current_time - session.start_time
    final_status = (
        SessionStatus.OVERDUE
        if is_overdue(session.scheduled_duration, elapsed)
        else SessionStatus.COMPLETED
    )
    with _transaction(db):
        _transition_or_raise(
            db,
            session_id,
            SessionStatus.ACTIVE,
            final_status,
            "complete",
            end_time=current_time,
        )
    return _fetch_session(db, session_id)


# --- History and summary -----------------------------------------------------


def finalize_abandoned_sessions(db: DbSession, now: datetime | None = None) -> int:
    """Finalize every paused session whose pause outlived the timeout. Returns the count."""
    current_time = _resolve_now(now)
    cutoff = current_time - ABANDONMENT_TIMEOUT
    due_pauses = db.execute(
        select(Interruption.session_id, Interruption.pause_time)
        .join(SessionModel, SessionModel.id == Interruption.session_id)
        .where(
            SessionModel.status == SessionStatus.PAUSED,
            Interruption.resume_time.is_(None),
            Interruption.pause_time <= cutoff,
        )
    ).all()
    if not due_pauses:
        return 0
    finalized = 0
    with _transaction(db):
        for session_id, pause_time in due_pauses:
            if _try_transition(
                db,
                session_id,
                SessionStatus.PAUSED,
                SessionStatus.ABANDONED,
                end_time=abandonment_deadline(pause_time),
            ):
                finalized += 1
    return finalized


def _compute_timing(
    session: SessionModel, now: datetime
) -> tuple[int | None, int, int | None]:
    """Return (elapsed, paused, focused) in whole seconds; elapsed/focused are None if unstarted."""
    if session.start_time is None:
        return None, 0, None
    end = session.end_time or now
    elapsed = max(_ZERO, end - session.start_time)
    paused = _ZERO
    for interruption in session.interruptions:
        paused_until = interruption.resume_time or end
        paused += max(_ZERO, paused_until - interruption.pause_time)
    focused = max(_ZERO, elapsed - paused)
    return int(elapsed.total_seconds()), int(paused.total_seconds()), int(focused.total_seconds())


def _to_history_item(session: SessionModel, now: datetime) -> SessionHistoryItem:
    elapsed, paused, focused = _compute_timing(session, now)
    return SessionHistoryItem.model_validate(session).model_copy(
        update={"elapsed_seconds": elapsed, "paused_seconds": paused, "focused_seconds": focused}
    )


def _build_summary(items: list[SessionHistoryItem]) -> HistorySummary:
    status_counts: dict[str, int] = {status.value: 0 for status in SessionStatus}
    for item in items:
        status_counts[item.status.value] += 1

    completed_count = status_counts[SessionStatus.COMPLETED.value]
    terminal_count = sum(status_counts[status.value] for status in TERMINAL_STATUSES)
    completion_rate = round(completed_count / terminal_count * 100, 1) if terminal_count else 0.0

    completed_focused = [
        item.focused_seconds
        for item in items
        if item.status is SessionStatus.COMPLETED and item.focused_seconds is not None
    ]
    average_completed = (
        round(sum(completed_focused) / len(completed_focused), 1) if completed_focused else None
    )

    return HistorySummary(
        total_sessions=len(items),
        status_counts=status_counts,
        completed_count=completed_count,
        completion_rate=completion_rate,
        total_interruptions=sum(item.pause_count for item in items),
        total_focused_seconds=sum(item.focused_seconds or 0 for item in items),
        average_focused_seconds_completed=average_completed,
    )


def get_history(db: DbSession, now: datetime | None = None) -> HistoryResponse:
    """All sessions (newest first) with derived timing and a productivity summary."""
    current_time = _resolve_now(now)
    finalize_abandoned_sessions(db, current_time)
    statement = (
        select(SessionModel)
        .options(selectinload(SessionModel.interruptions))
        .order_by(SessionModel.created_at.desc(), SessionModel.id.desc())
        .execution_options(populate_existing=True)
    )
    try:
        sessions = db.execute(statement).scalars().all()
    except SQLAlchemyError as exc:
        raise PersistenceError("A database error occurred while loading history.") from exc
    items = [_to_history_item(session, current_time) for session in sessions]
    return HistoryResponse(summary=_build_summary(items), sessions=items)