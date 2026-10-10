from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base, get_db
from database.models import Candidate, InterviewSchedule, InterviewSession
from routers.attendance import create_attendance_routes
from workers import tasks


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    candidate = Candidate(
        candidate_id="candidate-59",
        name="Test Candidate",
        email="candidate59@example.com",
    )

    scheduled_at = datetime.now(timezone.utc) - timedelta(hours=2)

    schedule = InterviewSchedule(
        id="schedule-59",
        candidate_id="candidate-59",
        interviewer_id="interviewer-1",
        scheduled_at=scheduled_at,
        status="scheduled",
    )

    # Multiple sessions for the same candidate.
    sessions = [
        InterviewSession(
            session_id="session-59-a",
            candidate_id="candidate-59",
            start_time=scheduled_at + timedelta(minutes=10),
        ),
        InterviewSession(
            session_id="session-59-b",
            candidate_id="candidate-59",
            start_time=scheduled_at + timedelta(minutes=20),
        ),
    ]

    db.add(candidate)
    db.add(schedule)
    db.add_all(sessions)
    db.commit()

    return db, schedule


def teardown_database(db):
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_manual_no_show_detection_handles_multiple_sessions():
    db, schedule = setup_database()

    app = FastAPI()
    app.include_router(create_attendance_routes())

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post("/attendance/check-no-shows")

        assert response.status_code == 200
        assert response.json()["count"] == 0
        assert schedule.status == "scheduled"
    finally:
        teardown_database(db)


def test_celery_no_show_detection_handles_multiple_sessions():
    db, schedule = setup_database()

    try:
        with patch.object(tasks, "SessionLocal", return_value=db):
            result = tasks.detect_no_shows.run()

        assert result["count"] == 0
        assert schedule.status == "scheduled"
    finally:
        teardown_database(db)

def test_manual_no_show_detection_marks_candidate_without_sessions():
    db, schedule = setup_database()

    try:
        db.query(InterviewSession).delete()
        db.commit()

        app = FastAPI()
        app.include_router(create_attendance_routes())

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as client:
            response = client.post("/attendance/check-no-shows")

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert schedule.status == "no-show"
    finally:
        teardown_database(db)


def test_celery_no_show_detection_marks_candidate_without_sessions():
    db, schedule = setup_database()

    try:
        db.query(InterviewSession).delete()
        db.commit()

        with patch.object(tasks, "SessionLocal", return_value=db):
            result = tasks.detect_no_shows.run()

        assert result["count"] == 1
        assert schedule.status == "no-show"
    finally:
        teardown_database(db)