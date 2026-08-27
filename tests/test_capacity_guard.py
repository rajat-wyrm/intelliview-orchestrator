from unittest.mock import patch

from fastapi.testclient import TestClient

from orchestrator.main import app


def test_returns_503_when_no_workers_available():
    from config import API_TOKEN

    client = TestClient(app)
    with (
        patch("orchestrator.main.session_manager") as mock_session_manager,
        patch("orchestrator.main.scheduler") as mock_scheduler,
    ):
        mock_session_manager.create_session.return_value = "session_test123"
        mock_scheduler.can_accept_task.return_value = False
        response = client.post(
            "/start-interview",
            json={"candidate_id": "test123"},
            headers={"X-API-Token": API_TOKEN},
        )
    assert response.status_code == 503
    assert response.headers.get("Retry-After") == "5"
    body = response.json()
    assert body["error"] == "service_unavailable"


def test_capacity_check_exception_fails_safe_to_503():
    from config import API_TOKEN

    client = TestClient(app)
    with (
        patch("orchestrator.main.session_manager") as mock_session_manager,
        patch("orchestrator.main.scheduler") as mock_scheduler,
    ):
        mock_session_manager.create_session.return_value = "session_test456"
        mock_scheduler.can_accept_task.side_effect = RuntimeError("redis down")
        response = client.post(
            "/start-interview",
            json={"candidate_id": "test456"},
            headers={"X-API-Token": API_TOKEN},
        )
    assert response.status_code == 503