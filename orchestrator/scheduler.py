"""
Scheduler
Controls when and how tasks are executed

Responsibilities:
- Schedule interview tasks to workers
- Handle task prioritization
- Support delayed execution
- Manage task retries
- Coordinate with load balancer
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from orchestrator.load_balancer import BalancingStrategy, LoadBalancer
from orchestrator.session_manager import SessionManager
from orchestrator.worker_registry import WorkerRegistry
from workers.tasks import process_interview_session

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""

    LOW = 0
    MEDIUM = 1
    HIGH = 2


class Scheduler:
    """
    Manages task scheduling and distribution to workers
    """

    def __init__(self, load_balancer: LoadBalancer | None = None):
        """
        Initialize scheduler

        Args:
            load_balancer: Optional custom LoadBalancer instance
        """
        self.load_balancer = load_balancer or LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
        self.worker_registry = WorkerRegistry()
        self.session_manager = SessionManager()
        logger.info("Scheduler initialized with Least Loaded strategy")

    def schedule_task(
       
        self,
        session_id: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        delay_seconds: int = 0,
    ) -> bool:
     

        """
        Schedule an interview task for execution

        Execution flow:
        1. Get session details
        2. Select worker using load balancer
        3. If worker available: assign task directly
        4. If no worker: queue task in Redis
        5. Update session status

        Args:
            session_id: Interview session ID
            priority: Task priority level
            delay_seconds: Seconds to delay execution (0 = immediate)

        Returns:
            bool: True if scheduling successful
        """
        logger.info("===== schedule_task() called for session %s =====", session_id)
        try:
            logger.info(f"Scheduling task for session {session_id} (priority: {priority.name})")

            # Verify session exists
            session_data = self.session_manager.get_session(session_id)
            if not session_data:
                logger.error(f"Session {session_id} not found")
                return False

            # Select worker
            worker = self.load_balancer.get_best_worker_for_priority(priority.name.lower())

            if not worker:
                logger.warning(f"No worker available for session {session_id} - queueing task")
                # Queue task directly to Redis, it will be picked up by any available worker
                return self._queue_task(session_id, delay_seconds)

            logger.info(
                f"Assigned session {session_id} to worker {worker['worker_id']} "
                f"(load: {worker['active_tasks']}/{worker['capacity']})"
            )

            # Update worker active task count
            self.worker_registry.increment_active_tasks(worker["worker_id"])

            # Enqueue the task — if Celery dispatch fails, roll back the
            # worker counter so the registry doesn't permanently over-report
            # load for this worker.
            try:
                logger.info("===== About to dispatch Celery task =====")
                if delay_seconds > 0:
                    task = process_interview_session.apply_async(args=[session_id], countdown=delay_seconds)
                    #logger.info(f"Task queued with {delay_seconds}s delay: {task.id}")
                else:
                    task = process_interview_session.delay(session_id)
                    #logger.info(f"Task enqueued immediately: {task.id}")

                logger.info("===== Celery Task ID: %s =====", task.id)

            except Exception as dispatch_err:
                logger.error(f"Failed to enqueue task for session {session_id}: {dispatch_err}")
                self.worker_registry.decrement_active_tasks(worker["worker_id"])
                raise

            return True

        except Exception as e:
            logger.error(f"Error scheduling task: {e!s}")
            self.session_manager.mark_session_failed(session_id, f"Scheduling error: {e!s}")
            return False

    def _queue_task(self, session_id: str, delay_seconds: int = 0) -> bool:
        """
        Queue a task to Redis without direct worker assignment

        Args:
            session_id: Session ID
            delay_seconds: Delay before execution

        Returns:
            bool: True if queued successfully
        """
        try:
            if delay_seconds > 0:
                task = process_interview_session.apply_async(args=[session_id], countdown=delay_seconds)
            else:
                task = process_interview_session.delay(session_id)

            logger.info(f"Task queued in Redis: {session_id} (task_id: {task.id})")
            return True

        except Exception as e:
            logger.error(f"Error queuing task: {e!s}")
            return False

    def get_scheduling_status(self) -> dict[str, Any]:
        """Get current scheduling and load information"""
        load_status = self.load_balancer.get_load_status()

        # Check for overloaded system
        is_overloaded = load_status["system_overloaded"]

        # Recommend strategy switch if needed
        recommendation = None
        if is_overloaded and self.load_balancer.strategy != BalancingStrategy.LEAST_LOADED:
            recommendation = "Switch to LEAST_LOADED strategy to optimize load distribution"

        return {
            "load_balancer_strategy": self.load_balancer.strategy.value,
            "worker_stats": load_status["worker_stats"],
            "available_workers": load_status["available_workers"],
            "system_overloaded": is_overloaded,
            "recommendation": recommendation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def can_accept_task(self) -> bool:
        """
        Check if system can accept new tasks

        Returns:
            bool: True if system has capacity
        """
        available = self.worker_registry.get_available_workers()
        return len(available) > 0

    def get_estimated_wait_time(self, priority: TaskPriority = TaskPriority.MEDIUM) -> int:
        """
        Estimate wait time for a task with given priority

        Args:
            priority: Task priority

        Returns:
            int: Estimated wait time in seconds (rough estimate)
        """
        available = self.worker_registry.get_available_workers()

        if available:
            # If worker available, minimal wait
            return 0

        # Estimate based on system load
        stats = self.worker_registry.get_worker_statistics()
        avg_task_duration = 600  # Assume ~10 min per task
        total_queued_tasks = stats["total_active_tasks"]
        num_workers = stats["total_workers"]

        if num_workers == 0:
            return -1  # Cannot estimate

        # Rough estimate: (queued_tasks / workers) * avg_duration
        return int((total_queued_tasks / num_workers) * avg_task_duration)
