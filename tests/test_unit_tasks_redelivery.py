"""
Unit tests for the redelivery/idempotency guard in process_interview_session.

`celery_app.py` sets `task_acks_late=True` + `task_reject_on_worker_lost=True`,
so a task's message is only acked once it returns. If the worker dies
mid-flight - e.g. while blocked on `result.get()` waiting on the video/audio
group - the broker redelivers the same message to another worker while the
session's DB row is still sitting in an active status.

These tests simulate that redelivery at the unit level:

  * test_redelivery_of_in_flight_session_is_skipped
        Session is VIDEO_PROCESSING with a fresh (30s-old) start_time ->
        the redelivered task must NOT dispatch a second video/audio group.

  * test_stale_active_session_is_recovered
        Session is VIDEO_PROCESSING but start_time is older than
        task_time_limit -> the previous attempt is provably dead, so this
        delivery should recover by dispatching the group as normal.

  * test_fresh_queued_session_dispatches_normally
        Sanity check: a brand new QUEUED session still dispatches the
        group exactly once - the guard doesn't affect the happy path.

Only the DB session, the video/audio group dispatch, and the
`_after_parallel` callback are mocked; everything else (task_manager,
SessionManager instance, etc.) is the real thing, same as
test_unit_session_manager.py.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from prometheus_client import generate_latest

from monitoring.prometheus_metrics import registry
from workers import tasks


class _FakeGroupResult:
    """Stand-in for the Celery GroupResult returned by group(...).apply_async()."""

    def __init__(self, video_result, audio_result):
        self._video_result = video_result
        self._audio_result = audio_result

    def get(self, timeout=None):
        return self._video_result, self._audio_result


def _make_interview(status, start_time):
    interview = MagicMock()
    interview.status = status
    interview.start_time = start_time
    return interview


def _wire_db_session(interview):
    """A SessionLocal() stand-in whose .execute(...).scalar_one_or_none()
    returns `interview` for every query in the task.
    """
    db_session = MagicMock()
    db_session.execute.return_value.scalar_one_or_none.return_value = interview
    return db_session


def test_redelivery_of_in_flight_session_is_skipped():
    recent_start = datetime.now(timezone.utc) - timedelta(seconds=30)
    interview = _make_interview(tasks.session_manager.VIDEO_PROCESSING, recent_start)
    db_session = _wire_db_session(interview)

    with (
        patch.object(tasks, "SessionLocal", return_value=db_session),
        patch.object(tasks, "group") as fake_group,
        patch.object(
            tasks.session_manager, "update_session_status"
        ) as fake_update_status,
    ):
        result = tasks.process_interview_session.run("session-123")

    fake_group.assert_not_called()
    fake_update_status.assert_not_called()
    assert result["status"] == "skipped_duplicate_delivery"
    assert result["session_id"] == "session-123"


def test_stale_active_session_is_recovered():
    long_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    interview = _make_interview(tasks.session_manager.VIDEO_PROCESSING, long_ago)
    db_session = _wire_db_session(interview)

    with (
        patch.object(tasks, "SessionLocal", return_value=db_session),
        patch.object(tasks, "chord") as fake_chord,
        patch.object(tasks, "group") as fake_group,
    ):
        fake_chord_obj = MagicMock()
        fake_chord.return_value = fake_chord_obj
        fake_chord_obj.return_value = MagicMock()
        result = tasks.process_interview_session.run("session-456")

    fake_group.assert_called_once()
    fake_chord.assert_called_once()
    fake_chord_obj.assert_called_once()
    assert result["status"] == "processing_parallel"


def test_fresh_queued_session_dispatches_normally():
    interview = _make_interview("QUEUED", None)
    db_session = _wire_db_session(interview)

    with (
        patch.object(tasks, "SessionLocal", return_value=db_session),
        patch.object(tasks, "chord") as fake_chord,
        patch.object(tasks, "group") as fake_group,
    ):
        fake_chord_obj = MagicMock()
        fake_chord.return_value = fake_chord_obj
        fake_chord_obj.return_value = MagicMock()
        result = tasks.process_interview_session.run("session-789")

    fake_group.assert_called_once()
    fake_chord.assert_called_once()
    fake_chord_obj.assert_called_once()
    assert result["status"] == "processing_parallel"


def test_average_evaluation_latency_metric_exists():
    metrics = generate_latest(registry).decode()

    assert "intelliview_avg_evaluation_latency_seconds" in metrics


def test_average_evaluation_latency_updates_after_evaluation():
    tasks.evaluation_latency_total = 0.0
    tasks.evaluation_latency_count = 0

    start_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    interview = _make_interview("EVALUATING", start_time)
    db_session = _wire_db_session(interview)

    risk_report = {
        "final_risk_score": 0.5,
        "risk_classification": "low",
    }

    with (
        patch.object(tasks, "evaluate_answers", return_value={"score": 0.8}),
        patch.object(
            tasks.RiskScoringEngine,
            "generate_risk_report",
            return_value=risk_report,
        ),
        patch.object(tasks, "SessionLocal", return_value=db_session),
        patch.object(tasks.session_manager, "update_session_status"),
        patch.object(
            tasks.time,
            "perf_counter",
            side_effect=[0.0, 1.0],
        ),
        patch.object(
            tasks,
            "datetime",
        ) as mock_datetime,
    ):
        mock_datetime.now.return_value = datetime.now(timezone.utc)
        mock_datetime.side_effect = datetime

        tasks._after_parallel.run(
            [{"video": "result"}, {"audio": "result"}],
            "session-123",
        )

    assert tasks.evaluation_latency_count == 1
    assert tasks.evaluation_latency_total > 0
    assert tasks.AVG_EVALUATION_LATENCY._value.get() > 0


def test_average_evaluation_latency_running_average():
    tasks.evaluation_latency_total = 0.0
    tasks.evaluation_latency_count = 0

    first_start = datetime.now(timezone.utc) - timedelta(seconds=10)
    second_start = datetime.now(timezone.utc) - timedelta(seconds=30)

    first_interview = _make_interview("EVALUATING", first_start)
    second_interview = _make_interview("EVALUATING", second_start)

    first_db = _wire_db_session(first_interview)
    second_db = _wire_db_session(second_interview)

    risk_report = {
        "final_risk_score": 0.5,
        "risk_classification": "low",
    }

    with (
        patch.object(tasks, "evaluate_answers", return_value={"score": 0.8}),
        patch.object(
            tasks.RiskScoringEngine,
            "generate_risk_report",
            return_value=risk_report,
        ),
        patch.object(tasks.session_manager, "update_session_status"),
        patch.object(
            tasks,
            "SessionLocal",
            side_effect=[first_db, second_db],
        ),
    ):
        tasks._after_parallel.run(
            [{"video": "result"}, {"audio": "result"}],
            "session-1",
        )

        tasks._after_parallel.run(
            [{"video": "result"}, {"audio": "result"}],
            "session-2",
        )

    assert tasks.evaluation_latency_count == 2

    expected_average = tasks.evaluation_latency_total / tasks.evaluation_latency_count

    assert tasks.AVG_EVALUATION_LATENCY._value.get() == expected_average


def test_average_evaluation_latency_exposed_through_metrics_endpoint():
    from fastapi.testclient import TestClient

    from orchestrator import main

    with (
        patch.object(
            main.health_monitor,
            "_check_all_dependencies",
            return_value={
                "redis": {"status": "healthy"},
                "postgres": {"status": "healthy"},
            },
        ),
        patch.object(
            main.worker_registry,
            "get_all_workers",
            return_value=[],
        ),
        patch.object(
            main.worker_registry,
            "detect_unhealthy_workers",
            return_value=[],
        ),
    ):
        response = TestClient(main.app).get("/metrics")

    assert response.status_code == 200
    assert "intelliview_avg_evaluation_latency_seconds" in response.text
