"""ORM models mirroring the supplied schema, plus the resume_time column added in migration 0002."""
import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Dialect,
    ForeignKey,
    Index,
    Integer,
    Text,
    TypeDecorator,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def utc_now() -> datetime:
    """Single source of 'now' for the whole backend: timezone-aware UTC."""
    return datetime.now(timezone.utc)


class SessionStatus(str, enum.Enum):
    """Allowed statuses, in the order given by the assessment schema."""

    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    ABANDONED = "abandoned"
    OVERDUE = "overdue"

    @property
    def is_terminal(self) -> bool:
        return self in TERMINAL_STATUSES


# Terminal states: no further lifecycle operation is accepted.
TERMINAL_STATUSES: frozenset[SessionStatus] = frozenset(
    {
        SessionStatus.COMPLETED,
        SessionStatus.INTERRUPTED,
        SessionStatus.ABANDONED,
        SessionStatus.OVERDUE,
    }
)


class UtcDateTime(TypeDecorator[datetime]):
    """Stores naive UTC in SQLite; always returns timezone-aware UTC datetimes."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime rejected; use timezone-aware UTC values.")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class SessionStatusType(TypeDecorator[SessionStatus]):
    """Persists SessionStatus as its string value; returns the enum on read."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return SessionStatus(value).value

    def process_result_value(self, value: Any, dialect: Dialect) -> SessionStatus | None:
        if value is None:
            return None
        return SessionStatus(value)


_STATUS_CHECK_SQL: str = "status IN (" + ", ".join(f"'{s.value}'" for s in SessionStatus) + ")"


class Session(Base):
    """A scheduled focus session. Columns mirror the supplied DDL exactly
    (status and created_at are nullable there; their defaults always populate them)."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(_STATUS_CHECK_SQL),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_duration: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes
    start_time: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        SessionStatusType,
        nullable=True,
        default=SessionStatus.SCHEDULED,
        server_default=SessionStatus.SCHEDULED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=True,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    interruptions: Mapped[list["Interruption"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=lambda: [Interruption.pause_time, Interruption.id],
    )

    @property
    def pause_count(self) -> int:
        """Number of pause events (one interruption row per pause)."""
        return len(self.interruptions)


class Interruption(Base):
    """One pause event. resume_time stays NULL until the session is resumed."""

    __tablename__ = "interruptions"
    __table_args__ = (
        Index("ix_interruptions_session_id", "session_id"),
        # At most one unresumed pause per session (guards double-pause races).
        Index(
            "uq_interruptions_one_open_pause",
            "session_id",
            unique=True,
            sqlite_where=text("resume_time IS NULL"),
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    pause_time: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=True,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    resume_time: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)

    session: Mapped[Session] = relationship(back_populates="interruptions")