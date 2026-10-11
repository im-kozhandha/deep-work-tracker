"""HTTP layer for /sessions. Delegates every rule to the service layer."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session as DbSession

from backend.database import get_db
from backend.models import Session as SessionModel
from backend.schemas import (
    ErrorResponse,
    HistoryResponse,
    PauseRequest,
    SessionCreate,
    SessionRead,
)
from backend.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])

DbDep = Annotated[DbSession, Depends(get_db)]
SessionIdPath = Annotated[int, Path(ge=1, description="Identifier of the session.")]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Session not found."}
}
_CONFLICT: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "The action is not allowed in the session's current state.",
    }
}
_SERVER_ERROR: dict[int | str, dict[str, Any]] = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": ErrorResponse,
        "description": "Unexpected server or database error.",
    }
}
_TRANSITION_RESPONSES: dict[int | str, dict[str, Any]] = {
    **_NOT_FOUND,
    **_CONFLICT,
    **_SERVER_ERROR,
}


@router.post(
    "/",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="schedule_session",
    summary="Schedule a session",
    description="Creates a session in the `scheduled` state. `duration` is in minutes (1-1440).",
    responses=_SERVER_ERROR,
)
def schedule_session(payload: SessionCreate, db: DbDep) -> SessionModel:
    return session_service.create_session(db, payload)


@router.get(
    "/history",
    response_model=HistoryResponse,
    operation_id="get_session_history",
    summary="Session history and productivity summary",
    description=(
        "Returns every session (newest first) with pause count, interruption reasons, "
        "elapsed/paused/focused seconds and a summary including the completion rate. "
        "Paused sessions whose pause outlived the abandonment timeout are finalized as "
        "`abandoned` before the response is built."
    ),
    responses=_SERVER_ERROR,
)
def get_session_history(db: DbDep) -> HistoryResponse:
    return session_service.get_history(db)


@router.patch(
    "/{session_id}/start",
    response_model=SessionRead,
    operation_id="start_session",
    summary="Start a scheduled session",
    description="Allowed only from `scheduled`. Records `start_time` and sets `active`.",
    responses=_TRANSITION_RESPONSES,
)
def start_session(session_id: SessionIdPath, db: DbDep) -> SessionModel:
    return session_service.start_session(db, session_id)


@router.patch(
    "/{session_id}/pause",
    response_model=SessionRead,
    operation_id="pause_session",
    summary="Pause an active session",
    description=(
        "Allowed only from `active`; a non-empty `reason` is required. Records an "
        "interruption and sets `paused`. A session paused more than three times "
        "(the fourth pause) becomes `interrupted`, which is terminal."
    ),
    responses=_TRANSITION_RESPONSES,
)
def pause_session(session_id: SessionIdPath, payload: PauseRequest, db: DbDep) -> SessionModel:
    return session_service.pause_session(db, session_id, payload)


@router.patch(
    "/{session_id}/resume",
    response_model=SessionRead,
    operation_id="resume_session",
    summary="Resume a paused session",
    description=(
        "Allowed only from `paused` and only before the abandonment timeout elapses; "
        "afterwards the session is `abandoned` and the request is rejected."
    ),
    responses=_TRANSITION_RESPONSES,
)
def resume_session(session_id: SessionIdPath, db: DbDep) -> SessionModel:
    return session_service.resume_session(db, session_id)


@router.patch(
    "/{session_id}/complete",
    response_model=SessionRead,
    operation_id="complete_session",
    summary="Complete an active session",
    description=(
        "Allowed only from `active`. Sets `completed`, or `overdue` when the wall-clock "
        "time since start (pauses included) exceeds 110% of the scheduled duration."
    ),
    responses=_TRANSITION_RESPONSES,
)
def complete_session(session_id: SessionIdPath, db: DbDep) -> SessionModel:
    return session_service.complete_session(db, session_id)