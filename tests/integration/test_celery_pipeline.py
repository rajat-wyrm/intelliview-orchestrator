from unittest.mock import MagicMock, patch

import pytest

from workers.tasks import process_interview_session


@patch("workers.tasks.chord")
@patch("workers.tasks._after_parallel.delay")
@patch("workers.tasks.group")
@patch("workers.tasks.session_manager")
@patch("workers.tasks.SessionLocal")
def test_process_interview_session_pipeline(
    mock_session_local,
    mock_session_manager,
    mock_group,
    mock_after_parallel,
    mock_chord,
):
    """Integration test covering task lifecycle:

    queued -> processing
    """
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    interview = MagicMock()
    interview.status = "QUEUED"
    mock_db.execute.return_value.scalar_one_or_none.return_value = interview

    group_result = MagicMock()
    group_result.get.return_value = [
        {"risk_score": 0.2},
        {"risk_score": 0.1},
    ]
    mock_group.return_value.apply_async.return_value = group_result

    # Mock chord execution to prevent Redis backend lookup
    mock_chord_instance = MagicMock()
    mock_chord.return_value = mock_chord_instance

    # Execute task transition from QUEUED
    result = process_interview_session.run("test-session-001")

    # Assert lifecycle and worker updates
    assert result["session_id"] == "test-session-001"
    assert result["status"] == "processing_parallel"
    mock_session_manager.update_session_status.assert_called_with(
        "test-session-001",
        mock_session_manager.VIDEO_PROCESSING,
        {"stage": "parallel_video_audio"},
    )


@patch("workers.tasks.session_manager")
@patch("workers.tasks.SessionLocal")
def test_process_interview_session_pipeline_failure(
    mock_session_local,
    mock_session_manager,
):
    """Simulated failure case path."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    mock_db.execute.side_effect = Exception(
        "Database connection failed or session missing"
    )

    with pytest.raises(Exception) as exc_info:
        process_interview_session.run("test-session-failed")

    assert "Database connection failed or session missing" in str(exc_info.value)
