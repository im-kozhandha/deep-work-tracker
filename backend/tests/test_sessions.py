"""HTTP-level tests for the six endpoints. Every test runs on a fresh in-memory database."""
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.services import session_service
from backend.services.exceptions import PersistenceError
from backend.tests.helpers import (
    TERMINAL_STATE_NAMES,
    TRANSITION_ACTIONS,
    ApiHelper,
    FakeClock,
    interrupt_session,
    make_terminal_session,
    parse_ts,
)

VALID_CREATE_PAYLOAD: dict[str, Any] = {"title": "Write report", "duration": 50}

INVALID_CREATE_PAYLOADS = [
    pytest.param({"duration": 50}, id="missing-title"),
    pytest.param({"title": None, "duration": 50}, id="null-title"),
    pytest.param({"title": "", "duration": 50}, id="empty-title"),
    pytest.param({"title": "   ", "duration": 50}, id="blank-title"),
    pytest.param({"title": "x" * 201, "duration": 50}, id="title-too-long"),
    pytest.param({"title": "x"}, id="missing-duration"),
    pytest.param({"title": "x", "duration": 0}, id="zero-duration"),
    pytest.param({"title": "x", "duration": -5}, id="negative-duration"),
    pytest.param({"title": "x", "duration": 1441}, id="duration-above-cap"),
    pytest.param({"title": "x", "duration": "abc"}, id="non-numeric-duration"),
    pytest.param({"title": "x", "duration": 1.5}, id="fractional-duration"),
    pytest.param({"title": "x", "duration": 50, "goal": "g" * 1001}, id="goal-too-long"),
]


class TestScheduleSession:
    def test_returns_201_and_a_scheduled_session(self, api: ApiHelper, clock: FakeClock) -> None:
        response = api.client.post(
            "/sessions/", json={**VALID_CREATE_PAYLOAD, "goal": "Finish the intro"}
        )
        assert response.status_code == 201
        body = response.json()
        assert body["id"] >= 1
        assert body["title"] == "Write report"
        assert body["goal"] == "Finish the intro"
        assert body["scheduled_duration"] == 50
        assert body["status"] == "scheduled"
        assert body["start_time"] is None
        assert body["end_time"] is None
        assert body["pause_count"] == 0
        assert body["interruptions"] == []
        assert parse_ts(body["created_at"]) == clock.now

    def test_goal_is_optional(self, api: ApiHelper) -> None:
        assert api.create()["goal"] is None

    def test_blank_goal_is_stored_as_null_and_title_is_trimmed(self, api: ApiHelper) -> None:
        body = api.create(title="  Deep work  ", goal="   ")
        assert body["title"] == "Deep work"
        assert body["goal"] is None

    @pytest.mark.parametrize("duration", [1, 1440])
    def test_duration_boundaries_are_accepted(self, api: ApiHelper, duration: int) -> None:
        assert api.create(duration=duration)["scheduled_duration"] == duration

    @pytest.mark.parametrize("payload", INVALID_CREATE_PAYLOADS)
    def test_invalid_payload_returns_422_and_saves_nothing(
        self, api: ApiHelper, payload: dict[str, Any]
    ) -> None:
        response = api.client.post("/sessions/", json=payload)
        assert response.status_code == 422
        assert api.history_json()["sessions"] == []

    def test_created_session_appears_in_history(self, api: ApiHelper) -> None:
        created = api.create(title="Persisted")
        item = api.history_item(created["id"])
        assert item["title"] == "Persisted"
        assert item["status"] == "scheduled"


class TestStartSession:
    def test_scheduled_session_becomes_active_with_start_time(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        session_id = api.create()["id"]
        clock.advance(minutes=3)
        body = api.start_ok(session_id)
        assert body["status"] == "active"
        assert parse_ts(body["start_time"]) == clock.now
        assert body["end_time"] is None

    def test_starting_twice_returns_409(self, api: ApiHelper) -> None:
        session_id = api.create_active()
        response = api.start(session_id)
        assert response.status_code == 409
        assert response.json()["detail"] == (
            f"Cannot start session {session_id}: status is 'active', expected 'scheduled'."
        )


class TestPauseSession:
    def test_active_session_becomes_paused_and_records_interruption(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        session_id = api.create_active()
        clock.advance(minutes=10)
        body = api.pause_ok(session_id, "Phone call")
        assert body["status"] == "paused"
        assert body["pause_count"] == 1
        assert len(body["interruptions"]) == 1
        interruption = body["interruptions"][0]
        assert interruption["reason"] == "Phone call"
        assert parse_ts(interruption["pause_time"]) == clock.now
        assert interruption["resume_time"] is None

    def test_reason_is_trimmed(self, api: ApiHelper) -> None:
        session_id = api.create_active()
        body = api.pause_ok(session_id, "  Phone call  ")
        assert body["interruptions"][0]["reason"] == "Phone call"

    def test_scheduled_session_cannot_be_paused(self, api: ApiHelper) -> None:
        session_id = api.create()["id"]
        response = api.pause(session_id)
        assert response.status_code == 409
        assert response.json()["detail"] == (
            f"Cannot pause session {session_id}: status is 'scheduled', expected 'active'."
        )

    def test_paused_session_cannot_be_paused_again(self, api: ApiHelper) -> None:
        session_id = api.create_active()
        api.pause_ok(session_id)
        assert api.pause(session_id).status_code == 409
        assert api.history_item(session_id)["pause_count"] == 1

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param(None, id="no-body"),
            pytest.param({}, id="empty-object"),
            pytest.param({"reason": ""}, id="empty-reason"),
            pytest.param({"reason": "   "}, id="blank-reason"),
            pytest.param({"reason": None}, id="null-reason"),
            pytest.param({"reason": "x" * 501}, id="reason-too-long"),
        ],
    )
    def test_missing_or_invalid_reason_returns_422(
        self, api: ApiHelper, body: dict[str, Any] | None
    ) -> None:
        session_id = api.create_active()
        response = api.client.patch(f"/sessions/{session_id}/pause", json=body)
        assert response.status_code == 422
        item = api.history_item(session_id)
        assert item["status"] == "active"
        assert item["pause_count"] == 0


class TestResumeSession:
    def test_paused_session_becomes_active_and_keeps_history(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        session_id = api.create_active()
        clock.advance(minutes=10)
        paused_at = clock.now
        api.pause_ok(session_id, "Coffee")
        clock.advance(minutes=5)
        body = api.resume_ok(session_id)
        assert body["status"] == "active"
        assert body["pause_count"] == 1
        interruption = body["interruptions"][0]
        assert interruption["reason"] == "Coffee"
        assert parse_ts(interruption["pause_time"]) == paused_at
        assert parse_ts(interruption["resume_time"]) == clock.now

    def test_scheduled_session_cannot_be_resumed(self, api: ApiHelper) -> None:
        session_id = api.create()["id"]
        assert api.resume(session_id).status_code == 409

    def test_active_session_cannot_be_resumed(self, api: ApiHelper) -> None:
        session_id = api.create_active()
        response = api.resume(session_id)
        assert response.status_code == 409
        assert response.json()["detail"] == (
            f"Cannot resume session {session_id}: status is 'active', expected 'paused'."
        )


class TestCompleteSession:
    def test_active_session_within_limit_is_completed(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        session_id = api.create_active()
        started_at = clock.now
        clock.advance(minutes=30)
        body = api.complete_ok(session_id)
        assert body["status"] == "completed"
        assert parse_ts(body["start_time"]) == started_at
        assert parse_ts(body["end_time"]) == clock.now

    def test_scheduled_session_cannot_be_completed(self, api: ApiHelper) -> None:
        session_id = api.create()["id"]
        assert api.complete(session_id).status_code == 409

    def test_paused_session_cannot_be_completed(self, api: ApiHelper) -> None:
        session_id = api.create_active()
        api.pause_ok(session_id)
        response = api.complete(session_id)
        assert response.status_code == 409
        assert response.json()["detail"] == (
            f"Cannot complete session {session_id}: status is 'paused', expected 'active'."
        )

    def test_completed_session_cannot_be_completed_again(self, api: ApiHelper) -> None:
        session_id = api.create_active()
        api.complete_ok(session_id)
        response = api.complete(session_id)
        assert response.status_code == 409
        assert response.json()["detail"] == (
            f"Cannot complete session {session_id}: it is in terminal state 'completed'."
        )


class TestMissingAndInvalidIds:
    @pytest.mark.parametrize("action", TRANSITION_ACTIONS)
    def test_unknown_id_returns_404(self, api: ApiHelper, action: str) -> None:
        response = api.act(999, action)
        assert response.status_code == 404
        assert response.json() == {"detail": "Session 999 not found."}

    @pytest.mark.parametrize("action", TRANSITION_ACTIONS)
    @pytest.mark.parametrize("bad_id", ["0", "-1", "abc"])
    def test_invalid_id_returns_422(self, api: ApiHelper, action: str, bad_id: str) -> None:
        assert api.act(bad_id, action).status_code == 422


class TestTerminalStatesAreConsistent:
    @pytest.mark.parametrize("action", TRANSITION_ACTIONS)
    @pytest.mark.parametrize("state", TERMINAL_STATE_NAMES)
    def test_every_action_is_rejected_in_every_terminal_state(
        self, api: ApiHelper, clock: FakeClock, state: str, action: str
    ) -> None:
        session_id = make_terminal_session(api, clock, state)
        response = api.act(session_id, action)
        assert response.status_code == 409
        assert f"terminal state '{state}'" in response.json()["detail"]
        assert api.history_item(session_id)["status"] == state


class TestFullLifecycle:
    def test_create_start_pause_resume_complete(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create(title="Lifecycle", goal="Walk the happy path")["id"]
        assert api.history_item(session_id)["status"] == "scheduled"
        api.start_ok(session_id)
        clock.advance(minutes=10)
        api.pause_ok(session_id, "Stretch")
        clock.advance(minutes=5)
        api.resume_ok(session_id)
        clock.advance(minutes=20)
        body = api.complete_ok(session_id)
        assert body["status"] == "completed"
        assert body["pause_count"] == 1
        item = api.history_item(session_id)
        assert item["status"] == "completed"
        assert item["interruptions"][0]["reason"] == "Stretch"

    def test_three_pauses_do_not_interrupt_a_session(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active()
        for pause_number in (1, 2, 3):
            clock.advance(minutes=2)
            assert api.pause_ok(session_id, f"Pause {pause_number}")["status"] == "paused"
            clock.advance(minutes=1)
            assert api.resume_ok(session_id)["status"] == "active"
        body = api.complete_ok(session_id)
        assert body["status"] == "completed"
        assert body["pause_count"] == 3

    def test_fourth_pause_interrupts_the_session(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active()
        body = interrupt_session(api, clock, session_id)
        assert body["status"] == "interrupted"
        assert body["pause_count"] == 4
        assert parse_ts(body["end_time"]) == clock.now


class TestHistory:
    def test_empty_history_is_valid(self, api: ApiHelper) -> None:
        body = api.history_json()
        assert body["sessions"] == []
        summary = body["summary"]
        assert summary["total_sessions"] == 0
        assert summary["completed_count"] == 0
        assert summary["completion_rate"] == 0.0
        assert summary["total_interruptions"] == 0
        assert summary["total_focused_seconds"] == 0
        assert summary["average_focused_seconds_completed"] is None
        assert summary["status_counts"] == {
            "scheduled": 0,
            "active": 0,
            "paused": 0,
            "completed": 0,
            "interrupted": 0,
            "abandoned": 0,
            "overdue": 0,
        }

    def test_sessions_are_listed_newest_first(self, api: ApiHelper, clock: FakeClock) -> None:
        first = api.create(title="first")["id"]
        clock.advance(minutes=1)
        second = api.create(title="second")["id"]
        clock.advance(minutes=1)
        third = api.create(title="third")["id"]
        assert [item["id"] for item in api.history_json()["sessions"]] == [third, second, first]

    def test_equal_creation_times_are_ordered_by_id_descending(self, api: ApiHelper) -> None:
        ids = [api.create(title=f"s{index}")["id"] for index in range(3)]
        assert [item["id"] for item in api.history_json()["sessions"]] == list(reversed(ids))

    def test_scheduled_session_has_no_timing(self, api: ApiHelper) -> None:
        item = api.history_item(api.create()["id"])
        assert item["elapsed_seconds"] is None
        assert item["focused_seconds"] is None
        assert item["paused_seconds"] == 0

    def test_active_session_timing_runs_up_to_now(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active()
        clock.advance(minutes=7)
        item = api.history_item(session_id)
        assert item["end_time"] is None
        assert item["elapsed_seconds"] == 420
        assert item["paused_seconds"] == 0
        assert item["focused_seconds"] == 420

    def test_open_pause_counts_as_paused_up_to_now(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active()
        clock.advance(minutes=10)
        api.pause_ok(session_id)
        clock.advance(minutes=5)
        item = api.history_item(session_id)
        assert item["status"] == "paused"
        assert item["elapsed_seconds"] == 900
        assert item["paused_seconds"] == 300
        assert item["focused_seconds"] == 600

    def test_completed_session_timing_and_summary(self, api: ApiHelper, clock: FakeClock) -> None:
        session_id = api.create_active()
        clock.advance(minutes=10)
        api.pause_ok(session_id, "Break")
        clock.advance(minutes=5)
        api.resume_ok(session_id)
        clock.advance(minutes=20)
        api.complete_ok(session_id)

        body = api.history_json()
        item = body["sessions"][0]
        assert item["status"] == "completed"
        assert item["elapsed_seconds"] == 2100
        assert item["paused_seconds"] == 300
        assert item["focused_seconds"] == 1800

        summary = body["summary"]
        assert summary["total_sessions"] == 1
        assert summary["completed_count"] == 1
        assert summary["completion_rate"] == 100.0
        assert summary["total_interruptions"] == 1
        assert summary["total_focused_seconds"] == 1800
        assert summary["average_focused_seconds_completed"] == 1800.0

    def test_history_lists_interruption_reasons_in_order(self, api: ApiHelper) -> None:
        session_id = api.create_active()
        api.pause_ok(session_id, "Phone")
        api.resume_ok(session_id)
        api.pause_ok(session_id, "Email")
        reasons = [i["reason"] for i in api.history_item(session_id)["interruptions"]]
        assert reasons == ["Phone", "Email"]

    def test_summary_counts_and_completion_rate_with_mixed_outcomes(
        self, api: ApiHelper, clock: FakeClock
    ) -> None:
        completed_id = api.create_active()
        clock.advance(minutes=10)
        api.complete_ok(completed_id)

        overdue_id = api.create_active()
        clock.advance(minutes=60)
        api.complete_ok(overdue_id)

        interrupted_id = api.create_active()
        interrupt_session(api, clock, interrupted_id)

        api.create(title="Never started")
        api.create_active()

        summary = api.history_json()["summary"]
        assert summary["total_sessions"] == 5
        assert summary["status_counts"] == {
            "scheduled": 1,
            "active": 1,
            "paused": 0,
            "completed": 1,
            "interrupted": 1,
            "abandoned": 0,
            "overdue": 1,
        }
        assert summary["completed_count"] == 1
        # 1 completed out of 3 terminal sessions (completed, overdue, interrupted).
        assert summary["completion_rate"] == 33.3
        assert summary["total_interruptions"] == 4
        # 600 (completed) + 3600 (overdue) + 240 (interrupted: 420 elapsed - 180 paused) + 0.
        assert summary["total_focused_seconds"] == 4440
        assert summary["average_focused_seconds_completed"] == 600.0


class TestServerErrors:
    def test_persistence_error_returns_500_with_its_message(
        self, api: ApiHelper, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def broken_create(*_args: Any, **_kwargs: Any) -> None:
            raise PersistenceError("A database error occurred while saving the session.")

        monkeypatch.setattr(session_service, "create_session", broken_create)
        response = api.client.post("/sessions/", json=VALID_CREATE_PAYLOAD)
        assert response.status_code == 500
        assert response.json() == {"detail": "A database error occurred while saving the session."}

    def test_unexpected_error_returns_generic_500_without_leaking_details(
        self, api: ApiHelper, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def exploding_history(*_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("secret internal detail")

        monkeypatch.setattr(session_service, "get_history", exploding_history)
        response = api.history()
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error."}
        assert "secret" not in response.text


class TestOpenApiAndCors:
    EXPECTED_OPERATIONS: dict[tuple[str, str], str] = {
        ("post", "/sessions/"): "schedule_session",
        ("get", "/sessions/history"): "get_session_history",
        ("patch", "/sessions/{session_id}/start"): "start_session",
        ("patch", "/sessions/{session_id}/pause"): "pause_session",
        ("patch", "/sessions/{session_id}/resume"): "resume_session",
        ("patch", "/sessions/{session_id}/complete"): "complete_session",
    }

    def test_openapi_exposes_exactly_the_six_operations(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        http_methods = {"get", "post", "patch", "put", "delete"}
        actual: dict[tuple[str, str], str] = {}
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if method in http_methods:
                    assert operation["tags"] == ["sessions"]
                    actual[(method, path)] = operation["operationId"]
        assert actual == self.EXPECTED_OPERATIONS

    def test_swagger_ui_is_served(self, client: TestClient) -> None:
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()

    def test_cors_preflight_allows_the_react_dev_server(self, client: TestClient) -> None:
        response = client.options(
            "/sessions/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"