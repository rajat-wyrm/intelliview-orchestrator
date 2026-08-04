"""
Strategies:
1. Round Robin - Distribute tasks evenly in sequence
2. Least Loaded - Assign to worker with fewest active tasks (recommended)
3. Queue-based - Fallback to Redis queue if no workers available
"""

import logging
from enum import Enum
from typing import Any

from metrics.prometheus_metrics import SYSTEM_UTILIZATION
from orchestrator.redis_client import get_redis_client
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
        self._lock = threading.Lock()

        self.session_affinity_enabled = True
        self.redis_client = get_redis_client()

        self.round_robin_lock = threading.Lock()
        logger.info(f"Load Balancer initialized with strategy: {strategy.value}")

    def _is_valid_worker(self, worker: dict[str, Any]) -> bool:
        """Return True only for workers with positive capacity."""
        if worker["capacity"] <= 0:
            logger.warning(
                "Skipping worker %s because it has invalid capacity (%s).",
                worker["worker_id"],
                worker["capacity"],
            )
            return False

        return True

    def _get_valid_workers(self) -> list[dict[str, Any]]:
        """Return only workers whose capacity is greater than zero."""
        available = self.worker_registry.get_available_workers()

        return [worker for worker in available if self._is_valid_worker(worker)]

    def select_worker(self) -> dict[str, Any] | None:
        with self._lock:
            if self.strategy == BalancingStrategy.ROUND_ROBIN:
                return self._select_round_robin()

            if self.strategy == BalancingStrategy.LEAST_LOADED:
                return self._select_least_loaded()

            if self.strategy == BalancingStrategy.QUEUE_BASED:
                return self._select_queue_based()
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

        workers = self._get_valid_workers()

        if not workers:
            logger.warning("No workers with valid capacity available for Round Robin")
            return None

        # Select using round robin index (thread-safe)
        with self.round_robin_lock:
            worker = workers[self.round_robin_index % len(workers)]
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

        workers = self._get_valid_workers()

        if not workers:
            logger.warning("No workers with valid capacity available")
            return None

        worker = min(
            workers,
            key=lambda w: w["active_tasks"],
        )

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

        workers = self._get_valid_workers()

        if not workers:
            logger.debug("No valid workers available")
            return None

        worker = min(
            workers,
            key=lambda w: w["active_tasks"],
        )

        logger.debug(f"Queue-based selected worker: {worker['worker_id']}")
        return worker

    def switch_strategy(self, strategy: BalancingStrategy) -> None:

        with self._lock:
            self.strategy = strategy

        logger.info(
            "Switched to %s strategy",
            strategy.value,
        )

    def get_best_worker_for_priority(self, priority: str) -> dict[str, Any] | None:
        """
        Switch to a different load balancing strategy

        Args:
            strategy: New strategy to use
        """
        self.strategy = strategy
        logger.info(f"Switched to {strategy.value} strategy")

    def get_best_worker_for_priority(self, priority: str) -> dict[str, Any] | None:
        """Select worker considering task priority while respecting self.strategy.
        How priority and strategy work together:
        - Step 1 (Priority Filter): Narrow down the candidate worker pool based
          on task priority level:
           * high   → all available workers are candidates (no restriction)
           * medium → exclude workers above 70% capacity utilization
           * low    → only workers below 50% capacity utilization
        - Step 2 (Strategy Selection): From the filtered candidate pool, apply
          self.strategy (round_robin / least_loaded / queue_based) via
          select_worker() to pick the final worker — exactly the same way a
          normal task would be routed.

        This ensures priority-aware routing stays consistent with the configured
        strategy instead of running a separate, disconnected selection logic.

        Args:
           priority: Task priority — "high", "medium", or "low" (case-insensitive)

        Returns:
           dict: Selected worker or None if no workers available
        """
        workers = self._get_valid_workers()

        if not workers:
            return None

        # Normalize priority to lowercase so "High"/"high"/"HIGH" all work
        priority = priority.lower()

        # ── Step 1: Filter candidate pool by priority ─────────────────────────
        if priority == "high":
            return min(workers, key=lambda w: w["active_tasks"])

        # For medium priority, select from least loaded
        if priority == "medium":
            # Select a worker that's not overloaded
            underutilized = [w for w in workers if w["active_tasks"] < w["capacity"] * 0.7]
            if underutilized:
                return min(underutilized, key=lambda w: w["active_tasks"])
            return min(workers, key=lambda w: w["active_tasks"])

        # For low priority, select any available
        return max(workers, key=lambda w: w["active_tasks"])  # Select the one with most load (fill it up)

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
        SYSTEM_UTILIZATION.set(stats["capacity_utilization"] / 100)
        available_workers = len(self._get_valid_workers())

        return {
            "strategy": self.strategy.value,
            "worker_stats": stats,
            "available_workers": available_workers,
            "system_overloaded": self.is_system_overloaded(),
            "timestamp": None,
        }
