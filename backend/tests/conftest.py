"""Pytest fixtures: isolated in-memory database, controllable clock, API helper.

The environment variables are set BEFORE any `backend` module is imported so the production
database file is never opened by the test run.
"""
import os

TEST_DATABASE_URL: str = "sqlite://"
TEST_ABANDONMENT_TIMEOUT_MINUTES: str = "30"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ABANDONMENT_TIMEOUT_MINUTES"] = TEST_ABANDONMENT_TIMEOUT_MINUTES
os.environ.pop("CORS_ALLOWED_ORIGINS", None)

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

import backend.database as database  # noqa: E402
import backend.models  # noqa: E402,F401  (registers tables on Base.metadata)
from backend.database import Base, build_engine, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.services import session_service  # noqa: E402
from backend.tests.helpers import CLOCK_START, ApiHelper, FakeClock  # noqa: E402

if database.DATABASE_URL != TEST_DATABASE_URL:
    raise RuntimeError(
        f"Tests must run against {TEST_DATABASE_URL!r}, but backend.database is bound to "
        f"{database.DATABASE_URL!r}. Refusing to run so the real database is not touched."
    )


@pytest.fixture(autouse=True)
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    """Freeze 'now' for the service layer; tests move it with clock.advance(...)."""
    fake_clock = FakeClock(CLOCK_START)
    monkeypatch.setattr(session_service, "utc_now", fake_clock)
    return fake_clock


@pytest.fixture()
def db_engine() -> Iterator[Engine]:
    """A fresh in-memory SQLite database with foreign keys on and all tables created."""
    engine = build_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A session for direct service-layer and database tests."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """TestClient whose get_db dependency points at the isolated test database."""

    def override_get_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # raise_server_exceptions=False lets tests assert on the generic 500 response.
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def api(client: TestClient) -> ApiHelper:
    return ApiHelper(client)