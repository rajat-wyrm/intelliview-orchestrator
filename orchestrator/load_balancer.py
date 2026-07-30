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

    def __init__(self, strategy: BalancingStrategy = BalancingStrategy.LEAST_LOADED):
        """
        Initialize load balancer

        Args:
            strategy: Load balancing strategy to use
        """
        self.worker_registry = WorkerRegistry()
        self.strategy = strategy
        self.last_assigned_worker_id = None
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

        # Sort for deterministic ordering
        available.sort(key=lambda w: w["worker_id"])

        idx = 0
        if hasattr(self, "last_assigned_worker_id") and self.last_assigned_worker_id:
            for i, w in enumerate(available):
                if w["worker_id"] == self.last_assigned_worker_id:
                    idx = (i + 1) % len(available)
                    break

        worker = available[idx]
        self.last_assigned_worker_id = worker["worker_id"]

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

    def get_best_worker_for_priority(self, priority: str) -> dict[str, Any] | None:
        """
        Select worker considering task priority

        Args:
            priority: Task priority ("low", "medium", "high")

        Returns:
            dict: Selected worker or None
        """
        available = self.worker_registry.get_available_workers()

        if not available:
            return None

        # For high priority, select least loaded
        if priority == "high":
            return min(available, key=lambda w: w["active_tasks"])

        # For medium priority, select from least loaded
        if priority == "medium":
            # Select a worker that's not overloaded
            underutilized = [w for w in available if w["active_tasks"] < w["capacity"] * 0.7]
            if underutilized:
                return min(underutilized, key=lambda w: w["active_tasks"])
            return min(available, key=lambda w: w["active_tasks"])

        # For low priority, select any available
        return max(available, key=lambda w: w["active_tasks"])  # Select the one with most load (fill it up)

    def is_system_overloaded(self, threshold: float = 0.9) -> bool:
        """
        Check if system is overloaded

        Args:
            threshold: Utilization threshold (0-1)

        Returns:
            bool: True if system utilization exceeds threshold
        """
        stats = self.worker_registry.get_worker_statistics()
        utilization = stats["capacity_utilization"] / 100  # Convert to 0-1 scale

        is_overloaded = utilization >= threshold

        if is_overloaded:
            logger.warning(
                f"System overloaded! Utilization: {stats['capacity_utilization']}% "
                f"(threshold: {threshold * 100}%)"
            )

        return is_overloaded

    def get_load_status(self) -> dict[str, Any]:
        """Get current system load status"""
        stats = self.worker_registry.get_worker_statistics()
        available_workers = len(self.worker_registry.get_available_workers())

        return {
            "strategy": self.strategy.value,
            "worker_stats": stats,
            "available_workers": available_workers,
            "system_overloaded": self.is_system_overloaded(),
            "timestamp": None,
        }
