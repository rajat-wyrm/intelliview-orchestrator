"""
Worker Registry
Tracks all available worker nodes and their status

Responsibilities:
- Register worker nodes
- Track worker capacity and active tasks
- Maintain worker health status
- Provide worker availability queries
- Real-time multi-instance sync via Redis Pub/Sub
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

# Import Prometheus worker monitoring metrics
from metrics.prometheus_metrics import (
    CURRENT_WORKERS,
    WORKER_ACTIVE_TASKS,
    WORKER_CAPACITY,
    WORKERS_HEALTHY,
    WORKERS_REGISTERED,
    WORKERS_UNHEALTHY,
)
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
    SYNC_CHANNEL = "worker_registry_sync"

    def __init__(self):
        """Initialize worker registry"""
        try:
            self.redis_client = self._create_redis_client()
            self.local_workers: dict[str, dict[str, Any]] = {}
            self.lock = Lock()
            self._hydrated = False
            self._hydrate_from_redis()

            # Keep a strong reference to background tasks to prevent garbage collection
            self.background_tasks: set[asyncio.Task[Any]] = set()

            # Start background listener for real-time synchronization
            if self.redis_client:
                try:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(self._start_pubsub_listener())
                    self.background_tasks.add(task)
                    task.add_done_callback(self.background_tasks.discard)
                    logger.info("Worker Registry initialized with Pub/Sub Sync")
                except RuntimeError:
                    # No running event loop (pytest/unit tests)
                    logger.debug(
                        "Skipping Pub/Sub listener because no event loop is running"
                    )
            else:
                logger.warning("Worker Registry initialized WITHOUT Redis connection")

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
                capacity = int(raw.get("capacity", 4))
                self.local_workers[wid] = {
                    "worker_id": wid,
                    "status": raw.get("status", "healthy"),
                    "active_tasks": int(raw.get("active_tasks", 0)),
                    "capacity": capacity,
                    "weight": int(raw.get("weight", capacity)),
                    "registered_at": raw.get("registered_at", ""),
                    "last_heartbeat": raw.get("last_heartbeat", ""),
                    "total_tasks_processed": int(raw.get("total_tasks_processed", 0)),
                    "failed_tasks": int(raw.get("failed_tasks", 0)),
                }
            self._hydrated = True
        except Exception as exc:
            logger.warning("Could not hydrate worker registry from Redis: %s", exc)

    def _trigger_sync_broadcast(self, worker_id: str, action: str = "update") -> None:
        """Publish a sync event to Redis Pub/Sub so other cluster instances
        can update their local worker registry."""
        if not self.redis_client:
            return
        try:
            message = json.dumps({"worker_id": worker_id, "action": action})
            self.redis_client.publish(self.SYNC_CHANNEL, message)
        except Exception as exc:
            logger.warning("Failed to broadcast sync event for %s: %s", worker_id, exc)

    async def _start_pubsub_listener(self) -> None:
        """Listen for sync events from other cluster instances and update
        the local worker registry accordingly."""
        if not self.redis_client:
            return
        try:
            pubsub = self.redis_client.raw.pubsub()
            await pubsub.subscribe(self.SYNC_CHANNEL)
            logger.info(
                "Worker Registry Pub/Sub listener started on %s", self.SYNC_CHANNEL
            )
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    wid = data.get("worker_id")
                    act = data.get("action")
                    if not wid:
                        continue
                    if act == "deregister":
                        with self.lock:
                            self.local_workers.pop(wid, None)
                    elif act == "update":
                        raw = self.redis_client.hgetall(
                            f"{self.WORKER_KEY_PREFIX}{wid}"
                        )
                        if raw:
                            with self.lock:
                                self.local_workers[wid] = {
                                    "worker_id": wid,
                                    "status": raw.get("status", "healthy"),
                                    "active_tasks": int(raw.get("active_tasks", 0)),
                                    "capacity": int(raw.get("capacity", 4)),
                                    "weight": int(raw.get("weight", 4)),
                                    "registered_at": raw.get("registered_at", ""),
                                    "last_heartbeat": raw.get("last_heartbeat", ""),
                                    "total_tasks_processed": int(
                                        raw.get("total_tasks_processed", 0)
                                    ),
                                    "failed_tasks": int(raw.get("failed_tasks", 0)),
                                    "failure_count": int(raw.get("failure_count", 0)),
                                    "penalty_weight": float(
                                        raw.get("penalty_weight", 1.0)
                                    ),
                                    "penalty_until": raw.get("penalty_until"),
                                }
                except Exception as exc:
                    logger.warning("Error processing sync event: %s", exc)
        except Exception as exc:
            logger.warning("Pub/Sub listener error: %s", exc)
        finally:
            try:
                await pubsub.unsubscribe(self.SYNC_CHANNEL)
                await pubsub.close()
            except Exception:
                pass

    def register_worker(
        self, worker_id: str, capacity: int = 4, weight: int | None = None
    ) -> bool:
        """
        Private helper to alert other cluster nodes to sync memory updates

        Args:
            worker_id: Unique worker identifier
            capacity: Maximum concurrent tasks this worker can handle
            weight: Scheduling weight for weighted round robin (defaults to capacity)

        Returns:
            bool: True if successful.
        """
        try:
            effective_weight = weight if weight is not None else capacity
            worker_data = {
                "worker_id": worker_id,
                "status": "healthy",
                "active_tasks": 0,
                "capacity": capacity,
                "weight": effective_weight,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "total_tasks_processed": 0,
                "failed_tasks": 0,
                # New fields
                "failure_count": 0,
                "penalty_weight": 1.0,
                "penalty_until": None,
            }

            with self.lock:
                self.local_workers[worker_id] = worker_data

            # Store in Redis
            if self.redis_client:
                key = f"{self.WORKER_KEY_PREFIX}{worker_id}"

                # hset expects native int/str values.
                # Store tags as a JSON string.
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
                            "failure_count",
                        }
                        else str(v)
                    )
                    for k, v in worker_data.items()
                }

                self.redis_client.hset(key, mapping=payload)
                self.redis_client.sadd(self.WORKER_SET_KEY, worker_id)
                self.redis_client.expire(
                    key,
                    int(timedelta(hours=24).total_seconds()),
                )

                # Broadcast modification to other running cluster instances
                self._trigger_sync_broadcast(worker_id)

            logger.info(f"Registered worker: {worker_id} with capacity {capacity}")

            # Update total registered workers metric
            WORKERS_REGISTERED.set(len(self.local_workers))

            # Update healthy worker count
            WORKERS_HEALTHY.set(
                sum(1 for w in self.local_workers.values() if w["status"] == "healthy")
            )

            # Update unhealthy worker count
            WORKERS_UNHEALTHY.set(
                sum(
                    1 for w in self.local_workers.values() if w["status"] == "unhealthy"
                )
            )

            # Store capacity allocated to this worker
            WORKER_CAPACITY.labels(worker_id=worker_id).set(capacity)

            # Initialize active task metric for the new worker
            WORKER_ACTIVE_TASKS.labels(worker_id=worker_id).set(0)

            logger.info(
                f"Registered worker: {worker_id} with capacity {capacity}, weight {effective_weight}"
            )
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
                self.local_workers[worker_id]["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

            # Update in Redis
            if self.redis_client:
                key = f"{self.WORKER_KEY_PREFIX}{worker_id}"
                self.redis_client.hset(key, "status", status)
                self.redis_client.hset(
                    key, "updated_at", datetime.now(timezone.utc).isoformat()
                )

                # Broadcast modification to other running cluster instances
                self._trigger_sync_broadcast(worker_id)

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
            has_changed = False
            with self.lock:
                if worker_id not in self.local_workers:
                    logger.warning(
                        f"Received heartbeat from unknown worker: {worker_id}"
                    )
                    return False

                old_worker = self.local_workers.get(worker_id)
                if old_worker:
                    if (
                        old_worker.get("active_tasks") != active_tasks
                        or old_worker.get("status") != "healthy"
                    ):
                        has_changed = True
                else:
                    has_changed = True

                self.local_workers[worker_id]["active_tasks"] = active_tasks
                self.local_workers[worker_id]["last_heartbeat"] = datetime.now(
                    timezone.utc
                ).isoformat()
                self.local_workers[worker_id]["status"] = "healthy"

            # Update in Redis
            if self.redis_client:
                key = f"{self.WORKER_KEY_PREFIX}{worker_id}"
                self.redis_client.hset(key, "active_tasks", active_tasks)
                self.redis_client.hset(
                    key, "last_heartbeat", datetime.now(timezone.utc).isoformat()
                )
                self.redis_client.hset(key, "status", "healthy")

                # Also store heartbeat timestamp
                hb_key = f"{self.WORKER_HEARTBEAT_KEY}{worker_id}"
                self.redis_client.set(hb_key, "ok", ex=self.HEARTBEAT_TIMEOUT)

                if has_changed:
                    self._trigger_sync_broadcast(worker_id)

            logger.debug(f"Heartbeat from {worker_id}: {active_tasks} active tasks")

            # Update worker active task count from heartbeat
            WORKER_ACTIVE_TASKS.labels(worker_id=worker_id).set(active_tasks)

            # Refresh healthy worker metric after heartbeat
            WORKERS_HEALTHY.set(
                sum(1 for w in self.local_workers.values() if w["status"] == "healthy")
            )

            # Refresh unhealthy worker metric after heartbeat
            WORKERS_UNHEALTHY.set(
                sum(
                    1 for w in self.local_workers.values() if w["status"] == "unhealthy"
                )
            )

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

                # Broadcast modification to other running cluster instances
                self._trigger_sync_broadcast(worker_id)

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

                # Broadcast modification to other running cluster instances
                self._trigger_sync_broadcast(worker_id)

            return True
        except Exception as e:
            logger.error(f"Error decrementing active tasks: {e!s}")
            return False

    def record_success(self, worker_id: str) -> None:
        """
        Reset penalty after successful execution.
        """
        with self.lock:
            worker = self.local_workers.get(worker_id)
            if not worker:
                return

            worker["failure_count"] = 0
            worker["penalty_weight"] = 1.0
            worker["penalty_until"] = None

        if self.redis_client:
            key = f"{self.WORKER_KEY_PREFIX}{worker_id}"
            self.redis_client.hset(
                key,
                mapping={
                    "failure_count": 0,
                    "penalty_weight": 1.0,
                    "penalty_until": "",
                },
            )

    def get_worker_weight(self, worker: dict[str, Any]) -> float:
        """
        Return effective scheduling weight.
        Penalized workers receive a lower weight.
        """
        penalty_until = worker.get("penalty_until")

        if penalty_until:
            try:
                expiry = datetime.fromisoformat(penalty_until)

                if expiry > datetime.now(timezone.utc):
                    return worker["penalty_weight"]

                # Penalty expired
                worker["penalty_weight"] = 1.0
                worker["penalty_until"] = None

            except Exception:
                pass

        return 1.0

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
        from orchestrator.time_utils import utcnow
        from datetime import datetime, timezone, timedelta
        
        timeout_threshold = utcnow() - timedelta(seconds=self.HEARTBEAT_TIMEOUT)
        
        with self.lock:
            for worker in self.local_workers.values():
                last_hb_raw = worker.get("last_heartbeat")
                if not last_hb_raw:
                    continue
                last_hb = datetime.fromisoformat(last_hb_raw)
                if last_hb.tzinfo is None:
                    last_hb = last_hb.replace(tzinfo=timezone.utc)
                    
                if (
                    last_hb >= timeout_threshold
                    and worker["active_tasks"] < worker["capacity"]
                ):
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
            healthy_workers = sum(
                1 for w in self.local_workers.values() if w["status"] == "healthy"
            )
            total_capacity = sum(w["capacity"] for w in self.local_workers.values())
            total_active_tasks = sum(
                w["active_tasks"] for w in self.local_workers.values()
            )
            total_processed = sum(
                w.get("total_tasks_processed", 0) for w in self.local_workers.values()
            )
            idle_workers = sum(
                1 for w in self.local_workers.values() if w["active_tasks"] == 0
            )
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
                    "failure_count": w.get("failure_count", 0),
                    "penalty_weight": w.get("penalty_weight", 1.0),
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
                    (
                        (total_active_tasks / total_capacity * 100)
                        if total_capacity > 0
                        else 0
                    ),
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

        # Broadcast if status changes to unhealthy
        for wid in unhealthy:
            self._trigger_sync_broadcast(wid)

        return unhealthy

    def record_worker_failure(self, worker_id: str):
        worker = self.local_workers.get(worker_id)

        if not worker:
            return None

        worker["failure_count"] += 1

        if worker["failure_count"] >= 3:
            worker["penalty_weight"] = 0.5
            worker["penalty_until"] = (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ).isoformat()

    def clear_penalty(self, worker_id: str):
        worker = self.local_workers.get(worker_id)

        if not worker:
            return

        worker["failure_count"] = 0
        worker["penalty_weight"] = 1.0
        worker["penalty_until"] = None

    def record_failure(self, worker_id: str):
        worker = self.local_workers.get(worker_id)
        if not worker:
            return

        worker["failure_count"] += 1

        if worker["failure_count"] >= 3:
            worker["penalty_weight"] = 0.5

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

                # Broadcast deregistration action
                self._trigger_sync_broadcast(worker_id, action="deregister")

            logger.info(f"Deregistered worker: {worker_id}")

            # Update Prometheus metrics
            WORKERS_REGISTERED.set(len(self.local_workers))
            CURRENT_WORKERS.set(len(self.local_workers))

            WORKERS_HEALTHY.set(
                sum(1 for w in self.local_workers.values() if w["status"] == "healthy")
            )

            WORKERS_UNHEALTHY.set(
                sum(
                    1 for w in self.local_workers.values() if w["status"] == "unhealthy"
                )
            )

            return True
        except Exception as e:
            logger.error(f"Error deregistering worker: {e!s}")
            return False
