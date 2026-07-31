"""
Load Balancer
Implements intelligent task distribution strategies across worker nodes

Strategies:
1. Round Robin - Distribute tasks evenly in sequence
2. Least Loaded - Assign to worker with fewest active tasks (recommended)
3. Queue-based - Fallback to Redis queue if no workers available
"""

import logging
from enum import Enum
from typing import Any

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

    def select_worker(self) -> dict[str, Any] | None:
        """
        Select a worker for task execution based on current strategy.

        Returns:
            Selected worker details or None.
        """
        if self.strategy == BalancingStrategy.ROUND_ROBIN:
            return self._select_round_robin()

        if self.strategy == BalancingStrategy.LEAST_LOADED:
            return self._select_least_loaded()

        if self.strategy == BalancingStrategy.QUEUE_BASED:
            return self._select_queue_based()

        return self._select_least_loaded()

    def _select_round_robin(self) -> dict[str, Any] | None:
        """
        Round Robin Strategy.
        """

        workers = self._get_valid_workers()

        if not workers:
            logger.warning("No valid workers available for Round Robin selection")
            return None

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

    def switch_strategy(
        self,
        strategy: BalancingStrategy,
    ) -> None:
        """
        Switch load balancing strategy.
        """

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
        """

        workers = self._get_valid_workers()

        if not workers:
            logger.warning("No workers with valid capacity available")
            return None

        if priority == "high":
            return min(
                workers,
                key=lambda w: w["active_tasks"],
            )

        if priority == "medium":
            underutilized = [
                worker for worker in workers if worker["active_tasks"] < worker["capacity"] * 0.7
            ]

            if underutilized:
                return underutilized[0]

            return workers[0]

        return workers[-1]

    def is_system_overloaded(
        self,
        threshold: float = 0.9,
    ) -> bool:
        """
        Check if system utilization exceeds threshold.
        """

        stats = self.worker_registry.get_worker_statistics()

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
