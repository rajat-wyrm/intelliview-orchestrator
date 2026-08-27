from datetime import datetime

import pytest

from database.models import Candidate, InterviewSession


@pytest.fixture
def mock_candidate_manager(db_session, monkeypatch):
    """Fixture to mock the candidate manager with db_session"""
    from orchestrator.candidate_manager import CandidateManager

    monkeypatch.setattr(
        "orchestrator.candidate_manager.SessionLocal",
        lambda: db_session,
    )
    return CandidateManager()


def test_candidate_stats_empty_database(db_session, monkeypatch):
    """Test that stats endpoint returns all zeros on empty database"""
    from orchestrator.candidate_manager import CandidateManager

    monkeypatch.setattr(
        "orchestrator.candidate_manager.SessionLocal",
        lambda: db_session,
    )

    manager = CandidateManager()
    candidates = manager.list_candidates()

    assert len(candidates) == 0
    assert all(c.get("active_sessions", 0) == 0 for c in candidates)
    assert all(c.get("completed_sessions", 0) == 0 for c in candidates)


def test_candidate_stats_single_candidate_no_sessions(db_session, monkeypatch):
    """Test stats with one candidate but no sessions"""
    candidate = Candidate(
        candidate_id="cand_1",
        name="John Doe",
        email="john@example.com",
        skills=["Python"],
        interview_history=[],
        total_interviews=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db_session.add(candidate)
    db_session.commit()

    from orchestrator.candidate_manager import CandidateManager

    monkeypatch.setattr(
        "orchestrator.candidate_manager.SessionLocal",
        lambda: db_session,
    )

    manager = CandidateManager()
    candidates = manager.list_candidates()

    assert len(candidates) == 1
    assert candidates[0]["candidate_id"] == "cand_1"
    assert candidates[0]["active_sessions"] == 0
    assert candidates[0]["completed_sessions"] == 0


def test_candidate_stats_multiple_candidates_mixed_sessions(db_session, monkeypatch):
    """Test stats with multiple candidates with different session states"""
    # Candidate 1: No sessions
    cand1 = Candidate(
        candidate_id="cand_1",
        name="Alice",
        email="alice@example.com",
        skills=[],
        interview_history=[],
        total_interviews=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Candidate 2: One active, one completed
    cand2 = Candidate(
        candidate_id="cand_2",
        name="Bob",
        email="bob@example.com",
        skills=[],
        interview_history=[],
        total_interviews=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Candidate 3: Two active sessions
    cand3 = Candidate(
        candidate_id="cand_3",
        name="Charlie",
        email="charlie@example.com",
        skills=[],
        interview_history=[],
        total_interviews=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db_session.add_all([cand1, cand2, cand3])
    db_session.flush()

    # Sessions for cand2
    session_completed = InterviewSession(
        session_id="sess_1",
        candidate_id="cand_2",
        status="COMPLETED",
    )
    session_active = InterviewSession(
        session_id="sess_2",
        candidate_id="cand_2",
        status="PROCESSING",
    )

    # Sessions for cand3
    session_active_1 = InterviewSession(
        session_id="sess_3",
        candidate_id="cand_3",
        status="CREATED",
    )
    session_active_2 = InterviewSession(
        session_id="sess_4",
        candidate_id="cand_3",
        status="QUEUED",
    )

    db_session.add_all(
        [session_completed, session_active, session_active_1, session_active_2]
    )
    db_session.commit()

    from orchestrator.candidate_manager import CandidateManager

    monkeypatch.setattr(
        "orchestrator.candidate_manager.SessionLocal",
        lambda: db_session,
    )

    manager = CandidateManager()
    candidates = manager.list_candidates()

    # Candidate stats should not contain NaN
    for c in candidates:
        assert isinstance(c.get("active_sessions", 0), int)
        assert isinstance(c.get("completed_sessions", 0), int)
        assert c.get("active_sessions", 0) >= 0
        assert c.get("completed_sessions", 0) >= 0

    # Find each candidate in results
    cand1_stats = next(c for c in candidates if c["candidate_id"] == "cand_1")
    cand2_stats = next(c for c in candidates if c["candidate_id"] == "cand_2")
    cand3_stats = next(c for c in candidates if c["candidate_id"] == "cand_3")

    # Verify counts
    assert cand1_stats["active_sessions"] == 0
    assert cand1_stats["completed_sessions"] == 0

    assert cand2_stats["active_sessions"] == 1  # PROCESSING
    assert cand2_stats["completed_sessions"] == 1  # COMPLETED

    assert cand3_stats["active_sessions"] == 2  # CREATED, QUEUED
    assert cand3_stats["completed_sessions"] == 0


def test_candidate_stats_terminal_statuses(db_session, monkeypatch):
    """Test that terminal statuses (COMPLETED, FAILED, TIMEOUT, CANCELLED) are not counted as active"""
    candidate = Candidate(
        candidate_id="cand_terminal",
        name="Terminal Test",
        email="terminal@example.com",
        skills=[],
        interview_history=[],
        total_interviews=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db_session.add(candidate)
    db_session.flush()

    # Create sessions with all terminal statuses
    sessions = [
        InterviewSession(
            session_id="sess_completed",
            candidate_id="cand_terminal",
            status="COMPLETED",
        ),
        InterviewSession(
            session_id="sess_failed",
            candidate_id="cand_terminal",
            status="FAILED",
        ),
        InterviewSession(
            session_id="sess_timeout",
            candidate_id="cand_terminal",
            status="TIMEOUT",
        ),
        InterviewSession(
            session_id="sess_cancelled",
            candidate_id="cand_terminal",
            status="CANCELLED",
        ),
    ]

    db_session.add_all(sessions)
    db_session.commit()

    from orchestrator.candidate_manager import CandidateManager

    monkeypatch.setattr(
        "orchestrator.candidate_manager.SessionLocal",
        lambda: db_session,
    )

    manager = CandidateManager()
    candidates = manager.list_candidates()

    assert len(candidates) == 1
    assert candidates[0]["active_sessions"] == 0  # None are active (all terminal)
    assert candidates[0]["completed_sessions"] == 1  # Only COMPLETED counts
