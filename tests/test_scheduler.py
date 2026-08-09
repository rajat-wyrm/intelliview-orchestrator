from unittest.mock import MagicMock, patch

import pytest

from orchestrator.scheduler import Scheduler, TaskPriority


@pytest.fixture
def scheduler():
    load_balancer = MagicMock()
    scheduler = Scheduler(load_balancer=load_balancer)

    scheduler.worker_registry = MagicMock()
    scheduler.session_manager = MagicMock()

    return scheduler


def test_schedule_task_dispatches_to_selected_worker(scheduler):
    scheduler.session_manager.get_session.return_value = {
        "session_id": "session-1",
        "status": "QUEUED",
    }

    scheduler.load_balancer.get_best_worker_for_priority.return_value = {
        "worker_id": "worker-1",
        "active_tasks": 0,
        "capacity": 4,
    }

    celery_task = MagicMock()
    celery_task.id = "task-123"

    with patch(
        "orchestrator.scheduler.process_interview_session.delay",
        return_value=celery_task,
    ):
        result = scheduler.schedule_task(
            "session-1",
            priority=TaskPriority.MEDIUM,
        )

    assert result is True

    scheduler.load_balancer.get_best_worker_for_priority.assert_called_once_with(
        "medium"
    )
    scheduler.worker_registry.increment_active_tasks.assert_called_once_with("worker-1")


def test_high_priority_is_passed_to_load_balancer(scheduler):
    scheduler.session_manager.get_session.return_value = {
        "session_id": "session-1",
        "status": "QUEUED",
    }

    scheduler.load_balancer.get_best_worker_for_priority.return_value = {
        "worker_id": "worker-1",
        "active_tasks": 0,
        "capacity": 4,
    }

    celery_task = MagicMock()
    celery_task.id = "task-high"

    with patch(
        "orchestrator.scheduler.process_interview_session.delay",
        return_value=celery_task,
    ):
        result = scheduler.schedule_task(
            "session-1",
            priority=TaskPriority.HIGH,
        )

    assert result is True
    scheduler.load_balancer.get_best_worker_for_priority.assert_called_once_with("high")


def test_low_priority_is_passed_to_load_balancer(scheduler):
    scheduler.session_manager.get_session.return_value = {
        "session_id": "session-1",
        "status": "QUEUED",
    }

    scheduler.load_balancer.get_best_worker_for_priority.return_value = {
        "worker_id": "worker-1",
        "active_tasks": 0,
        "capacity": 4,
    }

    celery_task = MagicMock()
    celery_task.id = "task-low"

    with patch(
        "orchestrator.scheduler.process_interview_session.delay",
        return_value=celery_task,
    ):
        result = scheduler.schedule_task(
            "session-1",
            priority=TaskPriority.LOW,
        )

    assert result is True
    scheduler.load_balancer.get_best_worker_for_priority.assert_called_once_with("low")


def test_schedule_task_returns_false_for_missing_session(scheduler):
    scheduler.session_manager.get_session.return_value = None

    result = scheduler.schedule_task("missing-session")

    assert result is False
    scheduler.load_balancer.get_best_worker_for_priority.assert_not_called()


def test_schedule_task_queues_when_no_worker_available(scheduler):
    scheduler.session_manager.get_session.return_value = {
        "session_id": "session-1",
        "status": "QUEUED",
    }

    scheduler.load_balancer.get_best_worker_for_priority.return_value = None

    with patch.object(
        scheduler,
        "_queue_task",
        return_value=True,
    ) as queue_task:
        result = scheduler.schedule_task("session-1")

    assert result is True
    queue_task.assert_called_once_with("session-1", 0)


def test_schedule_task_queues_with_delay(scheduler):
    scheduler.session_manager.get_session.return_value = {
        "session_id": "session-1",
        "status": "QUEUED",
    }

    scheduler.load_balancer.get_best_worker_for_priority.return_value = None

    with patch.object(
        scheduler,
        "_queue_task",
        return_value=True,
    ) as queue_task:
        result = scheduler.schedule_task(
            "session-1",
            delay_seconds=30,
        )

    assert result is True
    queue_task.assert_called_once_with("session-1", 30)


def test_dispatch_failure_rolls_back_worker_load(scheduler):
    scheduler.session_manager.get_session.return_value = {
        "session_id": "session-1",
        "status": "QUEUED",
    }

    scheduler.load_balancer.get_best_worker_for_priority.return_value = {
        "worker_id": "worker-1",
        "active_tasks": 0,
        "capacity": 4,
    }

    with patch(
        "orchestrator.scheduler.process_interview_session.delay",
        side_effect=RuntimeError("Celery unavailable"),
    ):
        result = scheduler.schedule_task("session-1")

    assert result is False

    scheduler.worker_registry.increment_active_tasks.assert_called_once_with("worker-1")
    scheduler.worker_registry.decrement_active_tasks.assert_called_once_with("worker-1")
    scheduler.session_manager.mark_session_failed.assert_called_once()


def test_empty_worker_pool_can_not_accept_task(scheduler):
    scheduler.worker_registry.get_available_workers.return_value = []

    assert scheduler.can_accept_task() is False


def test_worker_pool_can_accept_task(scheduler):
    scheduler.worker_registry.get_available_workers.return_value = [
        {
            "worker_id": "worker-1",
            "active_tasks": 0,
            "capacity": 4,
        }
    ]

    assert scheduler.can_accept_task() is True


def test_estimated_wait_time_is_zero_when_worker_available(scheduler):
    scheduler.worker_registry.get_available_workers.return_value = [
        {
            "worker_id": "worker-1",
            "active_tasks": 0,
            "capacity": 4,
        }
    ]

    assert scheduler.get_estimated_wait_time() == 0


def test_estimated_wait_time_is_minus_one_when_no_workers(scheduler):
    scheduler.worker_registry.get_available_workers.return_value = []
    scheduler.worker_registry.get_worker_statistics.return_value = {
        "total_active_tasks": 0,
        "total_workers": 0,
    }

    assert scheduler.get_estimated_wait_time() == -1
