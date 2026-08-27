from datetime import datetime

from database.models import Candidate, InterviewSession
from orchestrator.candidate_manager import CandidateManager


def test_list_candidates_returns_zero_session_counts(db_session, monkeypatch):
    candidate = Candidate(
        candidate_id="candidate_stats_1",
        name="Test Candidate",
        email="stats@example.com",
        skills=[],
        interview_history=[],
        total_interviews=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db_session.add(candidate)
    db_session.commit()

    monkeypatch.setattr(
        "orchestrator.candidate_manager.SessionLocal",
        lambda: db_session,
    )

    manager = CandidateManager()

    candidates = manager.list_candidates()

    assert len(candidates) == 1
    assert candidates[0]["active_sessions"] == 0
    assert candidates[0]["completed_sessions"] == 0


def test_list_candidates_counts_active_and_completed_sessions(db_session, monkeypatch):
    candidate = Candidate(
        candidate_id="candidate_stats_2",
        name="Test Candidate",
        email="stats2@example.com",
        skills=[],
        interview_history=[],
        total_interviews=2,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db_session.add(candidate)

    db_session.add_all(
        [
            InterviewSession(
                session_id="session_completed",
                candidate_id="candidate_stats_2",
                status="COMPLETED",
            ),
            InterviewSession(
                session_id="session_active",
                candidate_id="candidate_stats_2",
                status="PROCESSING",
            ),
        ]
    )

    db_session.commit()

    monkeypatch.setattr(
        "orchestrator.candidate_manager.SessionLocal",
        lambda: db_session,
    )

    manager = CandidateManager()
    candidates = manager.list_candidates()

    assert len(candidates) == 1
    assert candidates[0]["active_sessions"] == 1
    assert candidates[0]["completed_sessions"] == 1
