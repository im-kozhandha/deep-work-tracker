"""Database engine, session factory, declarative base and FastAPI dependency."""
import os
import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL: str = f"sqlite:///{(PROJECT_ROOT / 'deepwork.db').as_posix()}"
DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# Seconds a connection waits for a competing write lock before raising.
SQLITE_BUSY_TIMEOUT_SECONDS: int = 15


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models and Alembic."""


def _enable_sqlite_foreign_keys(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
    """SQLite ignores foreign keys unless this pragma is set on every connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _is_in_memory_sqlite(database_url: str) -> bool:
    return database_url == "sqlite://" or ":memory:" in database_url


def build_engine(database_url: str) -> Engine:
    """Create a SQLite engine with foreign-key enforcement enabled.

    In-memory databases use a StaticPool so every session shares one connection
    (required for tests, otherwise each connection sees an empty database).
    """
    if not database_url.startswith("sqlite"):
        raise ValueError(f"Only SQLite URLs are supported, got: {database_url!r}")

    engine_options: dict[str, Any] = {
        "connect_args": {
            "check_same_thread": False,
            "timeout": SQLITE_BUSY_TIMEOUT_SECONDS,
        }
    }
    if _is_in_memory_sqlite(database_url):
        engine_options["poolclass"] = StaticPool

    engine = create_engine(database_url, **engine_options)
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


engine: Engine = build_engine(DATABASE_URL)

# autoflush is off: the service layer flushes and commits explicitly.
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, rolled back on error, always closed.

    The service layer owns commits; this dependency never commits implicitly.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()