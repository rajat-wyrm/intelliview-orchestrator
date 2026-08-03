"""
Load Balancer
Implements intelligent task distribution strategies across worker nodes

Strategies:
1. Round Robin - Distribute tasks evenly in sequence
2. Least Loaded - Assign to worker with fewest active tasks (recommended)
3. Queue-based - Fallback to Redis queue if no workers available
"""

import logging
import threading
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

    def __init__(self, strategy: BalancingStrategy = BalancingStrategy.LEAST_LOADED, window_size: int = 5):
        """
        Initialize load balancer
        """
        self.worker_registry = WorkerRegistry()
        self.strategy = strategy
        self.round_robin_index = 0
        self.window_size = window_size
        self.load_history = []
        self._lock = threading.Lock()
        self.round_robin_lock = threading.Lock()
        self.last_assigned_worker_id = None
        logger.info(f"Load Balancer initialized with strategy: {strategy.value}")

    def select_worker(self) -> dict[str, Any] | None:
        with self._lock:
            if self.strategy == BalancingStrategy.ROUND_ROBIN:
                return self._select_round_robin()
            if self.strategy == BalancingStrategy.LEAST_LOADED:
                return self._select_least_loaded()
            if self.strategy == BalancingStrategy.QUEUE_BASED:
                return self._select_queue_based()

            return self._select_least_loaded()

    def _select_round_robin(self) -> dict[str, Any] | None:
        """
        Round Robin Strategy: Distribute tasks in sequence

        Distributes tasks evenly across all available workers in a circular fashion.
        Good for evenly distributed workloads.
        """
        available = self.worker_registry.get_available_workers()

        if not available:
            logger.warning("No workers available for Round Robin selection")
            return None

        # Select using round robin index (thread-safe)
        with self.round_robin_lock:
            worker = available[self.round_robin_index % len(available)]
            self.round_robin_index += 1

        logger.debug(f"Round Robin selected worker: {worker['worker_id']}")
        return worker

    def _select_least_loaded(self) -> dict[str, Any] | None:
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
        worker = self.worker_registry.get_least_loaded_worker()

        if not worker:
            logger.debug("No workers available - task will be queued in Redis")
            return None

        logger.debug(f"Queue-based selected worker: {worker['worker_id']}")
        return worker

    def switch_strategy(self, strategy: BalancingStrategy) -> None:
        with self._lock:
            self.strategy = strategy
            logger.info(f"Switched to {strategy.value} strategy")

    def get_best_worker_for_priority(self, priority: str) -> dict[str, Any] | None:
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
        stats = self.worker_registry.get_worker_statistics()
        available_workers = len(self.worker_registry.get_available_workers())

        return {
            "strategy": self.strategy.value,
            "worker_stats": stats,
            "available_workers": available_workers,
            "system_overloaded": self.is_system_overloaded(),
            "timestamp": None,
        }

    def record_current_load(self) -> None:
        with self._lock:
            stats = self.worker_registry.get_worker_statistics()
            utilization = stats["capacity_utilization"] / 100
            self.load_history.append(utilization)

            # Keep array sizing limited to the trailing time window limit
            if len(self.load_history) > self.window_size:
                self.load_history = self.load_history[-self.window_size :]

    def get_scaling_recommendation(self, up_threshold: float = 0.85, down_threshold: float = 0.30) -> str:
        with self._lock:
            if len(self.load_history) < self.window_size:
                return "no_change"

            avg_load = sum(self.load_history) / len(self.load_history)

            if avg_load >= up_threshold:
                return "scale_up"
            if avg_load <= down_threshold:
                return "scale_down"

            return "no_change"
