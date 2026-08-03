"""
Tests for the SQLAlchemy 2.0 migration.

Runs the refactored query paths against an in-memory SQLite database to
verify the new `select()`-based syntax produces correct results.
"""

import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("POSTGRES_HOST", "localhost")

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db import Base
from database.models import Candidate, InterviewSession
from orchestrator.session_manager import SessionManager
from orchestrator.session_tracker import SessionTracker


@pytest.fixture
def db_session(postgres_container):
    engine = create_engine(
        postgres_container.get_connection_url(),
        future=True,
    )
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _make_session(
    session_id: str,
    status: str,
    risk: float | None = None,
    started_minutes_ago: int = 0,
):
    now = datetime.now(timezone.utc)
    return InterviewSession(
        session_id=session_id,
        candidate_id=f"cand-{session_id}",
        status=status,
        risk_score=risk,
        start_time=now - timedelta(minutes=started_minutes_ago) if started_minutes_ago else None,
        end_time=now if status == "COMPLETED" else None,
        created_at=now,
        updated_at=now,
    )


def test_session_tracker_active_sessions(db_session):
    db_session.add_all(
        [
            Candidate(candidate_id="cand-s1", name="Test 1", email="test1@example.com"),
            Candidate(candidate_id="cand-s2", name="Test 2", email="test2@example.com"),
            Candidate(candidate_id="cand-s3", name="Test 3", email="test3@example.com"),
            Candidate(candidate_id="cand-s4", name="Test 4", email="test4@example.com"),
        ]
    )
    db_session.commit()

    db_session.add_all(
        [
            _make_session("s1", "QUEUED"),
            _make_session("s2", "PROCESSING"),
            _make_session("s3", "COMPLETED", risk=0.1),
            _make_session("s4", "FAILED"),
        ]
    )
    db_session.commit()

    tracker = SessionTracker()
    # Patch SessionLocal to use our test session
    import orchestrator.session_tracker as st

    st.SessionLocal = lambda: db_session
    active = tracker.get_active_sessions()
    assert {s["session_id"] for s in active} == {"s1", "s2"}


def test_session_tracker_high_risk(db_session):
    db_session.add_all(
        [
            Candidate(candidate_id="cand-s1", name="Test 1", email="test1@example.com"),
            Candidate(candidate_id="cand-s2", name="Test 2", email="test2@example.com"),
            Candidate(candidate_id="cand-s3", name="Test 3", email="test3@example.com"),
        ]
    )
    db_session.commit()
    db_session.add_all(
        [
            _make_session("s1", "COMPLETED", risk=0.9),
            _make_session("s2", "COMPLETED", risk=0.5),
            _make_session("s3", "COMPLETED", risk=0.1),
        ]
    )
    db_session.commit()

    tracker = SessionTracker()
    import orchestrator.session_tracker as st

    st.SessionLocal = lambda: db_session
    high = tracker.get_high_risk_sessions(threshold=0.8, limit=10)
    assert [s["session_id"] for s in high] == ["s1"]


def test_session_tracker_statistics(db_session):
    db_session.add_all(
        [
            Candidate(candidate_id="cand-s1", name="Test 1", email="test1@example.com"),
            Candidate(candidate_id="cand-s2", name="Test 2", email="test2@example.com"),
            Candidate(candidate_id="cand-s3", name="Test 3", email="test3@example.com"),
            Candidate(candidate_id="cand-s4", name="Test 4", email="test4@example.com"),
        ]
    )
    db_session.commit()
    db_session.add_all(
        [
            _make_session("s1", "COMPLETED", risk=0.1, started_minutes_ago=10),
            _make_session("s2", "COMPLETED", risk=0.9, started_minutes_ago=20),
            _make_session("s3", "FAILED"),
            _make_session("s4", "QUEUED"),
        ]
    )
    db_session.commit()

    tracker = SessionTracker()
    import orchestrator.session_tracker as st

    st.SessionLocal = lambda: db_session
    stats = tracker.get_session_statistics()
    assert stats["total_sessions"] == 4
    assert stats["completed_sessions"] == 2
    assert stats["failed_sessions"] == 1
    assert stats["risk_score_stats"]["high_risk_sessions"] == 1
    assert stats["risk_score_stats"]["average_risk_score"] == pytest.approx(0.5, abs=1e-9)


def test_session_manager_state_machine(db_session):
    sm = SessionManager()
    import orchestrator.session_manager as smod

    smod.SessionLocal = lambda: db_session

    db_session.add(
        Candidate(
            candidate_id="c1",
            name="Test Candidate",
            email="c1@example.com",
        )
    )
    db_session.commit()
    db_session.add(
        InterviewSession(
            session_id="s1",
            candidate_id="c1",
            status=sm.CREATED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    assert sm.update_session_status("s1", sm.QUEUED) is True
    assert sm.update_session_status("s1", sm.PROCESSING) is True
    fetched = sm.get_session("s1")
    assert fetched is not None
    assert fetched["status"] == sm.PROCESSING


def test_session_manager_rejects_invalid_transition(db_session):
    sm = SessionManager()
    import orchestrator.session_manager as smod

    smod.SessionLocal = lambda: db_session

    db_session.add(
        Candidate(
            candidate_id="c2",
            name="Test Candidate",
            email="c2@example.com",
        )
    )
    db_session.commit()

    db_session.add(
        InterviewSession(
            session_id="s2",
            candidate_id="c2",
            status=sm.COMPLETED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    # COMPLETED is terminal — no further transitions allowed
    assert sm.update_session_status("s2", sm.PROCESSING) is False
