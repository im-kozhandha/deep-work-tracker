"""Shared test helpers: controllable clock, API wrapper and scenario builders."""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response

from backend.services.session_service import INTERRUPTION_PAUSE_LIMIT

CLOCK_START: datetime = datetime(2026, 1, 5, 9, 0, 0, tzinfo=timezone.utc)
TERMINAL_STATE_NAMES: tuple[str, ...] = ("completed", "overdue", "interrupted", "abandoned")
TRANSITION_ACTIONS: tuple[str, ...] = ("start", "pause", "resume", "complete")


class FakeClock:
    """A clock that only moves when a test advances it."""

    def __init__(self, start: datetime) -> None:
        self._now: datetime = start

    @property
    def now(self) -> datetime:
        return self._now

    def __call__(self) -> datetime:
        return self._now

    def advance(self, **delta_kwargs: float) -> datetime:
        """Advance by timedelta keyword arguments, e.g. advance(minutes=5)."""
        self._now += timedelta(**delta_kwargs)
        return self._now


def parse_ts(value: str) -> datetime:
    """Parse an ISO-8601 timestamp from the API (accepts a trailing 'Z' on Python 3.10)."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ApiHelper:
    """Thin wrapper over TestClient. Plain methods return the raw Response;
    *_ok methods assert HTTP 200 and return the JSON body."""

    def __init__(self, client: TestClient) -> None:
        self.client: TestClient = client

    def create(
        self, *, title: str = "Focus block", duration: int = 50, goal: str | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title, "duration": duration}
        if goal is not None:
            payload["goal"] = goal
        response = self.client.post("/sessions/", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    def start(self, session_id: Any) -> Response:
        return self.client.patch(f"/sessions/{session_id}/start")

    def pause(self, session_id: Any, reason: str = "Short break") -> Response:
        return self.client.patch(f"/sessions/{session_id}/pause", json={"reason": reason})

    def resume(self, session_id: Any) -> Response:
        return self.client.patch(f"/sessions/{session_id}/resume")

    def complete(self, session_id: Any) -> Response:
        return self.client.patch(f"/sessions/{session_id}/complete")

    def act(self, session_id: Any, action: str) -> Response:
        """Call any of the four PATCH actions by name."""
        if action == "pause":
            return self.pause(session_id)
        return self.client.patch(f"/sessions/{session_id}/{action}")

    def history(self) -> Response:
        return self.client.get("/sessions/history")

    def history_json(self) -> dict[str, Any]:
        response = self.history()
        assert response.status_code == 200, response.text
        return response.json()

    def history_item(self, session_id: int) -> dict[str, Any]:
        for item in self.history_json()["sessions"]:
            if item["id"] == session_id:
                return item
        raise AssertionError(f"Session {session_id} not found in history.")

    def start_ok(self, session_id: int) -> dict[str, Any]:
        response = self.start(session_id)
        assert response.status_code == 200, response.text
        return response.json()

    def pause_ok(self, session_id: int, reason: str = "Short break") -> dict[str, Any]:
        response = self.pause(session_id, reason)
        assert response.status_code == 200, response.text
        return response.json()

    def resume_ok(self, session_id: int) -> dict[str, Any]:
        response = self.resume(session_id)
        assert response.status_code == 200, response.text
        return response.json()

    def complete_ok(self, session_id: int) -> dict[str, Any]:
        response = self.complete(session_id)
        assert response.status_code == 200, response.text
        return response.json()

    def create_active(self, duration: int = 50) -> int:
        """Create and start a session; returns its id."""
        session_id: int = self.create(duration=duration)["id"]
        self.start_ok(session_id)
        return session_id


def interrupt_session(api: ApiHelper, clock: FakeClock, session_id: int) -> dict[str, Any]:
    """Pause an active session until it is interrupted. Resumes after each pause except the last.

    Advances the clock 1 minute before every pause and 1 minute before every resume.
    Returns the response body of the final (interrupting) pause.
    """
    final_body: dict[str, Any] = {}
    for pause_number in range(1, INTERRUPTION_PAUSE_LIMIT + 2):
        clock.advance(minutes=1)
        final_body = api.pause_ok(session_id, f"Interruption {pause_number}")
        if pause_number <= INTERRUPTION_PAUSE_LIMIT:
            assert final_body["status"] == "paused"
            clock.advance(minutes=1)
            api.resume_ok(session_id)
    assert final_body["status"] == "interrupted"
    return final_body


def make_terminal_session(api: ApiHelper, clock: FakeClock, state: str) -> int:
    """Drive a fresh 50-minute session into the given terminal state; returns its id.

    For 'abandoned' the pause deadline has passed but nothing has touched the session yet,
    so it is still stored as 'paused' until the next request or history call.
    """
    session_id = api.create_active(duration=50)
    if state == "completed":
        clock.advance(minutes=10)
        assert api.complete_ok(session_id)["status"] == "completed"
    elif state == "overdue":
        clock.advance(minutes=60)
        assert api.complete_ok(session_id)["status"] == "overdue"
    elif state == "interrupted":
        interrupt_session(api, clock, session_id)
    elif state == "abandoned":
        clock.advance(minutes=5)
        api.pause_ok(session_id, "Left the desk")
        clock.advance(minutes=30)
    else:
        raise ValueError(f"Unknown terminal state: {state!r}")
    return session_id