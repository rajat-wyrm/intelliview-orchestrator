"""
Worker Registry
Tracks all available worker nodes and their status

Responsibilities:
- Register worker nodes
- Track worker capacity and active tasks
- Maintain worker health status
- Provide worker availability queries
"""

import logging
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from orchestrator.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class WorkerRegistry:
    """
    Centralized registry for tracking worker nodes in the system
    """

    # Redis key patterns
    WORKER_KEY_PREFIX = "worker:"
    WORKER_SET_KEY = "workers:all"
    WORKER_HEARTBEAT_KEY = "worker:heartbeat:"
    HEARTBEAT_TIMEOUT = 60  # seconds

    def __init__(self):
        """Initialize worker registry"""
        try:
            self.redis_client = self._create_redis_client()
            self.local_workers: dict[str, dict[str, Any]] = {}
            self.lock = Lock()
            self._hydrated = False
            self._hydrate_from_redis()
            logger.info("Worker Registry initialized")
        except Exception as e:
            logger.error(f"Error initializing Worker Registry: {e!s}")
            self.redis_client = None

    def _create_redis_client(self) -> Any:
        """Create the shared Redis client used by the orchestrator."""
        return get_redis_client()

    def _hydrate_from_redis(self) -> None:
        """Populate `local_workers` from Redis on first use so workers
        registered in another process (worker agent / seed script) are
        visible to this FastAPI process."""
        if self._hydrated or not self.redis_client:
            return
        try:
            worker_ids = self.redis_client.smembers(self.WORKER_SET_KEY) or set()
            for wid in worker_ids:
                raw = self.redis_client.hgetall(f"{self.WORKER_KEY_PREFIX}{wid}")
                if not raw:
                    continue
                self.local_workers[wid] = {
                    "worker_id": wid,
                    "status": raw.get("status", "healthy"),
                    "active_tasks": int(raw.get("active_tasks", 0)),
                    "capacity": int(raw.get("capacity", 4)),
                    "registered_at": raw.get("registered_at", ""),
                    "last_heartbeat": raw.get("last_heartbeat", ""),
                    "total_tasks_processed": int(raw.get("total_tasks_processed", 0)),
                    "failed_tasks": int(raw.get("failed_tasks", 0)),
                }
            self._hydrated = True
        except Exception as exc:
            logger.warning("Could not hydrate worker registry from Redis: %s", exc)

    def register_worker(self, worker_id: str, capacity: int = 4) -> bool:
        """
        Register a new worker node

        Args:
            worker_id: Unique worker identifier
            capacity: Maximum concurrent tasks this worker can handle

        Returns:
            bool: True if successful
        """
        try:
            worker_data = {
                "worker_id": worker_id,
                "status": "healthy",
                "active_tasks": 0,
                "capacity": capacity,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "total_tasks_processed": 0,
                "failed_tasks": 0,
            }

            with self.lock:
                self.local_workers[worker_id] = worker_data

            # Store in Redis
            if self.redis_client:
                key = f"{self.WORKER_KEY_PREFIX}{worker_id}"
                # hset expects native int/bool/str values; coerce ints explicitly.
                payload = {
                    k: (
                        int(v)
                        if isinstance(v, (int, float))
                        and k
                        in {
                            "capacity",
                            "active_tasks",
                            "total_tasks_processed",
                            "failed_tasks",
                        }
                        else str(v)
                    )
                    for k, v in worker_data.items()
                }
                self.redis_client.hset(key, mapping=payload)
                self.redis_client.sadd(self.WORKER_SET_KEY, worker_id)
                self.redis_client.expire(key, int(timedelta(hours=24).total_seconds()))

            logger.info(f"Registered worker: {worker_id} with capacity {capacity}")
            return True

        except Exception as e:
            logger.error(f"Error registering worker: {e!s}")
            return False

    def update_worker_status(self, worker_id: str, status: str) -> bool:
        """
        Update worker health status

        Args:
            worker_id: Worker identifier
            status: Status ("healthy", "degraded", "unhealthy")

        Returns:
            bool: True if successful
        """
        try:
            with self.lock:
                if worker_id not in self.local_workers:
                    logger.warning(f"Worker {worker_id} not found in registry")
                    return False

                self.local_workers[worker_id]["status"] = status
                self.local_workers[worker_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Update in Redis
            if self.redis_client:
                key = f"{self.WORKER_KEY_PREFIX}{worker_id}"
                self.redis_client.hset(key, "status", status)
                self.redis_client.hset(key, "updated_at", datetime.now(timezone.utc).isoformat())

            logger.info(f"Updated worker {worker_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Error updating worker status: {e!s}")
            return False

    def heartbeat(self, worker_id: str, active_tasks: int) -> bool:
        """
        Process worker heartbeat signal

        Args:
            worker_id: Worker identifier
            active_tasks: Current number of active tasks on worker

        Returns:
            bool: True if successful
        """
        try:
            with self.lock:
                if worker_id not in self.local_workers:
                    logger.warning(f"Received heartbeat from unknown worker: {worker_id}")
                    return False

                self.local_workers[worker_id]["active_tasks"] = active_tasks
                self.local_workers[worker_id]["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
                self.local_workers[worker_id]["status"] = "healthy"

            # Update in Redis
            if self.redis_client:
                key = f"{self.WORKER_KEY_PREFIX}{worker_id}"
                self.redis_client.hset(key, "active_tasks", active_tasks)
                self.redis_client.hset(key, "last_heartbeat", datetime.now(timezone.utc).isoformat())
                self.redis_client.hset(key, "status", "healthy")

                # Also store heartbeat timestamp
                hb_key = f"{self.WORKER_HEARTBEAT_KEY}{worker_id}"
                self.redis_client.set(hb_key, "ok", ex=self.HEARTBEAT_TIMEOUT)

            logger.debug(f"Heartbeat from {worker_id}: {active_tasks} active tasks")
            return True

        except Exception as e:
            logger.error(f"Error processing heartbeat: {e!s}")
            return False

    def increment_active_tasks(self, worker_id: str) -> bool:
        """Increment active task count for a worker"""
        try:
            with self.lock:
                if worker_id not in self.local_workers:
                    return False
                self.local_workers[worker_id]["active_tasks"] += 1

            if self.redis_client:
                key = f"{self.WORKER_KEY_PREFIX}{worker_id}"
                self.redis_client.hincrby(key, "active_tasks", 1)

            return True
        except Exception as e:
            logger.error(f"Error incrementing active tasks: {e!s}")
            return False

    def decrement_active_tasks(self, worker_id: str) -> bool:
        """Decrement active task count for a worker"""
        try:
            with self.lock:
                if worker_id not in self.local_workers:
                    return False
                current = self.local_workers[worker_id]["active_tasks"]
                self.local_workers[worker_id]["active_tasks"] = max(0, current - 1)
                self.local_workers[worker_id]["total_tasks_processed"] += 1

            if self.redis_client:
                key = f"{self.WORKER_KEY_PREFIX}{worker_id}"
                self.redis_client.hincrby(key, "active_tasks", -1)
                self.redis_client.hincrby(key, "total_tasks_processed", 1)

            return True
        except Exception as e:
            logger.error(f"Error decrementing active tasks: {e!s}")
            return False

    def get_worker(self, worker_id: str) -> dict[str, Any] | None:
        """Get worker details"""
        with self.lock:
            return self.local_workers.get(worker_id)

    def get_all_workers(self) -> dict[str, dict[str, Any]]:
        """Get all registered workers"""
        with self.lock:
            return dict(self.local_workers)

    def get_available_workers(self) -> list[dict[str, Any]]:
        """
        Get workers that are healthy and have capacity

        Returns:
            list: Available worker details
        """
        available = []
        with self.lock:
            for worker in self.local_workers.values():
                if worker["status"] == "healthy" and worker["active_tasks"] < worker["capacity"]:
                    available.append(worker)

        return available

    def get_least_loaded_worker(self) -> dict[str, Any] | None:
        """
        Get the worker with the lowest active task count

        Returns:
            dict: Least loaded worker or None if none available
        """
        available = self.get_available_workers()
        if not available:
            return None

        # Sort by active_tasks and return the one with fewest
        return min(available, key=lambda w: w["active_tasks"])

    def get_worker_statistics(self) -> dict[str, Any]:
        """Get overall worker registry statistics"""
        with self.lock:
            total_workers = len(self.local_workers)
            healthy_workers = sum(1 for w in self.local_workers.values() if w["status"] == "healthy")
            total_capacity = sum(w["capacity"] for w in self.local_workers.values())
            total_active_tasks = sum(w["active_tasks"] for w in self.local_workers.values())
            total_processed = sum(w.get("total_tasks_processed", 0) for w in self.local_workers.values())
            idle_workers = sum(1 for w in self.local_workers.values() if w["active_tasks"] == 0)
            active_loads = [w["active_tasks"] for w in self.local_workers.values()]
            avg_active = (total_active_tasks / total_workers) if total_workers else 0

            worker_details = [
                {
                    "worker_id": wid,
                    "capacity": w["capacity"],
                    "active_tasks": w["active_tasks"],
                    "status": w["status"],
                    "last_heartbeat": w.get("last_heartbeat"),
                    "total_tasks_processed": w.get("total_tasks_processed", 0),
                    "failed_tasks": w.get("failed_tasks", 0),
                }
                for wid, w in self.local_workers.items()
            ]

            return {
                "total_workers": total_workers,
                "healthy_workers": healthy_workers,
                "unhealthy_workers": total_workers - healthy_workers,
                "total_capacity": total_capacity,
                "total_active_tasks": total_active_tasks,
                "capacity_utilization": round(
                    (total_active_tasks / total_capacity * 100) if total_capacity > 0 else 0,
                    2,
                ),
                "total_tasks_processed": total_processed,
                "average_active_tasks": round(avg_active, 2),
                "min_active_tasks": min(active_loads) if active_loads else 0,
                "max_active_tasks": max(active_loads) if active_loads else 0,
                "idle_workers": idle_workers,
                "workers": worker_details,
            }

    def detect_unhealthy_workers(self) -> list[str]:
        """
        Detect workers that haven't sent heartbeat recently

        Returns:
            list: List of unhealthy worker IDs
        """
        from orchestrator.time_utils import utcnow

        unhealthy: list[str] = []
        timeout_threshold = utcnow() - timedelta(seconds=self.HEARTBEAT_TIMEOUT)

        with self.lock:
            for worker_id, worker in self.local_workers.items():
                last_hb_raw = worker.get("last_heartbeat")
                if not last_hb_raw:
                    continue
                last_hb = datetime.fromisoformat(last_hb_raw)
                if last_hb.tzinfo is None:
                    last_hb = last_hb.replace(tzinfo=timezone.utc)
                if last_hb < timeout_threshold:
                    unhealthy.append(worker_id)
                    worker["status"] = "unhealthy"

        return unhealthy

    def deregister_worker(self, worker_id: str) -> bool:
        """Remove a worker from the registry"""
        try:
            with self.lock:
                if worker_id in self.local_workers:
                    del self.local_workers[worker_id]

            if self.redis_client:
                key = f"{self.WORKER_KEY_PREFIX}{worker_id}"
                self.redis_client.delete(key)
                self.redis_client.srem(self.WORKER_SET_KEY, worker_id)

            logger.info(f"Deregistered worker: {worker_id}")
            return True
        except Exception as e:
            logger.error(f"Error deregistering worker: {e!s}")
            return False
