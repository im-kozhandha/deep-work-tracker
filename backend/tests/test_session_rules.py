"""Business-rule tests: thresholds, abandonment, interruption limit and race/atomicity guards."""
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy.orm import Session as DbSession

from backend.models import Session as SessionModel
from backend.models import SessionStatus
from backend.schemas import PauseRequest, SessionCreate
from backend.services import session_service
from backend.services.exceptions import (
    InvalidTransitionError,
    PersistenceError,
    SessionNotFoundError,
)
from backend.services.session_service import (
    ABANDONMENT_TIMEOUT,
    INTERRUPTION_PAUSE_LIMIT,
    abandonment_deadline,
    is_overdue,
    overdue_threshold,
)
from backend.tests.helpers import (
    TRANSITION_ACTIONS,
    ApiHelper,
    FakeClock,
    interrupt_session,
    parse_ts,
)

ABANDONMENT_SECONDS: int = 30 * 60

# (scheduled minutes, elapsed seconds, expected status). Threshold seconds = minutes * 66.
OVERDUE_CASES = [
    pytest.param(50, 0, "completed", id="50min-at-0s"),
    pytest.param(50, 3000, "completed", id="50min-at-50min"),
    pytest.param(50, 3300, "completed", id="50min-at-exactly-110pct"),
    pytest.param(50, 3301, "overdue", id="50min-one-second-over"),
    pytest.param(50, 3600, "overdue", id="50min-at-60min"),
    pytest.param(1, 66, "completed", id="1min-at-66s"),
    pytest.param(1, 67, "overdue", id="1min-at-67s"),
    pytest.param(25, 1650, "completed", id="25min-at-exactly-110pct"),
    pytest.param(25, 1651, "overdue", id="25min-one-second-over"),
    pytest.param(1440, 95040, "completed", id="1440min-at-exactly-110pct"),
    pytest.param(1440, 95041, "overdue", id="1440min-one-second-over"),
]


def _new_session(db: DbSession, title: str = "Service test", duration: int = 50) -> int:
    return session_service.create_session(db, SessionCreate(title=title, duration=duration)).id


def _active_session(db: DbSession, title: str = "Service test") -> int:
    session_id = _new_session(db, title)
    session_service.start_session(db, session_id)
    return session_id


def _paused_session(db: DbSession, title: str = "Service test") -> int:
    session_id = _active_session(db, title)
    session_service.pause_session(db, session_id, PauseRequest(reason="Break"))
    return session_id


def _status_of(db: DbSession, session_id: int) -> SessionStatus:
    db.expire_all()
    session = db.get(SessionModel, session_id)
    assert session is not None
    return session.status


class TestPureRuleHelpers:
    def test_overdue_threshold_is_110_percent_of_scheduled_duration(self) -> None:
        assert overdue_threshold(50) == timedelta(minutes=55)
        assert overdue_threshold(1) == timedelta(seconds=66)

    @pytest.mark.parametrize(("minutes", "elapsed_seconds", "expected"), OVERDUE_CASES)
    def test_is_overdue_boundaries(self, minutes: int, elapsed_seconds: int, expected: str) -> None:
        assert is_overdue(minutes, timedelta(seconds=elapsed_seconds)) is (expected == "overdue")

    def test_one_microsecond_past_the_threshold_is_overdue(self) -> None:
        assert is_overdue(50, timedelta(minutes=55, microseconds=1)) is True

    def test_interruption_limit_is_three_pauses(self) -> None:
        assert INTERRUPTION_PAUSE_LIMIT == 3

    def test_abandonment_deadline_adds_the_timeout(self) -> None:
        pause_time = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
        assert ABANDONMENT_TIMEOUT == timedelta(minutes=30)
        assert abandonment_deadline(pause_time) == pause_time + timedelta(minutes=30)


class TestOverdueThreshold:
    @pytest.mark.parametrize(("minutes", "elapsed_seconds", "expected"), OVERDUE_CASES)
    def test_completion_status_at_boundary(
        self,
        api: ApiHelper,
        clock: FakeClock,
        minutes: int,
        elapsed_seconds: int,
        expected: str,
    ) -> None:
        session_id = api.create_active(duration=minutes)
        clock.advance(seconds=elapsed_seconds)
        body = api.complete_ok(session_id)
        assert body["status"] == expected
        assert parse_ts(body["end_time"]) == clock.now

    @pytest.mark.parametrize(
        ("final_advance_seconds", "expected"),
        [
            pytest.param(25 * 60, "completed", id="total-55m00s"),
            pytest.param(25 * 60 + 1, "overdue", id="total-55m01s"),
        ],
    )
    def test_paused_time_counts_toward_the_overdue_threshold(
        self, api: ApiHelper, clock: FakeClock, final_advance_seconds: int, expected: str
    ) -> None:
        session_id = api.create_active(duration=50)
        clock.advance(minutes=10)
        api.pause_ok(session_id, "Long break")
        clock.advance(minutes=20)  # inside the 30-minute abandonment window
        api.resume_ok(session_id)
        clock.advance(seconds=final_advance_seconds)
        assert api.complete_ok(session_id)["status"] == expected

    def test_overdue_session_is_not_counted_as_completed(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active(duration=50)
        clock.advance(minutes=60)
        assert api.complete_ok(session_id)["status"] == "overdue"
        summary = api.history_json()["summary"]
        assert summary["status_counts"]["overdue"] == 1
        assert summary["completed_count"] == 0
        assert summary["completion_rate"] == 0.0


class TestInterruptionThreshold:
    def test_pauses_one_to_three_pause_and_the_fourth_interrupts(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        session_id = api.create_active()
        for pause_number in (1, 2, 3):
            body = api.pause_ok(session_id, f"Pause {pause_number}")
            assert body["status"] == "paused"
            assert body["pause_count"] == pause_number
            assert body["end_time"] is None
            assert api.resume_ok(session_id)["status"] == "active"

        clock.advance(minutes=1)
        body = api.pause_ok(session_id, "Pause 4")
        assert body["status"] == "interrupted"
        assert body["pause_count"] == 4
        assert parse_ts(body["end_time"]) == clock.now

    def test_fourth_pause_is_recorded_and_stays_unresumed(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        session_id = api.create_active()
        body = interrupt_session(api, clock, session_id)
        interruptions = body["interruptions"]
        assert [i["reason"] for i in interruptions] == [f"Interruption {n}" for n in (1, 2, 3, 4)]
        assert all(i["resume_time"] is not None for i in interruptions[:3])
        assert interruptions[3]["resume_time"] is None
        assert parse_ts(body["end_time"]) == parse_ts(interruptions[3]["pause_time"])

    def test_interrupted_takes_precedence_over_overdue(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active(duration=50)
        clock.advance(minutes=100)  # far beyond 110% while still active
        body = interrupt_session(api, clock, session_id)
        assert body["status"] == "interrupted"

    def test_interrupted_session_is_never_abandoned(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active()
        interrupt_session(api, clock, session_id)
        before = api.history_item(session_id)
        clock.advance(hours=5)
        after = api.history_item(session_id)
        assert after["status"] == "interrupted"
        assert after["end_time"] == before["end_time"]


class TestAbandonment:
    def test_pause_within_timeout_stays_paused(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active()
        api.pause_ok(session_id)
        clock.advance(seconds=ABANDONMENT_SECONDS - 1)
        assert api.history_item(session_id)["status"] == "paused"

    @pytest.mark.parametrize(
        ("seconds_paused", "resume_status_code"),
        [
            pytest.param(ABANDONMENT_SECONDS - 1, 200, id="one-second-before-deadline"),
            pytest.param(ABANDONMENT_SECONDS, 409, id="exactly-at-deadline"),
            pytest.param(2 * ABANDONMENT_SECONDS, 409, id="well-after-deadline"),
        ],
    )
    def test_resume_is_only_possible_before_the_deadline(
        self, api: ApiHelper, clock: FakeClock, seconds_paused: int, resume_status_code: int
    ) -> None:
        session_id = api.create_active()
        api.pause_ok(session_id)
        clock.advance(seconds=seconds_paused)
        response = api.resume(session_id)
        assert response.status_code == resume_status_code
        expected_status = "active" if resume_status_code == 200 else "abandoned"
        assert api.history_item(session_id)["status"] == expected_status

    def test_history_finalizes_abandonment_at_the_deadline_not_at_discovery(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        session_id = api.create_active()
        clock.advance(minutes=5)
        paused_at = clock.now
        api.pause_ok(session_id, "Left the desk")
        clock.advance(hours=3)  # nobody looks for a long time

        item = api.history_item(session_id)
        assert item["status"] == "abandoned"
        assert parse_ts(item["end_time"]) == paused_at + ABANDONMENT_TIMEOUT
        assert item["interruptions"][0]["resume_time"] is None
        assert item["elapsed_seconds"] == 35 * 60
        assert item["paused_seconds"] == ABANDONMENT_SECONDS
        assert item["focused_seconds"] == 5 * 60

    def test_abandonment_is_stable_across_repeated_history_calls(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        session_id = api.create_active()
        api.pause_ok(session_id)
        clock.advance(hours=1)
        first = api.history_item(session_id)
        clock.advance(hours=1)
        second = api.history_item(session_id)
        assert first["status"] == second["status"] == "abandoned"
        assert first["end_time"] == second["end_time"]

    @pytest.mark.parametrize("action", TRANSITION_ACTIONS)
    def test_every_action_on_a_timed_out_pause_is_rejected_as_abandoned(
        self, api: ApiHelper, clock: FakeClock, action: str
    ) -> None:
        session_id = api.create_active()
        api.pause_ok(session_id)
        clock.advance(seconds=ABANDONMENT_SECONDS)
        response = api.act(session_id, action)
        assert response.status_code == 409
        assert "terminal state 'abandoned'" in response.json()["detail"]

    def test_active_session_is_never_abandoned(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active()
        clock.advance(hours=10)
        assert api.history_item(session_id)["status"] == "active"

    def test_resumed_session_is_not_abandoned(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active()
        api.pause_ok(session_id)
        clock.advance(minutes=5)
        api.resume_ok(session_id)
        clock.advance(hours=2)
        assert api.history_item(session_id)["status"] == "active"

    def test_abandonment_is_measured_from_the_latest_open_pause(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        session_id = api.create_active()
        api.pause_ok(session_id, "First")
        clock.advance(minutes=20)
        api.resume_ok(session_id)
        clock.advance(minutes=5)
        second_pause_at = clock.now
        api.pause_ok(session_id, "Second")

        clock.advance(minutes=29)
        assert api.history_item(session_id)["status"] == "paused"

        clock.advance(minutes=1)
        item = api.history_item(session_id)
        assert item["status"] == "abandoned"
        assert parse_ts(item["end_time"]) == second_pause_at + ABANDONMENT_TIMEOUT


class TestFinalizeAbandonedSessions:
    @pytest.mark.parametrize(
        ("seconds_paused", "expected_finalized"),
        [
            pytest.param(ABANDONMENT_SECONDS - 1, 0, id="one-second-early"),
            pytest.param(ABANDONMENT_SECONDS, 1, id="exact-deadline"),
            pytest.param(ABANDONMENT_SECONDS + 1, 1, id="one-second-late"),
        ],
    )
    def test_deadline_boundary(
        self, db: DbSession, clock: FakeClock, seconds_paused: int, expected_finalized: int
    ) -> None:
        session_id = _paused_session(db)
        clock.advance(seconds=seconds_paused)
        assert session_service.finalize_abandoned_sessions(db) == expected_finalized
        expected_status = SessionStatus.ABANDONED if expected_finalized else SessionStatus.PAUSED
        assert _status_of(db, session_id) is expected_status

    def test_only_due_paused_sessions_are_finalized(self, db: DbSession, clock: FakeClock) -> None:
        due_one = _paused_session(db, "due-one")
        due_two = _paused_session(db, "due-two")
        clock.advance(minutes=20)
        not_due = _paused_session(db, "not-due")
        clock.advance(minutes=11)  # due_* paused 31 min ago, not_due 11 min ago
        active = _active_session(db, "active")
        scheduled = _new_session(db, "scheduled")

        assert session_service.finalize_abandoned_sessions(db) == 2
        assert _status_of(db, due_one) is SessionStatus.ABANDONED
        assert _status_of(db, due_two) is SessionStatus.ABANDONED
        assert _status_of(db, not_due) is SessionStatus.PAUSED
        assert _status_of(db, active) is SessionStatus.ACTIVE
        assert _status_of(db, scheduled) is SessionStatus.SCHEDULED
        assert session_service.finalize_abandoned_sessions(db) == 0  # idempotent


class TestServiceLayerGuards:
    @pytest.mark.parametrize("action", TRANSITION_ACTIONS)
    def test_missing_session_raises_not_found(self, db: DbSession, action: str) -> None:
        calls: dict[str, Any] = {
            "start": lambda: session_service.start_session(db, 999),
            "pause": lambda: session_service.pause_session(db, 999, PauseRequest(reason="x")),
            "resume": lambda: session_service.resume_session(db, 999),
            "complete": lambda: session_service.complete_session(db, 999),
        }
        with pytest.raises(SessionNotFoundError, match="Session 999 not found"):
            calls[action]()

    def test_naive_now_is_rejected(self, db: DbSession) -> None:
        session_id = _new_session(db)
        with pytest.raises(ValueError, match="timezone-aware"):
            session_service.start_session(db, session_id, now=datetime(2026, 1, 5, 9, 0))

    def test_non_utc_now_is_normalized_to_utc(self, db: DbSession) -> None:
        session_id = _new_session(db)
        ist = timezone(timedelta(hours=5, minutes=30))
        started = session_service.start_session(
            db, session_id, now=datetime(2026, 1, 5, 14, 30, tzinfo=ist)
        )
        assert started.start_time == datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
        assert started.start_time is not None
        assert started.start_time.utcoffset() == timedelta(0)

    def test_status_swap_is_compare_and_swap(self, db: DbSession, clock: FakeClock) -> None:
        session_id = _new_session(db)
        assert (
            session_service._try_transition(
                db, session_id, SessionStatus.ACTIVE, SessionStatus.PAUSED
            )
            is False
        )
        db.rollback()
        with pytest.raises(InvalidTransitionError, match="modified by another request"):
            session_service._transition_or_raise(
                db, session_id, SessionStatus.ACTIVE, SessionStatus.COMPLETED, "complete"
            )
        db.rollback()
        assert (
            session_service._try_transition(
                db,
                session_id,
                SessionStatus.SCHEDULED,
                SessionStatus.ACTIVE,
                start_time=clock.now,
            )
            is True
        )
        db.commit()
        assert _status_of(db, session_id) is SessionStatus.ACTIVE

    def test_stale_snapshot_cannot_start_a_session_twice(
        self, db: DbSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session_id = _new_session(db)
        stale = session_service._fetch_session(db, session_id)  # status: scheduled
        db.expunge(stale)
        session_service.start_session(db, session_id)  # the "other request" wins

        monkeypatch.setattr(session_service, "_get_current_session", lambda *_args: stale)
        with pytest.raises(InvalidTransitionError, match="modified by another request"):
            session_service.start_session(db, session_id)
        assert _status_of(db, session_id) is SessionStatus.ACTIVE

    def test_stale_snapshot_cannot_record_a_second_pause(
        self, db: DbSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session_id = _active_session(db)
        stale = session_service._fetch_session(db, session_id)  # status: active
        db.expunge(stale)
        session_service.pause_session(db, session_id, PauseRequest(reason="First"))

        monkeypatch.setattr(session_service, "_get_current_session", lambda *_args: stale)
        with pytest.raises(InvalidTransitionError, match="modified by another request"):
            session_service.pause_session(db, session_id, PauseRequest(reason="Second"))

        current = session_service._fetch_session(db, session_id)
        assert current.status is SessionStatus.PAUSED
        assert current.pause_count == 1

    def test_failed_pause_rolls_back_the_status_change(self, db: DbSession) -> None:
        session_id = _active_session(db)
        invalid_payload = PauseRequest.model_construct(reason=None)  # bypasses validation
        with pytest.raises(PersistenceError):
            session_service.pause_session(db, session_id, invalid_payload)  # type: ignore[arg-type]
        current = session_service._fetch_session(db, session_id)
        assert current.status is SessionStatus.ACTIVE
        assert current.pause_count == 0