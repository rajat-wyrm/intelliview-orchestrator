"""
Load Balancer
Implements intelligent task distribution strategies across worker nodes

Strategies:
1. Round Robin - Distribute tasks evenly in sequence
2. Least Loaded - Assign to worker with fewest active tasks (recommended)
3. Queue-based - Fallback to Redis queue if no workers available
"""

import json
import logging
import threading
from enum import Enum
from typing import Any

from orchestrator.redis_client import get_redis_client
from orchestrator.worker_registry import WorkerRegistry

logger = logging.getLogger(__name__)


class BalancingStrategy(Enum):
    """Load balancing strategy enumeration"""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    QUEUE_BASED = "queue_based"


class LoadBalancer:
    """
    Implements load balancing for task distribution across worker nodes
    """

    def __init__(
        self,
        strategy: BalancingStrategy = BalancingStrategy.LEAST_LOADED,
    ):
        """
        Initialize load balancer

        Args:
            strategy: Load balancing strategy to use
        """
        self.worker_registry = WorkerRegistry()
        self.strategy = strategy
        self.session_affinity_enabled = True
        self.round_robin_index = 0
<<<<<<< HEAD

=======
>>>>>>> upstream/main
        self.redis_client = get_redis_client()
        self._lock = threading.Lock()
        self.round_robin_lock = threading.Lock()

<<<<<<< HEAD
        logger.info(
            "Load Balancer initialized with strategy: %s",
            strategy.value,
        )

    def _is_valid_worker(self, worker: dict[str, Any]) -> bool:
        """
        Validate worker capacity before scheduling tasks.

        Args:
            worker: Worker information.

        Returns:
            bool: True if worker capacity is valid.
        """
        if worker["capacity"] <= 0:
            logger.warning(
                "Skipping worker %s because it has an invalid capacity (%s).",
                worker["worker_id"],
                worker["capacity"],
            )
            return False

        return True

    def _get_valid_workers(self) -> list[dict[str, Any]]:
        """
        Return all available workers with valid capacity.
        """

        available = self.worker_registry.get_available_workers()

        return [worker for worker in available if self._is_valid_worker(worker)]

    def select_worker(self, task: dict[str, Any] | None = None) -> dict[str, Any] | None:
=======
    def select_worker(self, task: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """
        Select a worker for task execution based on current strategy

        Args:
            task: Task payload dict (required for queue-based fallback)

        Returns:
            dict: Selected worker details or None if no workers available
        """
>>>>>>> upstream/main
        with self._lock:
            if self.strategy == BalancingStrategy.ROUND_ROBIN:
                return self._select_round_robin()

            if self.strategy == BalancingStrategy.LEAST_LOADED:
                return self._select_least_loaded()

            if self.strategy == BalancingStrategy.QUEUE_BASED:
<<<<<<< HEAD
                return self._select_queue_based(task)

=======
                return self._select_queue_based(task=task)
            # Default to least loaded
>>>>>>> upstream/main
            return self._select_least_loaded()

    def select_worker_with_affinity(
        self,
        preferred_worker_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Select a worker using session affinity.

        If the preferred worker is healthy and has available capacity,
        use it. Otherwise, fall back to the configured load balancing
        strategy.
        """
        if self.session_affinity_enabled and preferred_worker_id:
            worker = self.worker_registry.get_worker(preferred_worker_id)

            if worker and worker["status"] == "healthy" and worker["active_tasks"] < worker["capacity"]:
                logger.debug(
                    "Session affinity selected worker %s",
                    preferred_worker_id,
                )
                return worker

        return self.select_worker()

    def _select_round_robin(self) -> dict[str, Any] | None:
        """
<<<<<<< HEAD
        Round Robin Strategy.
=======
        Round Robin Strategy: Distribute tasks evenly in sequence

        Cycles through available workers in order, regardless of current load.
>>>>>>> upstream/main

        Returns:
            Selected worker or None.
        """

        workers = self._get_valid_workers()

        if not workers:
            logger.warning("No valid workers available for Round Robin selection")
            return None

<<<<<<< HEAD
        # Thread-safe round robin selection
=======
>>>>>>> upstream/main
        with self.round_robin_lock:
            worker = workers[self.round_robin_index % len(workers)]
            self.round_robin_index += 1

        logger.debug(
            "Round Robin selected worker: %s",
            worker["worker_id"],
        )

        return worker

    def _select_least_loaded(self) -> dict[str, Any] | None:
        """
        Least Loaded Strategy.

        Returns:
            Least loaded worker or None.
        """

        workers = self._get_valid_workers()

        if not workers:
            logger.warning("No workers with valid capacity available")
            return None

        worker = min(
            workers,
            key=lambda w: w["active_tasks"],
        )

        logger.debug(
            "Least Loaded selected worker: %s (active: %s/%s)",
            worker["worker_id"],
            worker["active_tasks"],
            worker["capacity"],
        )

        return worker

<<<<<<< HEAD
    def _select_queue_based(
        self,
        task: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Queue-based Strategy.
=======
    def _select_queue_based(self, task: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """
        Queue-based Strategy: Fallback to Redis queue if no workers available

        First tries to select a worker. If none available and a task is provided,
        enqueues the task in Redis for later processing.

        Args:
            task: Task payload dict to be enqueued if worker is unavailable
>>>>>>> upstream/main

        Returns:
            Selected worker or None.
        """

<<<<<<< HEAD
        workers = self._get_valid_workers()

        if not workers:
            logger.debug("No valid workers available - task will be queued")

            if task:
                try:
                    serialized_task = json.dumps(task)
                    self.redis_client.rpush(
                        "task_queue",
                        serialized_task,
                    )

                    logger.info("Task queued in Redis")
                except Exception as e:
                    logger.error(
                        "Failed to queue task: %s",
                        e,
                    )

=======
        if not worker:
            logger.debug("No workers available - fallback to Redis queue")
            if task:
                try:
                    serialized_task = json.dumps(task)
                    self.redis_client.rpush("task_queue", serialized_task)
                    logger.info("Task successfully enqueued into Redis queue")
                except Exception as e:
                    logger.error(f"Failed to push task to Redis queue: {e}")
>>>>>>> upstream/main
            return None

        worker = min(
            workers,
            key=lambda w: w["active_tasks"],
        )

        logger.debug(
            "Queue-based selected worker: %s",
            worker["worker_id"],
        )

        return worker

<<<<<<< HEAD
    def switch_strategy(
        self,
        strategy: BalancingStrategy,
    ) -> None:
        """
        Switch load balancing strategy.
        """

        with self._lock:
            self.strategy = strategy
=======
    def switch_strategy(self, strategy: BalancingStrategy) -> None:
        """
        Switch to a different load balancing strategy

        Args:
            strategy: New strategy to use
        """
        with self._lock:
            self.strategy = strategy
        logger.info(f"Switched to {strategy.value} strategy")
>>>>>>> upstream/main

        logger.info(
            "Switched to %s strategy",
            strategy.value,
        )

    def get_best_worker_for_priority(
        self,
        priority: str,
    ) -> dict[str, Any] | None:
        """
    Select worker considering task priority.

    Args:
        priority: Task priority ("high", "medium", or "low")

    Returns:
        Selected worker or None.
    """

        workers = self._get_valid_workers()

        if not workers:
            logger.warning("No workers with valid capacity available")
            return None

        # High priority: least loaded worker
        if priority == "high":
<<<<<<< HEAD
            return min(
                workers,
                key=lambda w: w["active_tasks"],
=======
            return min(available, key=lambda w: w["active_tasks"])

        # For medium priority, select from least loaded
        if priority == "medium":
            underutilized = [w for w in available if w["active_tasks"] < w["capacity"] * 0.7]
            if underutilized:
                return underutilized[0]
            return available[0]

        # For low priority, select any available
        return available[-1]

    def is_system_overloaded(self, threshold: float = 0.9) -> bool:
        """
        Check if system is overloaded

        Args:
            threshold: Utilization threshold (0-1)

        Returns:
            bool: True if system utilization exceeds threshold
        """
        stats = self.worker_registry.get_worker_statistics()
        utilization = stats["capacity_utilization"] / 100

        is_overloaded = utilization >= threshold

        if is_overloaded:
            logger.warning(
                f"System overloaded! Utilization: {stats['capacity_utilization']}% "
                f"(threshold: {threshold * 100}%)"
>>>>>>> upstream/main
            )

        # Medium priority: prefer underutilized workers
        if priority == "medium":
            underutilized = [
                w
                for w in workers
                if w["active_tasks"] < w["capacity"] * 0.7
            ]

            if underutilized:
                return min(
                    underutilized,
                    key=lambda w: w["active_tasks"],
                )

            return min(
                workers,
                key=lambda w: w["active_tasks"],
            )

        # Low priority: use the most loaded valid worker
        return max(
            workers,
            key=lambda w: w["active_tasks"],
        )


    def is_system_overloaded(
        self,
        threshold: float = 0.9,
    ) -> bool:
        """
    Check if system utilization exceeds threshold.

    Args:
        threshold: Utilization threshold (0-1).

    Returns:
        True if system utilization exceeds the threshold, otherwise False.
    """

        stats = self.worker_registry.get_worker_statistics()

        # Convert percentage (0-100) to decimal (0-1)
        utilization = stats["capacity_utilization"] / 100

        overloaded = utilization >= threshold

        if overloaded:
            logger.warning(
                "System overloaded! Utilization: %s%% (threshold: %s%%)",
                stats["capacity_utilization"],
                threshold * 100,
            )

        return overloaded

    def get_load_status(self) -> dict[str, Any]:
        """
        Get current system load status.
        """

        stats = self.worker_registry.get_worker_statistics()

        available_workers = len(self._get_valid_workers())

        return {
            "strategy": self.strategy.value,
            "worker_stats": stats,
            "available_workers": available_workers,
            "system_overloaded": self.is_system_overloaded(),
            "timestamp": None,
        }
