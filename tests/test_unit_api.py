from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from orchestrator.audit_logger import AuditLogger

with (
    patch("redis.from_url", return_value=MagicMock()),
    patch("sqlalchemy.create_engine", return_value=MagicMock()),
):
    from orchestrator.main import app

from database.db import Base, get_db
from database.models import Candidate, InterviewSchedule
from routers.schedule import create_schedule_routes

client = TestClient(app)


# ---------------------------------------------------------------------------
# Existing API tests
# ---------------------------------------------------------------------------


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert "status" in data
    assert "timestamp" in data


@patch("orchestrator.main.scheduler.can_accept_task", return_value=True)
def test_start_interview_invalid_candidate_id(mock_capacity):
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
    assert response.json()["detail"] == "Invalid or missing authentication"


def test_sync_to_database_with_token():
    response = client.post(
        "/sync-to-database",
        headers={"X-API-Token": "ci-test-token"},
    )

    assert response.status_code == 200


def test_admin_audit_events_contain_actor_action_and_timestamp():
    audit_logger = AuditLogger()

    audit_logger.log_admin_action(
        action="clear-cache",
        actor="admin@example.com",
    )
    audit_logger.log_admin_action(
        action="sync-to-database",
        actor="admin@example.com",
        details={"session_id": "session-123"},
    )

    events = audit_logger.get_recent_events(limit=2)

    assert len(events) == 2

    clear_cache_event = events[1]
    sync_event = events[0]

    assert clear_cache_event["actor"] == "admin@example.com"
    assert clear_cache_event["target"] == "clear-cache"
    assert clear_cache_event["event_type"] == "ADMIN_ACTION"
    assert clear_cache_event["timestamp"]

    assert sync_event["actor"] == "admin@example.com"
    assert sync_event["target"] == "sync-to-database"
    assert sync_event["event_type"] == "ADMIN_ACTION"
    assert sync_event["timestamp"]


def test_sync_to_database_audit_uses_authenticated_actor():
    from orchestrator.security import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "role": "admin",
        "user_id": "admin-123",
        "email": "admin@example.com",
    }

    try:
        with patch(
            "orchestrator.main.audit_logger.log_admin_action"
        ) as mock_log_admin_action:
            with patch(
                "orchestrator.main.state_sync.get_active_sessions",
                return_value=[],
            ):
                response = client.post("/sync-to-database")

        assert response.status_code == 200

        mock_log_admin_action.assert_called_once()

        call = mock_log_admin_action.call_args.kwargs

        assert call["action"] == "sync-to-database"
        assert call["actor"] == "admin@example.com"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_risk_config_returns_live_values(monkeypatch):
    monkeypatch.setenv("RISK_VIDEO_WEIGHT", "0.5")
    monkeypatch.setenv("RISK_AUDIO_WEIGHT", "0.25")
    monkeypatch.setenv("RISK_EVALUATION_WEIGHT", "0.25")

    monkeypatch.setenv("RISK_LOW_RISK_THRESHOLD", "0.2")
    monkeypatch.setenv("RISK_MEDIUM_RISK_THRESHOLD", "0.5")
    monkeypatch.setenv("RISK_HIGH_RISK_THRESHOLD", "0.75")

    response = client.get("/api/admin/risk-config")

    assert response.status_code == 200

    data = response.json()

    assert data["pipeline_weights"] == {
        "video": 0.5,
        "audio": 0.25,
        "evaluation": 0.25,
    }

    assert data["thresholds"] == {
        "low": 0.2,
        "medium": 0.5,
        "high": 0.75,
    }

    assert "multiple_persons" in data["video_factors"]
    assert "phone_detected" in data["video_factors"]
    assert "suspicious_head_movement" in data["video_factors"]
    assert "no_face_detected" in data["video_factors"]

    assert "background_voices" in data["audio_factors"]
    assert "suspicious_pattern" in data["audio_factors"]
    assert "no_transcription" in data["audio_factors"]

    assert "low_quality_answers" in data["evaluation_factors"]
    assert "low_accuracy" in data["evaluation_factors"]
    assert "poor_communication" in data["evaluation_factors"]
    assert "hallucination" in data["evaluation_factors"]


@patch("orchestrator.http_cache.invalidate")
@patch("orchestrator.main.scheduler.get_estimated_wait_time")
@patch("orchestrator.main.scheduler.schedule_task")
@patch("orchestrator.main.scheduler.can_accept_task")
@patch("orchestrator.main.session_manager.get_session")
@patch("orchestrator.main.session_manager.update_session_status")
@patch("orchestrator.main.session_manager.create_session")
def test_start_interview_valid(
    mock_create_session,
    mock_update_session_status,
    mock_get_session,
    mock_can_accept_task,
    mock_schedule_task,
    mock_get_estimated_wait_time,
    mock_invalidate,
):
    mock_create_session.return_value = "session-123"
    mock_update_session_status.return_value = None
    mock_get_session.return_value = {"created_at": "2026-07-16T10:00:00Z"}
    mock_can_accept_task.return_value = True
    mock_schedule_task.return_value = None
    mock_get_estimated_wait_time.return_value = 5
    mock_invalidate.return_value = None

    response = client.post(
        "/start-interview",
        headers={"X-API-Token": "ci-test-token"},
        json={
            "candidate_id": "candidate-123",
            "priority": "medium",
        },
    )

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Issue #19 - Schedule API tests
# ---------------------------------------------------------------------------

schedule_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

ScheduleTestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=schedule_engine,
)

schedule_test_app = FastAPI()
schedule_test_app.include_router(create_schedule_routes())


@pytest.fixture
def schedule_db():
    Base.metadata.create_all(bind=schedule_engine)

    session = ScheduleTestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=schedule_engine)


@pytest.fixture
def schedule_client(schedule_db):
    def override_get_db():
        yield schedule_db

    schedule_test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(schedule_test_app) as test_client:
        yield test_client

    schedule_test_app.dependency_overrides.clear()


@pytest.fixture
def schedule_candidate(schedule_db):
    candidate = Candidate(
        candidate_id="test-candidate-19",
        name="Test Candidate",
        email="test@example.com",
    )

    schedule_db.add(candidate)
    schedule_db.commit()

    return candidate


def test_schedule_create_valid(schedule_client, schedule_candidate):
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    response = schedule_client.post(
        "/api/schedule",
        json={
            "candidate_id": schedule_candidate.candidate_id,
            "interviewer_id": "interviewer-1",
            "scheduled_at": future_time,
            "notes": "Technical interview",
            "send_email": False,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert "schedule" in data

    schedule_data = data["schedule"]

    assert "id" in schedule_data
    assert schedule_data["candidate_id"] == schedule_candidate.candidate_id
    assert schedule_data["interviewer_id"] == "interviewer-1"


def test_schedule_create_candidate_not_found(schedule_client):
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    response = schedule_client.post(
        "/api/schedule",
        json={
            "candidate_id": "does-not-exist",
            "interviewer_id": "interviewer-1",
            "scheduled_at": future_time,
            "send_email": False,
        },
    )

    assert response.status_code == 404


def test_schedule_create_past_datetime(schedule_client, schedule_candidate):
    past_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    response = schedule_client.post(
        "/api/schedule",
        json={
            "candidate_id": schedule_candidate.candidate_id,
            "interviewer_id": "interviewer-1",
            "scheduled_at": past_time,
            "send_email": False,
        },
    )

    assert response.status_code == 400
    assert "future" in response.json()["detail"].lower()


def test_schedule_list(schedule_client, schedule_db, schedule_candidate):
    future_time = datetime.now(timezone.utc) + timedelta(days=1)

    schedule = InterviewSchedule(
        id="schedule-list-1",
        candidate_id=schedule_candidate.candidate_id,
        interviewer_id="interviewer-1",
        scheduled_at=future_time,
        status="scheduled",
    )

    schedule_db.add(schedule)
    schedule_db.commit()

    response = schedule_client.get("/api/schedule")

    assert response.status_code == 200

    data = response.json()

    assert "schedules" in data
    assert any(item["id"] == "schedule-list-1" for item in data["schedules"])


def test_schedule_upcoming(schedule_client, schedule_db, schedule_candidate):
    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="schedule-upcoming-1",
        candidate_id=schedule_candidate.candidate_id,
        interviewer_id="interviewer-1",
        scheduled_at=future_time,
        status="scheduled",
    )

    schedule_db.add(schedule)
    schedule_db.commit()

    response = schedule_client.get("/api/schedule/upcoming")

    assert response.status_code == 200

    data = response.json()

    assert "upcoming" in data
    assert any(item["id"] == "schedule-upcoming-1" for item in data["upcoming"])


def test_schedule_get_not_found(schedule_client):
    response = schedule_client.get(
        "/api/schedule/non-existent-schedule",
    )

    assert response.status_code == 404


def test_schedule_update_valid(
    schedule_client,
    schedule_db,
    schedule_candidate,
):
    future_time = datetime.now(timezone.utc) + timedelta(days=1)

    schedule = InterviewSchedule(
        id="schedule-update-1",
        candidate_id=schedule_candidate.candidate_id,
        interviewer_id="interviewer-1",
        scheduled_at=future_time,
        status="scheduled",
    )

    schedule_db.add(schedule)
    schedule_db.commit()

    response = schedule_client.patch(
        "/api/schedule/schedule-update-1",
        json={
            "status": "completed",
            "notes": "Interview completed",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["schedule"]["id"] == "schedule-update-1"
    assert data["schedule"]["status"] == "completed"
    assert data["schedule"]["notes"] == "Interview completed"


def test_schedule_update_invalid_status(
    schedule_client,
    schedule_db,
    schedule_candidate,
):
    future_time = datetime.now(timezone.utc) + timedelta(days=1)

    schedule = InterviewSchedule(
        id="schedule-invalid-status",
        candidate_id=schedule_candidate.candidate_id,
        interviewer_id="interviewer-1",
        scheduled_at=future_time,
        status="scheduled",
    )

    schedule_db.add(schedule)
    schedule_db.commit()

    response = schedule_client.patch(
        "/api/schedule/schedule-invalid-status",
        json={"status": "invalid-status"},
    )

    assert response.status_code == 400
    assert "Allowed statuses" in response.json()["detail"]
