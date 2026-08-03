from unittest.mock import MagicMock, patch

with (
    patch("redis.from_url", return_value=MagicMock()),
    patch("sqlalchemy.create_engine", return_value=MagicMock()),
):
    from orchestrator.main import app


from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert "status" in data
    assert "timestamp" in data


def test_start_interview_invalid_candidate_id():
    response = client.post(
        "/start-interview",
        headers={"X-API-Token": "ci-test-token"},
        json={"candidate_id": "@@@###", "priority": "medium"},
    )

    assert response.status_code == 422


@patch("orchestrator.main.session_manager.get_session")
def test_session_status_not_found(mock_get_session):
    mock_get_session.return_value = None

    response = client.get("/session-status/fake-session-id")

    assert response.status_code == 404


def test_sync_to_database_without_token():
    response = client.post("/sync-to-database")

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid or missing API token"


def test_sync_to_database_with_token():
    response = client.post(
        "/sync-to-database",
        headers={"X-API-Token": "ci-test-token"},
    )

    assert response.status_code == 200


@patch("orchestrator.main.http_cache")
@patch("orchestrator.main.scheduler")
@patch("orchestrator.main.session_manager")
def test_start_interview_valid(
    mock_session_manager,
    mock_scheduler,
    mock_http_cache,
):
    mock_session_manager.QUEUED = "QUEUED"

    mock_session_manager.create_session.return_value = "session-123"

    mock_session_manager.update_session_status.return_value = None

    mock_session_manager.get_session.return_value = {"created_at": "2026-07-16T10:00:00Z"}

    mock_scheduler.can_accept_task.return_value = True

    mock_scheduler.schedule_task.return_value = None

    mock_scheduler.get_estimated_wait_time.return_value = 5

    mock_http_cache.invalidate.return_value = None

    response = client.post(
        "/start-interview",
        headers={"X-API-Token": "ci-test-token"},
        json={
            "candidate_id": "candidate-123",
            "priority": "medium",
        },
    )

    assert response.status_code == 200
