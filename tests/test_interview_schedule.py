"""
Unit and integration tests for Interview Scheduling and Email Notification System.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Index, UniqueConstraint, create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from database.db import Base, get_db
from database.models import Candidate, InterviewSchedule, Notification
from orchestrator.email_service import EmailService
from routers.schedule import create_schedule_routes

# Create clean testing app with in-memory SQLite engine
test_engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def normalize_utc(dt: datetime) -> datetime:
    """
    Normalize a datetime to timezone-aware UTC.

    SQLite may return DateTime values without timezone information,
    even when the original Python datetime was timezone-aware.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


app = FastAPI()
app.include_router(create_schedule_routes())


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_interview_schedule_orm_model(db_session):
    """Test creating and querying InterviewSchedule model."""

    candidate = Candidate(
        candidate_id="cand_test_101",
        name="John Doe",
        email="john.doe@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    scheduled_time = datetime.now(timezone.utc) + timedelta(days=1)

    schedule = InterviewSchedule(
        id="sched_101",
        candidate_id="cand_test_101",
        interviewer_id="interviewer_alice",
        scheduled_at=scheduled_time,
        status="scheduled",
        notes="Senior Backend Role",
    )

    db_session.add(schedule)
    db_session.commit()

    fetched = db_session.query(InterviewSchedule).filter_by(id="sched_101").first()

    assert fetched is not None
    assert fetched.candidate_id == "cand_test_101"
    assert fetched.interviewer_id == "interviewer_alice"
    assert fetched.status == "scheduled"
    assert "sched_101" in repr(fetched)


def test_email_service_send_confirmation():
    """Test EmailService constructs email and handles SMTP gracefully."""

    email_svc = EmailService()

    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        success, msg = email_svc.send_interview_confirmation(
            candidate_name="Jane Doe",
            candidate_email="jane.doe@example.com",
            interview_date="August 12, 2026",
            interview_time="10:00 AM UTC",
            interviewer_name="Alice Smith",
            schedule_id="sched_202",
        )

        assert success is True
        assert "Email sent successfully" in msg
        mock_server.send_message.assert_called_once()


def test_email_service_handles_smtp_error():
    """Test EmailService catches SMTP exceptions and logs error."""

    email_svc = EmailService()

    with patch(
        "smtplib.SMTP",
        side_effect=Exception("SMTP Connection Refused"),
    ):
        success, msg = email_svc.send_interview_confirmation(
            candidate_name="Jane Doe",
            candidate_email="jane.doe@example.com",
            interview_date="August 12, 2026",
            interview_time="10:00 AM UTC",
            interviewer_name="Alice Smith",
            schedule_id="sched_202",
        )

        assert success is False
        assert "Failed to send email" in msg


def test_create_schedule_api_endpoint(client, db_session):
    """Test POST /api/schedule endpoint with candidate creation and email trigger."""

    candidate = Candidate(
        candidate_id="cand_test_303",
        name="Bob Architect",
        email="bob.architect@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    payload = {
        "candidate_id": "cand_test_303",
        "interviewer_id": "Tech Lead Charlie",
        "scheduled_at": tomorrow,
        "notes": "System Architecture Technical Round",
        "send_email": True,
    }

    with patch(
        "orchestrator.email_service.email_service.send_interview_confirmation"
    ) as mock_send:
        mock_send.return_value = (
            True,
            "Email sent successfully",
        )

        response = client.post(
            "/api/schedule",
            json=payload,
        )

    assert response.status_code == 201

    data = response.json()

    assert data["message"] == "Interview scheduled successfully."
    assert data["schedule"]["candidate_id"] == "cand_test_303"
    assert data["schedule"]["candidate_name"] == "Bob Architect"
    assert data["schedule"]["interviewer_id"] == "Tech Lead Charlie"
    assert data["email_notification"]["sent"] is True


def test_create_schedule_past_date_fails(client, db_session):
    """Test that scheduling an interview in the past raises HTTP 400 error."""

    candidate = Candidate(
        candidate_id="cand_test_past",
        name="Past Candidate",
        email="past@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    payload = {
        "candidate_id": "cand_test_past",
        "interviewer_id": "Interviewer X",
        "scheduled_at": yesterday,
    }

    response = client.post(
        "/api/schedule",
        json=payload,
    )

    assert response.status_code == 400
    assert "must be in the future" in response.json()["detail"]


def test_update_schedule_invalid_status_fails(client, db_session):
    """Test that updating schedule with an invalid status raises HTTP 400 error."""

    candidate = Candidate(
        candidate_id="cand_test_status",
        name="Status Candidate",
        email="status@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_invalid_status",
        candidate_id="cand_test_status",
        interviewer_id="Lead Tester",
        scheduled_at=future_time,
        status="scheduled",
    )

    db_session.add(schedule)
    db_session.commit()

    patch_res = client.patch(
        "/api/schedule/sched_invalid_status",
        json={"status": "invalid_status_xyz"},
    )

    assert patch_res.status_code == 400
    assert "Allowed statuses are" in patch_res.json()["detail"]


def test_cancel_schedule_api(client, db_session):
    """
    Test cancelling a scheduled interview.

    Expected behavior:
    1. Existing scheduled interview is found.
    2. PATCH request changes status to cancelled.
    3. Existing scheduled_at remains unchanged.
    4. Database contains cancelled status.
    """

    candidate = Candidate(
        candidate_id="cand_cancel_001",
        name="Cancel Candidate",
        email="cancel@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    original_time = datetime.now(timezone.utc) + timedelta(days=2)
    schedule = InterviewSchedule(
        id="sched_cancel_001",
        candidate_id="cand_cancel_001",
        interviewer_id="HR Manager",
        scheduled_at=original_time,
        status="scheduled",
        notes="Initial interview",
    )
    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_cancel_001",
        json={
            "status": "cancelled",
        },
    )
    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Schedule updated successfully"
    assert data["schedule"]["id"] == "sched_cancel_001"
    assert data["schedule"]["status"] == "cancelled"

    # scheduled_at should not change when only cancelling.
    returned_time = datetime.fromisoformat(data["schedule"]["scheduled_at"])

    assert normalize_utc(returned_time) == normalize_utc(original_time)

    # Verify database state.
    db_session.expire_all()

    updated_schedule = (
        db_session.query(InterviewSchedule).filter_by(id="sched_cancel_001").first()
    )
    assert updated_schedule is not None
    assert updated_schedule.status == "cancelled"

    # The original interview time should remain intact.
    assert normalize_utc(updated_schedule.scheduled_at) == normalize_utc(original_time)


def test_reschedule_schedule_api(client, db_session):
    """
    Test rescheduling an existing scheduled interview.

    Expected behavior:
    1. Existing scheduled interview is found.
    2. PATCH request changes status to rescheduled.
    3. scheduled_at is changed to the new future datetime.
    4. Database contains both updated status and datetime.
    """

    candidate = Candidate(
        candidate_id="cand_reschedule_001",
        name="Reschedule Candidate",
        email="reschedule@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    original_time = datetime.now(timezone.utc) + timedelta(days=2)

    new_time = datetime.now(timezone.utc) + timedelta(days=5)

    schedule = InterviewSchedule(
        id="sched_reschedule_001",
        candidate_id="cand_reschedule_001",
        interviewer_id="Technical Lead",
        scheduled_at=original_time,
        status="scheduled",
        notes="Original interview",
    )
    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_reschedule_001",
        json={
            "status": "rescheduled",
            "scheduled_at": new_time.isoformat(),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Schedule updated successfully"
    assert data["schedule"]["id"] == "sched_reschedule_001"
    assert data["schedule"]["status"] == "rescheduled"

    # Verify new datetime was returned.
    returned_time = datetime.fromisoformat(data["schedule"]["scheduled_at"])

    assert normalize_utc(returned_time) == normalize_utc(new_time)

    # Verify database state.
    db_session.expire_all()

    updated_schedule = (
        db_session.query(InterviewSchedule).filter_by(id="sched_reschedule_001").first()
    )
    assert updated_schedule is not None
    assert updated_schedule.status == "rescheduled"
    assert normalize_utc(updated_schedule.scheduled_at) == normalize_utc(new_time)
    # Make sure the original datetime was actually replaced.
    assert updated_schedule.scheduled_at != original_time


def test_reschedule_schedule_past_date_fails(client, db_session):
    """
    Test that an interview cannot be rescheduled to a past datetime.

    Expected behavior:
    - PATCH returns 400.
    - Existing schedule remains unchanged.
    - Status remains scheduled.
    """

    candidate = Candidate(
        candidate_id="cand_reschedule_past",
        name="Past Reschedule Candidate",
        email="past-reschedule@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    original_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_reschedule_past",
        candidate_id="cand_reschedule_past",
        interviewer_id="Interviewer A",
        scheduled_at=original_time,
        status="scheduled",
    )

    db_session.add(schedule)
    db_session.commit()

    past_time = datetime.now(timezone.utc) - timedelta(days=1)
    response = client.patch(
        "/api/schedule/sched_reschedule_past",
        json={
            "status": "rescheduled",
            "scheduled_at": past_time.isoformat(),
        },
    )

    assert response.status_code == 400
    assert "must be in the future" in response.json()["detail"]

    # Verify that the failed update did not modify the schedule.
    db_session.expire_all()

    unchanged_schedule = (
        db_session.query(InterviewSchedule)
        .filter_by(id="sched_reschedule_past")
        .first()
    )

    assert unchanged_schedule is not None
    assert unchanged_schedule.status == "scheduled"
    assert normalize_utc(unchanged_schedule.scheduled_at) == normalize_utc(
        original_time
    )


def test_cancel_rescheduled_schedule_api(client, db_session):
    """
    Test that a rescheduled interview can subsequently be cancelled.

    Flow:
        scheduled
            ↓
        rescheduled
            ↓
        cancelled
    """

    candidate = Candidate(
        candidate_id="cand_reschedule_cancel",
        name="Reschedule Cancel Candidate",
        email="reschedule-cancel@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    new_time = datetime.now(timezone.utc) + timedelta(days=4)
    schedule = InterviewSchedule(
        id="sched_reschedule_cancel",
        candidate_id="cand_reschedule_cancel",
        interviewer_id="Senior Engineer",
        scheduled_at=new_time,
        status="rescheduled",
    )
    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_reschedule_cancel",
        json={
            "status": "cancelled",
        },
    )
    assert response.status_code == 200

    data = response.json()

    assert data["schedule"]["id"] == "sched_reschedule_cancel"
    assert data["schedule"]["status"] == "cancelled"

    # Verify database state.
    db_session.expire_all()

    cancelled_schedule = (
        db_session.query(InterviewSchedule)
        .filter_by(id="sched_reschedule_cancel")
        .first()
    )

    assert cancelled_schedule is not None
    assert cancelled_schedule.status == "cancelled"
    assert normalize_utc(cancelled_schedule.scheduled_at) == normalize_utc(new_time)


def test_reschedule_missing_datetime_fails(client, db_session):
    """Test that rescheduling without providing scheduled_at/new_scheduled_at raises HTTP 400."""
    candidate = Candidate(
        candidate_id="cand_resched_missing_dt",
        name="Missing Date Candidate",
        email="missing-dt@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    schedule = InterviewSchedule(
        id="sched_missing_dt",
        candidate_id="cand_resched_missing_dt",
        interviewer_id="Interviewer Missing",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
        status="scheduled",
    )
    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_missing_dt",
        json={"status": "rescheduled"},
    )
    assert response.status_code == 200


def test_reschedule_with_new_scheduled_at_alias(client, db_session):
    """Test rescheduling using new_scheduled_at field name and schedule_id in body."""
    candidate = Candidate(
        candidate_id="cand_new_sched_alias",
        name="Alias Candidate",
        email="alias@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    original_time = datetime.now(timezone.utc) + timedelta(days=2)
    new_time = datetime.now(timezone.utc) + timedelta(days=6)

    schedule = InterviewSchedule(
        id="sched_alias_001",
        candidate_id="cand_new_sched_alias",
        interviewer_id="Interviewer Alias",
        scheduled_at=original_time,
        status="scheduled",
    )
    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_alias_001",
        json={
            "schedule_id": "sched_alias_001",
            "status": "rescheduled",
            "new_scheduled_at": new_time.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["schedule"]["status"] == "rescheduled"
    returned_time = datetime.fromisoformat(data["schedule"]["scheduled_at"])
    assert normalize_utc(returned_time) == normalize_utc(new_time)

    db_session.expire_all()
    updated = (
        db_session.query(InterviewSchedule).filter_by(id="sched_alias_001").first()
    )
    assert updated.status == "rescheduled"
    assert normalize_utc(updated.scheduled_at) == normalize_utc(new_time)


def test_update_schedule_not_found(client, db_session):
    """Test that updating a non-existent schedule returns HTTP 404."""
    response = client.patch(
        "/api/schedule/non_existent_schedule_id",
        json={"status": "cancelled"},
    )
    assert response.status_code == 404
    assert "Schedule not found" in response.json()["detail"]


def test_cancel_with_datetime_provided_fails(client, db_session):
    """Test that providing scheduled_at when status is cancelled raises HTTP 400."""
    candidate = Candidate(
        candidate_id="cand_cancel_dt_fail",
        name="Cancel DT Fail Candidate",
        email="canceldtfail@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    schedule = InterviewSchedule(
        id="sched_cancel_dt_fail",
        candidate_id="cand_cancel_dt_fail",
        interviewer_id="Interviewer Cancel",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
        status="scheduled",
    )
    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_cancel_dt_fail",
        json={
            "status": "cancelled",
            "scheduled_at": (
                datetime.now(timezone.utc) + timedelta(days=5)
            ).isoformat(),
        },
    )
    assert response.status_code == 400
    assert "scheduled_at cannot be provided" in response.json()["detail"]


def test_update_schedule_preserves_unrelated_fields(client, db_session):
    """Test that updating notes does not overwrite scheduled_at or status."""
    candidate = Candidate(
        candidate_id="cand_preserve_fields",
        name="Preserve Candidate",
        email="preserve@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    original_time = datetime.now(timezone.utc) + timedelta(days=3)
    schedule = InterviewSchedule(
        id="sched_preserve_001",
        candidate_id="cand_preserve_fields",
        interviewer_id="Lead Interviewer",
        scheduled_at=original_time,
        status="scheduled",
        notes="Initial note",
    )
    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_preserve_001",
        json={"notes": "Updated note only"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["schedule"]["notes"] == "Updated note only"
    assert data["schedule"]["status"] == "scheduled"

    db_session.expire_all()
    updated = (
        db_session.query(InterviewSchedule).filter_by(id="sched_preserve_001").first()
    )
    assert updated.notes == "Updated note only"
    assert updated.status == "scheduled"
    assert normalize_utc(updated.scheduled_at) == normalize_utc(original_time)
    assert updated.interviewer_id == "Lead Interviewer"
    assert updated.candidate_id == "cand_preserve_fields"


def test_reschedule_with_invalid_datetime_format_fails(client, db_session):
    """Test that rescheduling with an invalid datetime string returns HTTP 422."""
    candidate = Candidate(
        candidate_id="cand_invalid_dt",
        name="Invalid DT Candidate",
        email="invaliddt@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    schedule = InterviewSchedule(
        id="sched_invalid_dt_001",
        candidate_id="cand_invalid_dt",
        interviewer_id="Interviewer DT",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
        status="scheduled",
    )
    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_invalid_dt_001",
        json={
            "status": "rescheduled",
            "new_scheduled_at": "not-a-valid-datetime",
        },
    )
    assert response.status_code == 422


def test_list_and_upcoming_schedule_api(client, db_session):
    """Test GET /api/schedule and GET /api/schedule/upcoming."""

    candidate = Candidate(
        candidate_id="cand_test_404",
        name="Alice Engineer",
        email="alice.engineer@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_future",
        candidate_id="cand_test_404",
        interviewer_id="Manager Dave",
        scheduled_at=future_time,
        status="scheduled",
    )

    db_session.add(schedule)
    db_session.commit()

    # GET /api/schedule
    res_list = client.get("/api/schedule")

    assert res_list.status_code == 200

    schedules = res_list.json()["schedules"]

    assert len(schedules) >= 1
    assert any(schedule_data["id"] == "sched_future" for schedule_data in schedules)

    # GET /api/schedule/upcoming
    res_upcoming = client.get("/api/schedule/upcoming")

    assert res_upcoming.status_code == 200

    upcoming = res_upcoming.json()["upcoming"]

    assert len(upcoming) >= 1
    assert upcoming[0]["id"] == "sched_future"


def test_full_end_to_end_schedule_flow(client, db_session):
    """
    Final End-to-End Test Verification:
    Schedule interview for tomorrow -> Save in DB -> Send confirmation email
    -> Show interview on upcoming dashboard.
    """

    candidate = Candidate(
        candidate_id="cand_e2e_999",
        name="E2E Tester",
        email="e2e.tester@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    # 1. Schedule Interview via POST /api/schedule
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        post_res = client.post(
            "/api/schedule",
            json={
                "candidate_id": "cand_e2e_999",
                "interviewer_id": "Aditya Kanojiya",
                "scheduled_at": tomorrow,
                "notes": "Full-Stack Verification Round",
                "send_email": True,
            },
        )

    assert post_res.status_code == 201

    res_data = post_res.json()
    sched_id = res_data["schedule"]["id"]

    # 2. Verify Saved in DB
    db_entry = db_session.query(InterviewSchedule).filter_by(id=sched_id).first()

    assert db_entry is not None
    assert db_entry.candidate_id == "cand_e2e_999"
    assert db_entry.interviewer_id == "Aditya Kanojiya"
    assert db_entry.status == "scheduled"

    # 3. Verify Email Sent Notification
    assert res_data["email_notification"]["sent"] is True

    # 4. Verify Shows on Upcoming Dashboard API
    upcoming_res = client.get("/api/schedule/upcoming")

    assert upcoming_res.status_code == 200

    upcoming_list = upcoming_res.json()["upcoming"]

    assert any(schedule_data["id"] == sched_id for schedule_data in upcoming_list)


# ---------------------------------------------------------------------------
# Issue #25 - Hook reschedule/cancel into notifications
# ---------------------------------------------------------------------------


def test_update_schedule_cancelled_creates_one_notification(
    client,
    db_session,
):
    """
    Changing a scheduled interview to cancelled must create exactly
    one notification for the candidate.
    """

    candidate = Candidate(
        candidate_id="cand_notification_cancel",
        name="Cancel Candidate",
        email="cancel@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_notification_cancel",
        candidate_id="cand_notification_cancel",
        interviewer_id="Interviewer Cancel",
        scheduled_at=future_time,
        status="scheduled",
    )

    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_notification_cancel",
        json={"status": "cancelled"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["schedule"]["status"] == "cancelled"

    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == "cand_notification_cancel",
        )
        .all()
    )

    assert len(notifications) == 1

    notification = notifications[0]

    assert notification.user_id == "cand_notification_cancel"
    assert "cancelled" in notification.message.lower()
    assert notification.read == False


def test_update_schedule_rescheduled_creates_one_notification(
    client,
    db_session,
):
    """
    Changing a scheduled interview to rescheduled must create exactly
    one notification for the candidate.
    """

    candidate = Candidate(
        candidate_id="cand_notification_reschedule",
        name="Reschedule Candidate",
        email="reschedule@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_notification_reschedule",
        candidate_id="cand_notification_reschedule",
        interviewer_id="Interviewer Reschedule",
        scheduled_at=future_time,
        status="scheduled",
    )

    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_notification_reschedule",
        json={"status": "rescheduled"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["schedule"]["status"] == "rescheduled"

    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == "cand_notification_reschedule",
        )
        .all()
    )

    assert len(notifications) == 1

    notification = notifications[0]

    assert notification.user_id == "cand_notification_reschedule"
    assert "rescheduled" in notification.message.lower()
    assert notification.read == False


def test_repeating_cancelled_status_does_not_create_duplicate_notification(
    client,
    db_session,
):
    """
    Sending cancelled when the schedule is already cancelled must not
    create a duplicate notification.
    """

    candidate = Candidate(
        candidate_id="cand_notification_duplicate",
        name="Duplicate Candidate",
        email="duplicate@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_notification_duplicate",
        candidate_id="cand_notification_duplicate",
        interviewer_id="Interviewer Duplicate",
        scheduled_at=future_time,
        status="scheduled",
    )

    db_session.add(schedule)
    db_session.commit()

    # First transition: scheduled -> cancelled.
    first_response = client.patch(
        "/api/schedule/sched_notification_duplicate",
        json={"status": "cancelled"},
    )

    assert first_response.status_code == 200
    assert first_response.json()["schedule"]["status"] == "cancelled"

    # Second request: cancelled -> cancelled.
    # This must not create another notification.
    second_response = client.patch(
        "/api/schedule/sched_notification_duplicate",
        json={"status": "cancelled"},
    )

    assert second_response.status_code == 200
    assert second_response.json()["schedule"]["status"] == "cancelled"

    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == "cand_notification_duplicate",
        )
        .all()
    )

    assert len(notifications) == 1


def test_repeating_rescheduled_status_does_not_create_duplicate_notification(
    client,
    db_session,
):
    """
    Sending rescheduled when the schedule is already rescheduled must not
    create a duplicate notification.
    """

    candidate = Candidate(
        candidate_id="cand_notification_reschedule_duplicate",
        name="Reschedule Duplicate Candidate",
        email="reschedule-duplicate@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_notification_reschedule_duplicate",
        candidate_id="cand_notification_reschedule_duplicate",
        interviewer_id="Interviewer Reschedule Duplicate",
        scheduled_at=future_time,
        status="scheduled",
    )

    db_session.add(schedule)
    db_session.commit()

    # First transition: scheduled -> rescheduled.
    first_response = client.patch(
        "/api/schedule/sched_notification_reschedule_duplicate",
        json={"status": "rescheduled"},
    )

    assert first_response.status_code == 200
    assert first_response.json()["schedule"]["status"] == "rescheduled"

    # Second request: rescheduled -> rescheduled.
    # This must not create another notification.
    second_response = client.patch(
        "/api/schedule/sched_notification_reschedule_duplicate",
        json={"status": "rescheduled"},
    )

    assert second_response.status_code == 200
    assert second_response.json()["schedule"]["status"] == "rescheduled"

    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == "cand_notification_reschedule_duplicate",
        )
        .all()
    )

    assert len(notifications) == 1


def test_update_schedule_completed_does_not_create_notification(
    client,
    db_session,
):
    """
    Changing a scheduled interview to completed must not create a
    cancellation or reschedule notification.
    """

    candidate = Candidate(
        candidate_id="cand_notification_completed",
        name="Completed Candidate",
        email="completed@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_notification_completed",
        candidate_id="cand_notification_completed",
        interviewer_id="Interviewer Completed",
        scheduled_at=future_time,
        status="scheduled",
    )

    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_notification_completed",
        json={"status": "completed"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["schedule"]["status"] == "completed"

    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == "cand_notification_completed",
        )
        .all()
    )

    assert len(notifications) == 0


def test_update_schedule_without_status_does_not_create_notification(
    client,
    db_session,
):
    """
    Updating only schedule details without changing the status must not
    create a notification.
    """

    candidate = Candidate(
        candidate_id="cand_notification_no_status",
        name="No Status Candidate",
        email="no-status@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_notification_no_status",
        candidate_id="cand_notification_no_status",
        interviewer_id="Interviewer No Status",
        scheduled_at=future_time,
        status="scheduled",
        notes="Original notes",
    )

    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_notification_no_status",
        json={"notes": "Updated interview notes"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["schedule"]["status"] == "scheduled"
    assert response_data["schedule"]["notes"] == "Updated interview notes"

    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == "cand_notification_no_status",
        )
        .all()
    )

    assert len(notifications) == 0


def test_cancelled_to_rescheduled_creates_one_notification(
    client,
    db_session,
):
    """
    Changing an already cancelled schedule to rescheduled is a real status
    transition and must create exactly one reschedule notification.
    """

    candidate = Candidate(
        candidate_id="cand_cancel_to_reschedule",
        name="Cancel To Reschedule Candidate",
        email="cancel-to-reschedule@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_cancel_to_reschedule",
        candidate_id="cand_cancel_to_reschedule",
        interviewer_id="Interviewer Transition",
        scheduled_at=future_time,
        status="cancelled",
    )

    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_cancel_to_reschedule",
        json={"status": "rescheduled"},
    )

    assert response.status_code == 200
    assert response.json()["schedule"]["status"] == "rescheduled"

    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == "cand_cancel_to_reschedule",
        )
        .all()
    )

    assert len(notifications) == 1
    assert "rescheduled" in notifications[0].message.lower()


def test_rescheduled_to_cancelled_creates_one_notification(
    client,
    db_session,
):
    """
    Changing an already rescheduled schedule to cancelled is a real status
    transition and must create exactly one cancellation notification.
    """

    candidate = Candidate(
        candidate_id="cand_reschedule_to_cancel",
        name="Reschedule To Cancel Candidate",
        email="reschedule-to-cancel@example.com",
    )

    db_session.add(candidate)
    db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(days=2)

    schedule = InterviewSchedule(
        id="sched_reschedule_to_cancel",
        candidate_id="cand_reschedule_to_cancel",
        interviewer_id="Interviewer Transition",
        scheduled_at=future_time,
        status="rescheduled",
    )

    db_session.add(schedule)
    db_session.commit()

    response = client.patch(
        "/api/schedule/sched_reschedule_to_cancel",
        json={"status": "cancelled"},
    )

    assert response.status_code == 200
    assert response.json()["schedule"]["status"] == "cancelled"

    notifications = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == "cand_reschedule_to_cancel",
        )
        .all()
    )

    assert len(notifications) == 1
    assert "cancelled" in notifications[0].message.lower()


# ---------------------------------------------------------------------------
# Stabilized-version - DB-level slot integrity and model table args
# ---------------------------------------------------------------------------


def test_duplicate_slot_booking_prevented_at_db_level(db_session):
    """Test that booking the same candidate for the exact same slot raises IntegrityError at DB level."""
    candidate = Candidate(
        candidate_id="cand_dup_test",
        name="Dup Candidate",
        email="dup@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    slot_time = datetime(2026, 9, 1, 14, 0, 0, tzinfo=timezone.utc)

    # First booking succeeds
    sched1 = InterviewSchedule(
        id="sched_dup_1",
        candidate_id="cand_dup_test",
        interviewer_id="Interviewer A",
        scheduled_at=slot_time,
        status="scheduled",
    )
    db_session.add(sched1)
    db_session.commit()

    # Second booking for same candidate at the same slot must fail at DB constraint level
    sched2 = InterviewSchedule(
        id="sched_dup_2",
        candidate_id="cand_dup_test",
        interviewer_id="Interviewer B",
        scheduled_at=slot_time,
        status="scheduled",
    )
    db_session.add(sched2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_different_candidates_same_slot_allowed(db_session):
    """Test that two different candidates can have interviews scheduled at the same time."""
    c1 = Candidate(candidate_id="cand_multi_1", name="Cand 1", email="c1@example.com")
    c2 = Candidate(candidate_id="cand_multi_2", name="Cand 2", email="c2@example.com")
    db_session.add_all([c1, c2])
    db_session.commit()

    slot_time = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)

    sched1 = InterviewSchedule(
        id="sched_multi_1",
        candidate_id="cand_multi_1",
        interviewer_id="Interviewer Alpha",
        scheduled_at=slot_time,
        status="scheduled",
    )
    sched2 = InterviewSchedule(
        id="sched_multi_2",
        candidate_id="cand_multi_2",
        interviewer_id="Interviewer Beta",
        scheduled_at=slot_time,
        status="scheduled",
    )
    db_session.add_all([sched1, sched2])
    db_session.commit()

    assert (
        db_session.query(InterviewSchedule).filter_by(id="sched_multi_1").first()
        is not None
    )
    assert (
        db_session.query(InterviewSchedule).filter_by(id="sched_multi_2").first()
        is not None
    )


def test_same_candidate_different_slots_allowed(db_session):
    """Test that the same candidate can have multiple interviews at different times."""
    candidate = Candidate(
        candidate_id="cand_slots_test",
        name="Multi Slot Cand",
        email="multislot@example.com",
    )
    db_session.add(candidate)
    db_session.commit()

    time1 = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)
    time2 = datetime(2026, 9, 3, 14, 0, 0, tzinfo=timezone.utc)

    sched1 = InterviewSchedule(
        id="sched_slot_1",
        candidate_id="cand_slots_test",
        interviewer_id="Interviewer Round 1",
        scheduled_at=time1,
        status="scheduled",
    )
    sched2 = InterviewSchedule(
        id="sched_slot_2",
        candidate_id="cand_slots_test",
        interviewer_id="Interviewer Round 2",
        scheduled_at=time2,
        status="scheduled",
    )
    db_session.add_all([sched1, sched2])
    db_session.commit()

    results = (
        db_session.query(InterviewSchedule)
        .filter_by(candidate_id="cand_slots_test")
        .all()
    )
    assert len(results) == 2


def test_interview_schedule_table_args_and_indexes():
    """Verify table args contains unique constraint and composite indexes."""
    table_args = InterviewSchedule.__table_args__
    assert table_args is not None

    # Check UniqueConstraint
    unique_constraints = [
        arg for arg in table_args if isinstance(arg, UniqueConstraint)
    ]
    uq_names = [uq.name for uq in unique_constraints]
    assert "uq_schedule_candidate_slot" in uq_names

    # Check composite Indexes
    indexes = [arg for arg in table_args if isinstance(arg, Index)]
    idx_names = [idx.name for idx in indexes]
    assert "ix_schedule_interviewer_time" in idx_names
    assert "ix_schedule_status_time" in idx_names
