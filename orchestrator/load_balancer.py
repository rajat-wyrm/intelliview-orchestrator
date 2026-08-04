"""
Load Balancer
Implements intelligent task distribution strategies across worker nodes
 
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
 
    def __init__(self, strategy: BalancingStrategy = BalancingStrategy.LEAST_LOADED):
        """
        Initialize load balancer
 
        Args:
            strategy: Load balancing strategy to use
        """
        self.worker_registry = WorkerRegistry()
        self.strategy = strategy
        self.session_affinity_enabled = True
        self.round_robin_index = 0
        self.redis_client = get_redis_client()
        self._lock = threading.Lock()
        self.round_robin_lock = threading.Lock()
        logger.info(f"Load Balancer initialized with strategy: {strategy.value}")
 
    def select_worker(
        self,
        task: dict[str, Any] | None = None,
        required_tag: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Select a worker for task execution based on current strategy
 
        Args:
            task: Task payload dict (required for queue-based fallback)
            required_tag: Optional capability tag (e.g. "gpu", "video") the
                task needs. When provided, only workers advertising this
                tag are considered. When None, all workers are eligible,
                same as before this option existed.
 
        Returns:
            dict: Selected worker details or None if no matching worker
            is available (including the case where required_tag was
            given but no worker currently has it).
        """
        with self._lock:
            if self.strategy == BalancingStrategy.ROUND_ROBIN:
                return self._select_round_robin(required_tag=required_tag)
            if self.strategy == BalancingStrategy.LEAST_LOADED:
                return self._select_least_loaded(required_tag=required_tag)
            if self.strategy == BalancingStrategy.QUEUE_BASED:
                return self._select_queue_based(task=task, required_tag=required_tag)
            # Default to least loaded
            return self._select_least_loaded(required_tag=required_tag)
 
    def select_worker_with_affinity(
        self,
        preferred_worker_id: str | None = None,
        required_tag: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Select a worker using session affinity.
 
        If the preferred worker is healthy, has available capacity, and
        (when required_tag is set) has that tag, use it. Otherwise, fall
        back to the configured load balancing strategy.
        """
        if self.session_affinity_enabled and preferred_worker_id:
            worker = self.worker_registry.get_worker(preferred_worker_id)
 
            if (
                worker
                and worker["status"] == "healthy"
                and worker["active_tasks"] < worker["capacity"]
                and (required_tag is None or required_tag in worker.get("tags", []))
            ):
                logger.debug(
                    "Session affinity selected worker %s",
                    preferred_worker_id,
                )
                return worker
 
        return self.select_worker(required_tag=required_tag)
 
    def _select_round_robin(self, required_tag: str | None = None) -> dict[str, Any] | None:
        """
        Round Robin Strategy: Distribute tasks evenly in sequence
 
        Cycles through available workers in order, regardless of current load.
        When required_tag is given, only cycles through workers that have it.
 
        Returns:
            dict: Next worker in rotation or None if no matching workers available
        """
        available = self.worker_registry.get_available_workers(required_tag=required_tag)
 
        if not available:
            logger.warning(
                "No workers available for Round Robin selection (required_tag=%s)",
                required_tag,
            )
            return None
 
        with self.round_robin_lock:
            worker = available[self.round_robin_index % len(available)]
            self.round_robin_index += 1
 
        logger.debug(f"Round Robin selected worker: {worker['worker_id']}")
        return worker
 
    def _select_least_loaded(self, required_tag: str | None = None) -> dict[str, Any] | None:
        """
        Least Loaded Strategy: Assign to worker with fewest active tasks (RECOMMENDED)
 
        Selects the worker with the lowest number of active tasks among
        available (and, if required_tag is given, tag-matching) workers.
        Provides better load balancing for varying task durations.
 
        Returns:
            dict: Least loaded matching worker or None if none available
        """
        worker = self.worker_registry.get_least_loaded_worker(required_tag=required_tag)
 
        if not worker:
            logger.warning(
                "No workers available for Least Loaded selection (required_tag=%s)",
                required_tag,
            )
            return None
 
        logger.debug(
            f"Least Loaded selected worker: {worker['worker_id']} "
            f"(active: {worker['active_tasks']}/{worker['capacity']})"
        )
        return worker
 
    def _select_queue_based(
        self,
        task: dict[str, Any] | None = None,
        required_tag: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Queue-based Strategy: Fallback to Redis queue if no workers available
 
        First tries to select a (tag-matching, if required_tag is given)
        worker. If none available and a task is provided, enqueues the
        task in Redis for later processing.
 
        Args:
            task: Task payload dict to be enqueued if worker is unavailable
            required_tag: Optional capability tag the task needs
 
        Returns:
            dict: Selected worker or None to trigger queueing
        """
        worker = self.worker_registry.get_least_loaded_worker(required_tag=required_tag)
 
        if not worker:
            logger.debug("No workers available - fallback to Redis queue")
            if task:
                try:
                    serialized_task = json.dumps(task)
                    self.redis_client.rpush("task_queue", serialized_task)
                    logger.info("Task successfully enqueued into Redis queue")
                except Exception as e:
                    logger.error(f"Failed to push task to Redis queue: {e}")
            return None
 
        logger.debug(f"Queue-based selected worker: {worker['worker_id']}")
        return worker
 
    def switch_strategy(self, strategy: BalancingStrategy) -> None:
        """
        Switch to a different load balancing strategy
 
        Args:
            strategy: New strategy to use
        """
        with self._lock:
            self.strategy = strategy
        logger.info(f"Switched to {strategy.value} strategy")
 
    def get_best_worker_for_priority(
        self, priority: str, required_tag: str | None = None
    ) -> dict[str, Any] | None:
        """
        Select worker considering task priority
 
        Args:
            priority: Task priority ("low", "medium", "high")
            required_tag: Optional capability tag the task needs
 
        Returns:
            dict: Selected worker or None
        """
        available = self.worker_registry.get_available_workers(required_tag=required_tag)
 
        if not available:
            return None
 
        # For high priority, select least loaded
        if priority == "high":
            return min(available, key=lambda w: w["active_tasks"])
 
        # For medium priority, select from least loaded
        if priority == "medium":
            underutilized = [w for w in available if w["active_tasks"] < w["capacity"] * 0.7]
            if underutilized:
                return underutilized[0]
            return available[0]
 
        # For low priority, select any available
        return available[-1]
 
    def is_system_overloaded(self, threshold: float = 0.9) -> bool:
        """
        Check if system is overloaded
 
        Args:
            threshold: Utilization threshold (0-1)
 
        Returns:
            bool: True if system utilization exceeds threshold
        """
        stats = self.worker_registry.get_worker_statistics()
        utilization = stats["capacity_utilization"] / 100
 
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
 