"""

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
        self.round_robin_index = 0

        self.redis_client = get_redis_client()
        self._lock = threading.Lock()
        self.round_robin_lock = threading.Lock()

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
        with self._lock:
            if self.strategy == BalancingStrategy.ROUND_ROBIN:
                return self._select_round_robin()

            if self.strategy == BalancingStrategy.LEAST_LOADED:
                return self._select_least_loaded()

            if self.strategy == BalancingStrategy.QUEUE_BASED:
                return self._select_queue_based(task)

            return self._select_least_loaded()

    def _select_round_robin(self) -> dict[str, Any] | None:
        """
        Round Robin Strategy.

        Returns:
            Selected worker or None.
        """

        workers = self._get_valid_workers()

        if not workers:
            logger.warning("No valid workers available for Round Robin selection")
            return None

        # Thread-safe round robin selection
        with self.round_robin_lock:
            worker = workers[self.round_robin_index % len(workers)]
            self.round_robin_index += 1

        logger.debug(
            "Round Robin selected worker: %s",
            worker["worker_id"],
        )

        return worker

    def _select_least_loaded(self, task: dict[str, Any] | None = None,) -> dict[str, Any] | None:
        """
        Least Loaded Strategy.

        Returns:
            Least loaded worker or None.
        """

        workers = self._get_valid_workers()

        if not workers:
            logger.debug("No valid workers available")

            if task:
                try:
                    serialized_task = json.dumps(task)
                    self.redis_client.rpush(
                        "task_queue",
                        serialized_task,
                    )

                    logger.info("Task queued in Redis")

                except Exception as e:
                    logger.error("Failed to queue task: %s", e)

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

    def _select_queue_based(self) -> dict[str, Any] | None:
        """
        Queue-based Strategy.

        Returns:
            Selected worker or None.
        """

        workers = self._get_valid_workers()

        if not workers:
            logger.debug("No valid workers available - task will be queued")
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

    def switch_strategy( self, strategy: BalancingStrategy,) -> None:
        """
        Switch load balancing strategy.
        """

        with self._lock:
            self.strategy = strategy

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
            return min(
                workers,
                key=lambda w: w["active_tasks"],
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
