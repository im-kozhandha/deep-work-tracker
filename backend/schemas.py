"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from backend.models import SessionStatus

MAX_DURATION_MINUTES: int = 1440  # 24 hours; also guards against integer overflow
MAX_TITLE_LENGTH: int = 200
MAX_GOAL_LENGTH: int = 1000
MAX_REASON_LENGTH: int = 500

TitleStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TITLE_LENGTH)
]
ReasonStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_REASON_LENGTH)
]


class SessionCreate(BaseModel):
    title: TitleStr
    duration: int = Field(
        gt=0, le=MAX_DURATION_MINUTES, description="Scheduled duration in minutes."
    )
    goal: str | None = Field(default=None, max_length=MAX_GOAL_LENGTH)

    @field_validator("goal")
    @classmethod
    def blank_goal_becomes_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class PauseRequest(BaseModel):
    reason: ReasonStr = Field(description="Why the session is being paused (required).")


class InterruptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reason: str
    pause_time: datetime
    resume_time: datetime | None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    goal: str | None
    scheduled_duration: int = Field(description="Scheduled duration in minutes.")
    start_time: datetime | None
    end_time: datetime | None
    status: SessionStatus
    created_at: datetime
    pause_count: int
    interruptions: list[InterruptionRead]


class SessionHistoryItem(SessionRead):
    """Session plus derived timing, filled in by the service layer."""

    elapsed_seconds: int | None = Field(
        default=None,
        description="Wall-clock seconds from start to end (or to now if unfinished), "
        "including paused time. Null if never started.",
    )
    paused_seconds: int = Field(default=0, description="Total seconds spent paused.")
    focused_seconds: int | None = Field(
        default=None, description="elapsed_seconds minus paused_seconds. Null if never started."
    )


class HistorySummary(BaseModel):
    total_sessions: int
    status_counts: dict[str, int] = Field(
        description="Count per status; every allowed status is present, zeros included."
    )
    completed_count: int
    completion_rate: float = Field(
        description="completed / sessions in a terminal state * 100, rounded to 1 decimal; "
        "0.0 when no session is terminal."
    )
    total_interruptions: int
    total_focused_seconds: int
    average_focused_seconds_completed: float | None = Field(
        description="Mean focused seconds over completed sessions; null if none."
    )


class HistoryResponse(BaseModel):
    summary: HistorySummary
    sessions: list[SessionHistoryItem]


class ErrorResponse(BaseModel):
    """Shape of FastAPI HTTPException bodies, used for OpenAPI documentation."""

    detail: str