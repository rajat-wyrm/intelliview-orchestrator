"""
Load Balancer
Implements intelligent task distribution strategies across worker nodes

Strategies:
1. Round Robin - Distribute tasks evenly in sequence
2. Least Loaded - Assign to worker with fewest active tasks (recommended)
3. Queue-based - Fallback to Redis queue if no workers available
4. Weighted Round Robin - Smooth weighted distribution proportional to worker weights
"""

import logging
import time
from enum import Enum
from threading import Lock
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
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"


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

        # Smooth Weighted Round Robin state — tracks the running
        # ``current_weight`` for each worker across scheduling calls.
        # Protected by its own lock so the registry lock is not held
        # during weight arithmetic.
        self._wrr_current_weights: dict[str, int] = {}
        self._wrr_lock = Lock()

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
        if self.strategy == BalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._select_weighted_round_robin()
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
        available = self._get_cached_workers()

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
        old_strategy = self.strategy
        self.strategy = strategy

        # Reset SWRR state when switching away so a later switch back
        # starts from a clean slate.
        if old_strategy == BalancingStrategy.WEIGHTED_ROUND_ROBIN:
            with self._wrr_lock:
                self._wrr_current_weights.clear()

        logger.info(f"Switched to {strategy.value} strategy")

    def _select_weighted_round_robin(self) -> dict[str, Any] | None:
        """
        Smooth Weighted Round Robin Strategy (Nginx algorithm)

        For every scheduling request:
        1. Increase current_weight of every available worker by its configured weight.
        2. Select the worker with the highest current_weight.
        3. Reduce the selected worker's current_weight by the total weight.
        4. Return the selected worker.

        Produces a smooth, interleaved distribution proportional to worker weights.
        For weights {A:5, B:1, C:1}, the 7-call sequence is: A A B A C A A
        (not A A A A A B C).

        Thread-safe: uses ``_wrr_lock`` to protect ``_wrr_current_weights``.

        Returns:
            dict: Selected worker or None if no workers available
        """
        available = self.worker_registry.get_available_workers()

        if not available:
            logger.warning("No workers available for Weighted Round Robin selection")
            return None

        with self._wrr_lock:
            # Prune stale entries for workers that are no longer available
            available_ids = {w["worker_id"] for w in available}
            stale_ids = set(self._wrr_current_weights.keys()) - available_ids
            for sid in stale_ids:
                del self._wrr_current_weights[sid]

            # Step 1: increase current_weight by configured weight
            for w in available:
                wid = w["worker_id"]
                configured_weight = w.get("weight", w["capacity"])
                self._wrr_current_weights[wid] = (
                    self._wrr_current_weights.get(wid, 0) + configured_weight
                )

            # Step 2: select worker with the highest current_weight
            best = max(available, key=lambda w: self._wrr_current_weights[w["worker_id"]])

            # Step 3: reduce selected worker's current_weight by total weight
            total_weight = sum(w.get("weight", w["capacity"]) for w in available)
            self._wrr_current_weights[best["worker_id"]] -= total_weight

        logger.debug(
            f"Weighted Round Robin selected worker: {best['worker_id']} "
            f"(weight: {best.get('weight', best['capacity'])})"
        )
        return best

    def get_best_worker_for_priority(self, priority: str) -> dict[str, Any] | None:
        """
        Return cached workers if cache is still valid.
        """
        current_time = time.time()

        if self._worker_cache is None or current_time - self._cache_timestamp > self._cache_ttl:
            self._registry_lookup_count += 1

            logger.debug(f"Refreshing worker cache (Registry Lookup #{self._registry_lookup_count})")
            self._worker_cache = self.worker_registry.get_available_workers()
            self._cache_timestamp = current_time

        return self._worker_cache

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
        available = self._get_cached_workers()

if not available:
    return None

available.sort(
    key=lambda w: (
        w["active_tasks"] /
        self.worker_registry.get_worker_weight(w)
    )
)


        # Normalize priority to lowercase so "High"/"high"/"HIGH" all work
        priority = priority.lower()

        # ── Step 1: Filter candidate pool by priority ─────────────────────────
        if priority == "high":
        return available[0]

        # For medium priority, select from least loaded
        if priority == "medium":
            # Select a worker that's not overloaded
            underutilized = [w for w in available if w["active_tasks"] < w["capacity"] * 0.7]
            if underutilized:
                return underutilized[0]
            return available[0]

        # For low priority, select any available
        return available[-1]  # Select the one with most load (fill it up)

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
        available_workers = len(self._get_cached_workers())

        return {
            "strategy": self.strategy.value,
            "worker_stats": stats,
            "available_workers": available_workers,
            "registry_lookups": self._registry_lookup_count,
            "system_overloaded": self.is_system_overloaded(),
            "timestamp": None,
        }
