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

    def __init__(self, strategy: BalancingStrategy = BalancingStrategy.LEAST_LOADED):
        """
        Initialize load balancer

        Args:
            strategy: Load balancing strategy to use
        """
        self.worker_registry = WorkerRegistry()
        self.strategy = strategy
        self.round_robin_index = 0
        logger.info(f"Load Balancer initialized with strategy: {strategy.value}")

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
        if self.strategy == BalancingStrategy.WEIGHTED_LEAST_LOADED:
            return self._select_weighted_least_loaded()
        if self.strategy == BalancingStrategy.QUEUE_BASED:
            return self._select_queue_based()
        # Default to least loaded
        return self._select_least_loaded()

    def _select_round_robin(self) -> dict[str, Any] | None:
        """
        Round Robin Strategy: Distribute tasks in sequence

        Distributes tasks evenly across all available workers in a circular fashion.
        Good for evenly distributed workloads.

        Returns:
            dict: Next worker in rotation or None if no workers available
        """
        available = self.worker_registry.get_available_workers()

        if not available:
            logger.warning("No workers available for Round Robin selection")
            return None

        # FIX: Sort by worker_id to ensure stable order independent of registry changes
        available_sorted = sorted(available, key=lambda w: w["worker_id"])

        # Select using round robin index on the sorted list
        worker = available_sorted[self.round_robin_index % len(available_sorted)]
        self.round_robin_index += 1

        logger.debug(f"Round Robin selected worker: {worker['worker_id']}")
        return worker

    def _select_least_loaded(self) -> dict[str, Any] | None:
        """
        Least Loaded Strategy: Assign to worker with fewest active tasks (RECOMMENDED)

        Selects the worker with the lowest number of active tasks among available workers.
        Provides better load balancing for varying task durations.

        Returns:
            dict: Least loaded worker or None if no workers available
        """
        worker = self.worker_registry.get_least_loaded_worker()

        if not worker:
            logger.warning("No workers available for Least Loaded selection")
            return None

        logger.debug(
            f"Least Loaded selected worker: {worker['worker_id']} "
            f"(active: {worker['active_tasks']}/{worker['capacity']})"
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
        Queue-based Strategy: Fallback to queue if no workers available

        First tries to select a worker. If none available, returns None to signal
        task should be queued in Redis for later processing.

        Returns:
            dict: Selected worker or None to trigger queueing
        """
        worker = self.worker_registry.get_least_loaded_worker()

        if not worker:
            logger.debug("No workers available - task will be queued in Redis")
            return None

        logger.debug(f"Queue-based selected worker: {worker['worker_id']}")
        return worker

    def switch_strategy(self, strategy: BalancingStrategy) -> None:
        """
        Switch to a different load balancing strategy

        Args:
            strategy: New strategy to use
        """
        self.strategy = strategy
        logger.info(f"Switched to {strategy.value} strategy")

    ...

    def get_best_worker_for_priority(self, priority: str) -> dict[str, Any] | None:
        available = self.worker_registry.get_available_workers()

        if not available:
            logger.warning("No workers available for priority-based selection")
            return None

        if priority == "high":
            return min(
                available,
                key=lambda w: w["active_tasks"],
            )

        if priority == "medium":
            underutilized = [
                worker
                for worker in available
                if worker["active_tasks"] < worker["capacity"] * 0.7
            ]

            if underutilized:
                return min(
                    underutilized,
                    key=lambda w: w["active_tasks"],
                )

            return min(
                available,
                key=lambda w: w["active_tasks"],
            )

        return max(
            available,
            key=lambda w: w["active_tasks"],
        )