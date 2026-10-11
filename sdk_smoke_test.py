"""Smoke test for the generated SDK.

Drives one session through its lifecycle with the SDK, then cross-checks the result against
a raw HTTP call to the same API. Run (backend running, SDK installed):

    env\\Scripts\\python sdk_smoke_test.py

Note: it creates one session titled "SDK smoke test" in the backend's database.
"""
import os
import sys
from collections.abc import Callable
from typing import Any
from pathlib import Path


import httpx

SDK_ROOT = Path(__file__).resolve().parent / "deepwork_sdk"
sys.path.insert(0, str(SDK_ROOT))

from deepwork_sdk import ApiClient, Configuration
from deepwork_sdk.api.sessions_api import SessionsApi
from deepwork_sdk.exceptions import ApiException
from deepwork_sdk.models import PauseRequest, SessionCreate

BASE_URL: str = os.getenv("DEEPWORK_API_URL", "http://localhost:8000")
SMOKE_TITLE: str = "SDK smoke test"
SMOKE_DURATION_MINUTES: int = 50
UNKNOWN_SESSION_ID: int = 999_999_999
HTTP_TIMEOUT_SECONDS: float = 10.0


def enum_value(value: Any) -> Any:
    """Generated enums expose .value; plain strings pass through."""
    return getattr(value, "value", value)


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"  ok  {message}")


def expect_http_error(expected_status: int, label: str, call: Callable[[], Any]) -> None:
    try:
        call()
    except ApiException as exc:
        expect(exc.status == expected_status, f"{label} -> HTTP {expected_status}")
        return
    raise AssertionError(f"{label}: expected HTTP {expected_status} but the call succeeded")


def run() -> None:
    configuration = Configuration(host=BASE_URL)
    with ApiClient(configuration) as client:
        api = SessionsApi(client)

        created = api.schedule_session(
            session_create=SessionCreate(
                title=SMOKE_TITLE,
                duration=SMOKE_DURATION_MINUTES,
                goal="Verify the generated client",
            )
        )
        session_id: int = created.id
        expect(enum_value(created.status) == "scheduled", "schedule_session -> scheduled")

        started = api.start_session(session_id=session_id)
        expect(enum_value(started.status) == "active", "start_session -> active")

        paused = api.pause_session(
            session_id=session_id, pause_request=PauseRequest(reason="SDK coffee break")
        )
        expect(enum_value(paused.status) == "paused", "pause_session -> paused")
        expect(paused.pause_count == 1, "pause_session records one interruption")
        expect(paused.interruptions[0].reason == "SDK coffee break", "interruption reason stored")

        resumed = api.resume_session(session_id=session_id)
        expect(enum_value(resumed.status) == "active", "resume_session -> active")

        completed = api.complete_session(session_id=session_id)
        expect(enum_value(completed.status) == "completed", "complete_session -> completed")

        expect_http_error(
            409, "start_session on a completed session", lambda: api.start_session(session_id=session_id)
        )
        expect_http_error(
            404,
            "start_session on an unknown id",
            lambda: api.start_session(session_id=UNKNOWN_SESSION_ID),
        )

        sdk_history = api.get_session_history()
        raw_history = httpx.get(f"{BASE_URL}/sessions/history", timeout=HTTP_TIMEOUT_SECONDS)
        raw_history.raise_for_status()
        raw = raw_history.json()

        sdk_item = next((item for item in sdk_history.sessions if item.id == session_id), None)
        raw_item = next((item for item in raw["sessions"] if item["id"] == session_id), None)
        expect(sdk_item is not None and raw_item is not None, "session appears in both histories")
        assert sdk_item is not None and raw_item is not None  # narrows types for readers

        expect(len(sdk_history.sessions) == len(raw["sessions"]), "session counts match raw HTTP")
        expect(sdk_history.summary.total_sessions == raw["summary"]["total_sessions"], "summary total matches")
        expect(enum_value(sdk_item.status) == raw_item["status"] == "completed", "status matches raw HTTP")
        expect(sdk_item.pause_count == raw_item["pause_count"] == 1, "pause_count matches raw HTTP")
        expect(sdk_item.title == raw_item["title"] == SMOKE_TITLE, "title matches raw HTTP")
        expect(
            sdk_item.scheduled_duration == raw_item["scheduled_duration"] == SMOKE_DURATION_MINUTES,
            "scheduled_duration matches raw HTTP",
        )


def main() -> int:
    print(f"Testing the generated SDK against {BASE_URL}")
    try:
        run()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        return 1
    except (AttributeError, TypeError) as exc:
        print(f"FAIL: the generated SDK differs from what this test expects: {exc}")
        print("Inspect deepwork_sdk/docs/SessionsApi.md for the real method signatures.")
        return 1
    except Exception as exc:  # connection refused, timeouts, unexpected API errors
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1
    print("SDK smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())