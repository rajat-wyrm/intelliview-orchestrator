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
                return underutilized[0]
            return available[0]

        # For low priority, select any available
        return available[-1]  # Select the one with most load (fill it up)

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
        SYSTEM_UTILIZATION.set(stats["capacity_utilization"] / 100)
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
