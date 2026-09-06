"""Tests for Issue D4: integrity_score exposed via the session-status API.

Covers:
- integrity_score is present and correct in the session-status response
- it reflects tab-switch events ingested via POST /integrity/events
- it reflects video cheat-signal flags as soon as they're available
- it updates as more signal data comes in during a live session
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

with (
    patch("redis.from_url", return_value=MagicMock()),
    patch("sqlalchemy.create_engine", return_value=MagicMock()),
):
    from orchestrator.main import app

import routers.integrity as integrity_module

client = TestClient(app)


def _base_session_data(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "candidate_id": "cand-1",
        "status": "PROCESSING",
        "risk_score": None,
        "assigned_node": "node-1",
        "start_time": None,
        "end_time": None,
        "updated_at": None,
    }


def setup_function():
    """Ensure no integrity events leak between tests."""
    integrity_module.integrity_events.clear()


@patch("orchestrator.main.session_manager.get_session")
def test_integrity_score_perfect_with_no_signals(mock_get_session):
    session_id = "session_no_signals"
    mock_get_session.return_value = _base_session_data(session_id)

    response = client.get(f"/session-status/{session_id}")

    assert response.status_code == 200
    body = response.json()
    assert "integrity_score" in body
    assert body["integrity_score"] == 100


@patch("orchestrator.main.session_manager.get_session")
def test_integrity_score_reflects_tab_switch_events(mock_get_session):
    session_id = "session_tab_switches"
    mock_get_session.return_value = _base_session_data(session_id)

    for _ in range(2):
        r = client.post(
            "/integrity/events",
            json={"session_id": session_id, "event_type": "tab_switch"},
        )
        assert r.status_code == 200

    response = client.get(f"/session-status/{session_id}")

    assert response.status_code == 200
    # 2 tab switches * 5 penalty = 10 -> 100 - 10 = 90
    assert response.json()["integrity_score"] == 90


@patch("orchestrator.main.session_manager.get_session")
def test_integrity_score_reflects_live_video_flags(mock_get_session):
    session_id = "session_video_flags"
    session_data = _base_session_data(session_id)
    # Video stage has completed but the rest of the pipeline hasn't -
    # this is the "live", pre-completion shape written by workers/tasks.py.
    session_data["video_result"] = {
        "phone_detected": {"phone_detected": True},
        "face_detected": {"faces_found": True},
    }
    mock_get_session.return_value = session_data

    response = client.get(f"/session-status/{session_id}")

    assert response.status_code == 200
    # 1 cv flag * 10 penalty = 10 -> 100 - 10 = 90
    assert response.json()["integrity_score"] == 90


@patch("orchestrator.main.session_manager.get_session")
def test_integrity_score_reflects_final_risk_score(mock_get_session):
    session_id = "session_final_risk"
    session_data = _base_session_data(session_id)
    session_data["status"] = "COMPLETED"
    session_data["risk_score"] = 0.5
    mock_get_session.return_value = session_data

    response = client.get(f"/session-status/{session_id}")

    assert response.status_code == 200
    # risk_score 0.5 -> 25 penalty -> 100 - 25 = 75
    assert response.json()["integrity_score"] == 75


@patch("orchestrator.main.session_manager.get_session")
def test_integrity_score_updates_as_new_signals_arrive(mock_get_session):
    """Simulates a live session: the score should change as more anti-cheat
    signal data comes in, without any new session being created."""
    session_id = "session_live_updates"
    session_data = _base_session_data(session_id)
    mock_get_session.return_value = session_data

    first = client.get(f"/session-status/{session_id}")
    assert first.json()["integrity_score"] == 100

    # A tab-switch event comes in mid-session.
    client.post(
        "/integrity/events",
        json={"session_id": session_id, "event_type": "tab_switch"},
    )
    second = client.get(f"/session-status/{session_id}")
    assert second.json()["integrity_score"] == 95

    # The video pipeline stage completes and flags a phone.
    session_data["video_result"] = {"phone_detected": {"phone_detected": True}}
    third = client.get(f"/session-status/{session_id}")
    assert third.json()["integrity_score"] == 85
