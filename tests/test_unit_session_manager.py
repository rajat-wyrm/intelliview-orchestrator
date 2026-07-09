"""
Unit tests for the SessionManager state machine.
"""

import itertools
from datetime import datetime, timezone

import orchestrator.session_manager as session_manager
from orchestrator.session_manager import SessionManager


def test_valid_transitions_cover_full_pipeline():
    sm = SessionManager()
    # CREATED -> QUEUED -> PROCESSING -> VIDEO -> AUDIO -> EVALUATING -> COMPLETED
    pipeline = [
        sm.CREATED,
        sm.QUEUED,
        sm.PROCESSING,
        sm.VIDEO_PROCESSING,
        sm.AUDIO_PROCESSING,
        sm.EVALUATING,
        sm.COMPLETED,
    ]
    for prev, nxt in itertools.pairwise(pipeline):
        assert sm._is_valid_transition(prev, nxt), f"{prev} -> {nxt} should be valid"


def test_completed_is_terminal():
    sm = SessionManager()
    for s in [
        sm.PROCESSING,
        sm.VIDEO_PROCESSING,
        sm.AUDIO_PROCESSING,
        sm.EVALUATING,
        sm.QUEUED,
        sm.CREATED,
    ]:
        assert not sm._is_valid_transition(sm.COMPLETED, s)


def test_failed_is_terminal():
    sm = SessionManager()
    for s in [sm.COMPLETED, sm.QUEUED, sm.CREATED]:
        assert not sm._is_valid_transition(sm.FAILED, s)


def test_failed_can_be_reached_from_any_active_state():
    sm = SessionManager()
    for s in [
        sm.QUEUED,
        sm.PROCESSING,
        sm.VIDEO_PROCESSING,
        sm.AUDIO_PROCESSING,
        sm.EVALUATING,
    ]:
        assert sm._is_valid_transition(s, sm.FAILED), f"{s} -> FAILED should be valid"


def test_unknown_state_is_invalid():
    sm = SessionManager()
    assert not sm._is_valid_transition("UNKNOWN", sm.QUEUED)
    assert not sm._is_valid_transition(sm.QUEUED, "UNKNOWN")


def test_create_session_uses_same_timestamp_for_db_and_cache(monkeypatch):
    db_sessions = []
    cached_sessions = []
    timestamps = [
        datetime(2026, 1, 2, 3, 4, 5, 111111, tzinfo=timezone.utc),
        datetime(2026, 1, 2, 3, 4, 5, 222222, tzinfo=timezone.utc),
        datetime(2026, 1, 2, 3, 4, 5, 333333, tzinfo=timezone.utc),
        datetime(2026, 1, 2, 3, 4, 5, 444444, tzinfo=timezone.utc),
    ]

    class FakeDbSession:
        def add(self, interview_session):
            db_sessions.append(interview_session)

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    class FakeStateSynchronizer:
        def set_session_state(self, session_id, session_data):
            cached_sessions.append((session_id, session_data))
            return True

    monkeypatch.setattr(session_manager, "SessionLocal", FakeDbSession)
    monkeypatch.setattr(session_manager, "StateSynchronizer", FakeStateSynchronizer)
    monkeypatch.setattr(session_manager, "_utcnow", lambda: timestamps.pop(0))

    sm = SessionManager()
    session_id = sm.create_session("candidate-123")

    assert len(db_sessions) == 1
    assert len(cached_sessions) == 1

    interview_session = db_sessions[0]
    cached_session_id, session_data = cached_sessions[0]

    assert cached_session_id == session_id
    assert interview_session.created_at.isoformat() == session_data["created_at"]
    assert interview_session.updated_at.isoformat() == session_data["updated_at"]
