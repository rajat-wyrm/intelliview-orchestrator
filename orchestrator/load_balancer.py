"""

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
        self.round_robin_lock = threading.Lock()
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

        Thread-safe: uses a lock around the read-and-increment of round_robin_index
        so concurrent calls cannot read the same index value before it is updated.

        Returns:
            dict: Next worker in rotation or None if no workers available
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
        with self._lock:
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
        available = self.worker_registry.get_available_workers()

        if not available:
            logger.warning("No workers available for priority-based selection")
            return None

        # Normalize priority to lowercase so "High"/"high"/"HIGH" all work
        priority = priority.lower()

        # ── Step 1: Filter candidate pool by priority ─────────────────────────
        if priority == "high":
            # High priority: all workers are candidates — no filtering
            candidates = available

        elif priority == "medium":
            # Medium priority: skip workers above 70% capacity
            candidates = [w for w in available if w["active_tasks"] < w["capacity"] * 0.7]
            # Fallback: if all workers are busy, consider everyone
            if not candidates:
                logger.debug("Medium priority fallback: all workers above 70% — using full pool")
                candidates = available

        else:
            # Low priority: only workers below 50% capacity (spare capacity)
            candidates = [w for w in available if w["active_tasks"] < w["capacity"] * 0.5]
            # Fallback: if no spare-capacity worker found, use least loaded one
            if not candidates:
                logger.debug("Low priority fallback: no spare-capacity workers — using least loaded")
                candidates = [min(available, key=lambda w: w["active_tasks"])]

        # ── Step 2: Apply configured strategy on the filtered pool ────────────
        # Temporarily swap the registry's worker pool so select_worker() picks
        # only from our filtered candidates, then restore it afterward.
        original_get = self.worker_registry.get_available_workers

        self.worker_registry.get_available_workers = lambda: candidates
        try:
            selected = self.select_worker()
        finally:
            # Always restore original method — even if select_worker() raises
            self.worker_registry.get_available_workers = original_get

        logger.debug(
            f"Priority '{priority}' + strategy '{self.strategy.value}' "
            f"→ selected worker: {selected['worker_id'] if selected else None}"
        )
        return selected
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
