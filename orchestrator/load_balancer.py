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

from metrics.prometheus_metrics import SYSTEM_UTILIZATION
from orchestrator.worker_registry import WorkerRegistry

logger = logging.getLogger(__name__)


class BalancingStrategy(Enum):
    """Load balancing strategy enumeration"""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    WEIGHTED_LEAST_LOADED = "weighted_least_loaded"
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
            f"Load Balancer initialized with strategy: {strategy.value}"
        )

    def select_worker(self) -> dict[str, Any] | None:
        """
        Select a worker for task execution based on current strategy

        Returns:
            dict: Selected worker details or None if no workers available
        """

        if self.strategy == BalancingStrategy.ROUND_ROBIN:
            return self._select_round_robin()

        if self.strategy == BalancingStrategy.LEAST_LOADED:
            return self._select_least_loaded()

        if self.strategy == BalancingStrategy.QUEUE_BASED:
            return self._select_queue_based()

        # Default to least loaded
        return self._select_least_loaded()

    def _select_round_robin(self) -> dict[str, Any] | None:
        """
        Round Robin Strategy: Distribute tasks in sequence

        Distributes tasks evenly across all available workers
        in a circular fashion.

        Returns:
            dict: Next worker in rotation or None
        """

        available = self.worker_registry.get_available_workers()

        if not available:
            logger.warning(
                "No workers available for Round Robin selection"
            )
            return None

        worker = available[
            self.round_robin_index % len(available)
        ]

        self.round_robin_index += 1

        logger.debug(
            f"Round Robin selected worker: {worker['worker_id']}"
        )

        return worker

    def _select_least_loaded(self) -> dict[str, Any] | None:
        """
        Least Loaded Strategy:
        Assign to worker with fewest active tasks.

        Returns:
            dict: Least loaded worker or None
        """

        worker = (
            self.worker_registry.get_least_loaded_worker()
        )

        if not worker:
            logger.warning(
                "No workers available for Least Loaded selection"
            )
            return None

        logger.debug(
            f"Least Loaded selected worker: "
            f"{worker['worker_id']} "
            f"(active: "
            f"{worker['active_tasks']}/"
            f"{worker['capacity']})"
        )

        return worker

    def _select_weighted_least_loaded(self) -> dict[str, Any] | None:
        """
        Weighted Least Loaded Strategy

        Select worker based on:
            active_tasks / weight

        Lower score means the worker is less loaded relative
        to its capability.
        """

        available = self.worker_registry.get_available_workers()

        if not available:
            logger.warning("No workers available for Weighted Least Loaded selection")
            return None

        worker = min(
            available,
            key=lambda w: w["active_tasks"] / max(w.get("weight", 1), 1),
        )

        logger.debug(
            f"Weighted Least Loaded selected worker: {worker['worker_id']} "
            f"(weight={worker.get('weight', 1)}, active={worker['active_tasks']})"
        )

        return worker

    def _select_queue_based(self) -> dict[str, Any] | None:
        """
        Queue-based Strategy:
        Fallback to queue if no workers available.

        Returns:
            dict: Selected worker or None to trigger queueing
        """

        worker = (
            self.worker_registry.get_least_loaded_worker()
        )

        if not worker:
            logger.debug(
                "No workers available - "
                "task will be queued in Redis"
            )
            return None

        logger.debug(
            f"Queue-based selected worker: "
            f"{worker['worker_id']}"
        )

        return worker

    def switch_strategy(
        self,
        strategy: BalancingStrategy,
    ) -> None:
        """
        Switch to a different load balancing strategy

        Args:
            strategy: New strategy to use
        """

        self.strategy = strategy

        logger.info(
            f"Switched to {strategy.value} strategy"
        )

    def get_best_worker_for_priority(
        self,
        priority: str,
    ) -> dict[str, Any] | None:
        """
        Select worker considering task priority.

        Priority behavior:

        - High:
          Select the least-loaded worker.

        - Medium:
          Select the least-loaded worker below
          70% utilization. If all workers are at
          or above 70%, select the least-loaded
          available worker.

        - Low:
          Select the most-loaded available worker.

        Args:
            priority: Task priority
                      ("low", "medium", "high")

        Returns:
           dict: Selected worker or None if no workers available
        """

        available = (
            self.worker_registry.get_available_workers()
        )

        if not available:
            logger.warning("No workers available for priority-based selection")
            return None

        # High priority:
        # Select the worker with the fewest active tasks.
        if priority == "high":
            return min(
                available,
                key=lambda worker: worker["active_tasks"],
            )

        # Medium priority:
        # Select the least-loaded worker below
        # 70% utilization.
        if priority == "medium":

            underutilized = [
                worker
                for worker in available
                if worker["active_tasks"]
                < worker["capacity"] * 0.7
            ]

            if underutilized:
                return min(
                    underutilized,
                    key=lambda worker:
                    worker["active_tasks"],
                )

            # No worker is below 70%.
            # Do not assume available[0]
            # is the least-loaded worker.
            return min(
                available,
                key=lambda worker:
                worker["active_tasks"],
            )

        # Low priority:
        # Do not assume available[-1]
        # is the most-loaded worker.
        #
        # Explicitly select the worker
        # with the highest active task count.
        return max(
            available,
            key=lambda worker:
            worker["active_tasks"],
        )

    def is_system_overloaded(
        self,
        threshold: float = 0.9,
    ) -> bool:
        """
        Check if system is overloaded

        Args:
            threshold: Utilization threshold (0-1)

        Returns:
            bool: True if system utilization
                  exceeds threshold
        """

        stats = (
            self.worker_registry.get_worker_statistics()
        )

        utilization = (
            stats["capacity_utilization"] / 100
        )

        is_overloaded = utilization >= threshold

        if is_overloaded:
            logger.warning(
                f"System overloaded! Utilization: "
                f"{stats['capacity_utilization']}% "
                f"(threshold: "
                f"{threshold * 100}%)"
            )

        return is_overloaded

    def get_load_status(self) -> dict[str, Any]:
        """
        Get current system load status
        """

        stats = (
            self.worker_registry.get_worker_statistics()
        )

        available_workers = len(
            self.worker_registry.get_available_workers()
        )

        return {
            "strategy": self.strategy.value,
            "worker_stats": stats,
            "available_workers": available_workers,
            "system_overloaded":
                self.is_system_overloaded(),
            "timestamp": None,
        }