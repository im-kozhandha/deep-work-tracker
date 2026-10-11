"""Schema, constraint, migration and seed-data tests."""
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from backend.database import PROJECT_ROOT, build_engine
from backend.models import Interruption, SessionStatus, UtcDateTime
from backend.schemas import PauseRequest, SessionCreate
from backend.services import session_service
from backend.services.session_service import (
    ABANDONMENT_TIMEOUT,
    is_overdue,
    overdue_threshold,
)

SEED_PATH: Path = PROJECT_ROOT / "seed_data.sql"
HEAD_REVISION: str = "0002_interruption_resume_time"

EXPECTED_SEED_STATUS_BY_TITLE: dict[str, str] = {
    "Seed: Plan sprint": "scheduled",
    "Seed: Write report": "active",
    "Seed: Code review": "completed",
    "Seed: Morning focus": "completed",
    "Seed: Research paper": "paused",
    "Seed: Deep refactor": "interrupted",
    "Seed: Long workshop": "overdue",
    "Seed: Reading block": "abandoned",
}
EXPECTED_SEED_PAUSE_COUNTS: dict[str, int] = {
    "Seed: Plan sprint": 0,
    "Seed: Write report": 0,
    "Seed: Code review": 1,
    "Seed: Morning focus": 0,
    "Seed: Research paper": 1,
    "Seed: Deep refactor": 4,
    "Seed: Long workshop": 1,
    "Seed: Reading block": 1,
}


class TestConstraints:
    def test_foreign_keys_are_enforced(self, db: DbSession) -> None:
        db.add(Interruption(session_id=9999, reason="orphan"))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_deleting_a_session_cascades_to_its_interruptions(self, db: DbSession) -> None:
        session_id = session_service.create_session(
            db, SessionCreate(title="cascade", duration=30)
        ).id
        session_service.start_session(db, session_id)
        session_service.pause_session(db, session_id, PauseRequest(reason="x"))

        db.execute(text("DELETE FROM sessions WHERE id = :id"), {"id": session_id})
        db.commit()
        remaining = db.execute(text("SELECT COUNT(*) FROM interruptions")).scalar_one()
        assert remaining == 0

    def test_status_check_constraint_rejects_unknown_values(self, db: DbSession) -> None:
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT INTO sessions (title, scheduled_duration, status) "
                    "VALUES ('bad', 10, 'bogus')"
                )
            )
        db.rollback()

    def test_only_one_unresumed_pause_is_allowed_per_session(self, db: DbSession) -> None:
        session_id = session_service.create_session(
            db, SessionCreate(title="double pause", duration=30)
        ).id
        session_service.start_session(db, session_id)
        session_service.pause_session(db, session_id, PauseRequest(reason="first"))

        db.add(Interruption(session_id=session_id, reason="duplicate open pause"))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_session_status_column_defaults_to_scheduled(self, db: DbSession) -> None:
        db.execute(text("INSERT INTO sessions (title, scheduled_duration) VALUES ('d', 10)"))
        db.commit()
        status = db.execute(text("SELECT status FROM sessions")).scalar_one()
        assert status == SessionStatus.SCHEDULED.value


class TestUtcDateTimeType:
    def test_naive_datetimes_are_rejected_on_write(self) -> None:
        with pytest.raises(ValueError, match="Naive datetime rejected"):
            UtcDateTime().process_bind_param(datetime(2026, 1, 5, 9, 0), None)  # type: ignore[arg-type]

    def test_aware_values_are_stored_as_naive_utc(self) -> None:
        ist = timezone(timedelta(hours=5, minutes=30))
        stored = UtcDateTime().process_bind_param(
            datetime(2026, 1, 5, 14, 30, tzinfo=ist), None  # type: ignore[arg-type]
        )
        assert stored == datetime(2026, 1, 5, 9, 0)
        assert stored is not None and stored.tzinfo is None

    def test_values_are_returned_as_aware_utc(self) -> None:
        value = UtcDateTime().process_result_value(datetime(2026, 1, 5, 9, 0), None)  # type: ignore[arg-type]
        assert value == datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)

    def test_none_passes_through(self) -> None:
        type_ = UtcDateTime()
        assert type_.process_bind_param(None, None) is None  # type: ignore[arg-type]
        assert type_.process_result_value(None, None) is None  # type: ignore[arg-type]


@pytest.fixture()
def migrated_engine(tmp_path: Path) -> Iterator[Engine]:
    """A temporary file database created by `alembic upgrade head` (never the real one)."""
    database_file = tmp_path / "migrated_test.db"
    url = f"sqlite:///{database_file.as_posix()}"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", (PROJECT_ROOT / "alembic").as_posix())
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    engine = build_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


class TestAlembicMigrations:
    def test_upgrade_head_creates_the_expected_schema(self, migrated_engine: Engine) -> None:
        inspector = inspect(migrated_engine)
        assert {"sessions", "interruptions", "alembic_version"} <= set(inspector.get_table_names())
        assert {column["name"] for column in inspector.get_columns("sessions")} == {
            "id",
            "title",
            "goal",
            "scheduled_duration",
            "start_time",
            "end_time",
            "status",
            "created_at",
        }
        assert {column["name"] for column in inspector.get_columns("interruptions")} == {
            "id",
            "session_id",
            "reason",
            "pause_time",
            "resume_time",
        }
        index_names = {index["name"] for index in inspector.get_indexes("interruptions")}
        assert {"ix_interruptions_session_id", "uq_interruptions_one_open_pause"} <= index_names

        foreign_key = inspector.get_foreign_keys("interruptions")[0]
        assert foreign_key["referred_table"] == "sessions"
        assert foreign_key["options"].get("ondelete") == "CASCADE"

        with migrated_engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision == HEAD_REVISION

    def test_orm_lifecycle_works_on_the_migrated_schema(self, migrated_engine: Engine) -> None:
        factory = sessionmaker(bind=migrated_engine, autoflush=False, expire_on_commit=False)
        with factory() as db:
            session_id = session_service.create_session(
                db, SessionCreate(title="migrated", duration=40)
            ).id
            session_service.start_session(db, session_id)
            paused = session_service.pause_session(db, session_id, PauseRequest(reason="check"))
            assert paused.status is SessionStatus.PAUSED
            resumed = session_service.resume_session(db, session_id)
            assert resumed.status is SessionStatus.ACTIVE
            completed = session_service.complete_session(db, session_id)
            assert completed.status is SessionStatus.COMPLETED


def _apply_seed(engine: Engine) -> None:
    """Run seed_data.sql exactly as a user would: through a plain sqlite3 connection."""
    database_path = engine.url.database
    assert database_path is not None
    with closing(sqlite3.connect(database_path)) as connection:
        connection.executescript(SEED_PATH.read_text(encoding="utf-8"))


class TestSeedData:
    def test_seed_file_exists(self) -> None:
        assert SEED_PATH.is_file()

    def test_seed_loads_and_is_consistent_with_the_business_rules(
        self, migrated_engine: Engine
    ) -> None:
        _apply_seed(migrated_engine)
        factory = sessionmaker(bind=migrated_engine, autoflush=False, expire_on_commit=False)
        with factory() as db:
            history = session_service.get_history(db, now=datetime.now(timezone.utc))

        by_title = {item.title: item for item in history.sessions}
        assert {title: item.status.value for title, item in by_title.items()} == (
            EXPECTED_SEED_STATUS_BY_TITLE
        )
        assert {title: item.pause_count for title, item in by_title.items()} == (
            EXPECTED_SEED_PAUSE_COUNTS
        )

        summary = history.summary
        assert summary.total_sessions == 8
        assert summary.completed_count == 2
        assert summary.completion_rate == 40.0  # 2 completed of 5 terminal sessions
        assert summary.total_interruptions == 8

        for item in history.sessions:
            assert item.elapsed_seconds is None or item.elapsed_seconds >= 0
            elapsed = timedelta(seconds=item.elapsed_seconds or 0)
            if item.status is SessionStatus.COMPLETED:
                assert not is_overdue(item.scheduled_duration, elapsed), item.title
            if item.status is SessionStatus.OVERDUE:
                assert is_overdue(item.scheduled_duration, elapsed), item.title
                assert elapsed > overdue_threshold(item.scheduled_duration)
            if item.status is SessionStatus.INTERRUPTED:
                assert item.pause_count == 4
                assert item.interruptions[-1].resume_time is None
                assert item.end_time == item.interruptions[-1].pause_time
            if item.status is SessionStatus.ABANDONED:
                last = item.interruptions[-1]
                assert last.resume_time is None
                assert item.end_time == last.pause_time + ABANDONMENT_TIMEOUT

    def test_seed_can_be_applied_twice_without_duplicates(self, migrated_engine: Engine) -> None:
        _apply_seed(migrated_engine)
        _apply_seed(migrated_engine)
        with migrated_engine.connect() as connection:
            sessions = connection.execute(text("SELECT COUNT(*) FROM sessions")).scalar_one()
            interruptions = connection.execute(
                text("SELECT COUNT(*) FROM interruptions")
            ).scalar_one()
        assert sessions == 8
        assert interruptions == 8