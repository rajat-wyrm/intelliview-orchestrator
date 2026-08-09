from unittest.mock import MagicMock, patch

import pytest

from orchestrator.session_manager import SessionManager


@pytest.fixture
def session_manager():
    manager = SessionManager()
    manager.state_sync = MagicMock()
    return manager


def test_all_valid_status_transitions(session_manager):
    """Every transition declared by SessionManager should be accepted."""
    for current_status, allowed_statuses in session_manager.VALID_TRANSITIONS.items():
        for new_status in allowed_statuses:
            assert (
                session_manager._is_valid_transition(current_status, new_status) is True
            )


@pytest.mark.parametrize(
    ("current_status", "new_status"),
    [
        (SessionManager.CREATED, SessionManager.COMPLETED),
        (SessionManager.COMPLETED, SessionManager.FAILED),
        (SessionManager.FAILED, SessionManager.PROCESSING),
        (SessionManager.CANCELLED, SessionManager.QUEUED),
        (SessionManager.TIMEOUT, SessionManager.COMPLETED),
    ],
)
def test_invalid_status_transitions(session_manager, current_status, new_status):
    assert session_manager._is_valid_transition(current_status, new_status) is False


def test_queued_to_processing(session_manager):
    assert session_manager._is_valid_transition(
        SessionManager.QUEUED,
        SessionManager.PROCESSING,
    )


def test_processing_to_completed(session_manager):
    assert session_manager._is_valid_transition(
        SessionManager.PROCESSING,
        SessionManager.COMPLETED,
    )


def test_processing_to_failed(session_manager):
    assert session_manager._is_valid_transition(
        SessionManager.PROCESSING,
        SessionManager.FAILED,
    )


def test_processing_pipeline_transitions(session_manager):
    assert session_manager._is_valid_transition(
        SessionManager.PROCESSING,
        SessionManager.VIDEO_PROCESSING,
    )
    assert session_manager._is_valid_transition(
        SessionManager.VIDEO_PROCESSING,
        SessionManager.AUDIO_PROCESSING,
    )
    assert session_manager._is_valid_transition(
        SessionManager.AUDIO_PROCESSING,
        SessionManager.EVALUATING,
    )
    assert session_manager._is_valid_transition(
        SessionManager.EVALUATING,
        SessionManager.COMPLETED,
    )


def test_timeout_can_transition_to_failed(session_manager):
    assert session_manager._is_valid_transition(
        SessionManager.TIMEOUT,
        SessionManager.FAILED,
    )


def test_completed_session_has_no_valid_transitions(session_manager):
    assert session_manager.VALID_TRANSITIONS[SessionManager.COMPLETED] == []


def test_failed_session_has_no_valid_transitions(session_manager):
    assert session_manager.VALID_TRANSITIONS[SessionManager.FAILED] == []


def test_update_session_status_success(session_manager):
    interview = MagicMock()
    interview.status = SessionManager.QUEUED
    interview.risk_score = None

    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = interview

    with (
        patch("orchestrator.session_manager.SessionLocal", return_value=db),
        patch(
            "orchestrator.session_manager.is_circuit_open",
            return_value=False,
        ),
        patch.object(
            session_manager,
            "_broadcast_status",
        ) as broadcast,
    ):
        session_manager.state_sync.get_session_state.return_value = {
            "session_id": "session-1",
            "status": SessionManager.QUEUED,
        }

        result = session_manager.update_session_status(
            "session-1",
            SessionManager.PROCESSING,
        )

    assert result is True
    assert interview.status == SessionManager.PROCESSING
    db.commit.assert_called_once()
    session_manager.state_sync.set_session_state.assert_called_once()
    broadcast.assert_called_once()


def test_update_session_status_rejects_invalid_transition(session_manager):
    interview = MagicMock()
    interview.status = SessionManager.COMPLETED

    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = interview

    with patch("orchestrator.session_manager.SessionLocal", return_value=db):
        result = session_manager.update_session_status(
            "session-1",
            SessionManager.FAILED,
        )

    assert result is False
    db.commit.assert_not_called()


def test_update_session_status_returns_false_for_missing_session(session_manager):
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None

    with patch("orchestrator.session_manager.SessionLocal", return_value=db):
        result = session_manager.update_session_status(
            "missing-session",
            SessionManager.PROCESSING,
        )

    assert result is False
    db.commit.assert_not_called()


def test_mark_session_failed(session_manager):
    with patch.object(
        session_manager,
        "update_session_status",
        return_value=True,
    ) as update_status:
        result = session_manager.mark_session_failed(
            "session-1",
            "video processing failed",
        )

    assert result is True
    update_status.assert_called_once_with(
        "session-1",
        SessionManager.FAILED,
        {"error_message": "video processing failed"},
    )


def test_mark_session_completed(session_manager):
    interview = MagicMock()
    interview.status = SessionManager.PROCESSING
    interview.risk_score = None
    interview.end_time = None

    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = interview

    with (
        patch("orchestrator.session_manager.SessionLocal", return_value=db),
        patch(
            "orchestrator.session_manager.is_circuit_open",
            return_value=False,
        ),
    ):
        session_manager.state_sync.get_session_state.return_value = {
            "session_id": "session-1",
            "status": SessionManager.PROCESSING,
        }

        result = session_manager.mark_session_completed(
            "session-1",
            0.25,
        )

    assert result is True
    assert interview.status == SessionManager.COMPLETED
    assert interview.risk_score == 0.25
    assert interview.end_time is not None
    db.commit.assert_called_once()


def test_mark_session_completed_returns_false_for_missing_session(
    session_manager,
):
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None

    with patch("orchestrator.session_manager.SessionLocal", return_value=db):
        result = session_manager.mark_session_completed(
            "missing-session",
            0.5,
        )

    assert result is False
