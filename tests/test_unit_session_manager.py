"""
Unit tests for the SessionManager state machine.
"""

import itertools
from unittest.mock import MagicMock, patch

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

def test_create_session_preserves_language():
    sm = SessionManager()
    sm.state_sync = MagicMock()

    db_session = MagicMock()
    candidate = MagicMock()
    db_session.execute.return_value.scalar_one_or_none.return_value = candidate
    with patch(
        "orchestrator.session_manager.SessionLocal",
        return_value=db_session,
    ):
            session_id = sm.create_session(
            candidate_id="candidate-1",
            position="Software Engineer",
            candidate_name="Test Candidate",
            language="hi",
            )
            created_session = db_session.add.call_args.args[0]
            assert created_session.language == "hi"
def test_create_session_defaults_to_english():
    sm = SessionManager()
    sm.state_sync = MagicMock()

    db_session = MagicMock()
    candidate = MagicMock()
    db_session.execute.return_value.scalar_one_or_none.return_value = candidate

    with patch(
        "orchestrator.session_manager.SessionLocal",
        return_value=db_session,
    ):
        session_id = sm.create_session(
            candidate_id="candidate-2",
            position="Software Engineer",
            candidate_name="Test Candidate",
        )

        created_session = db_session.add.call_args.args[0]
        assert created_session.language == "en"