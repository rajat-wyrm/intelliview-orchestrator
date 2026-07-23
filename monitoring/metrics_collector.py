"""
Metrics Collector Module

Collects and aggregates system metrics for monitoring and observability.

Responsibilities:
- Track active, completed, failed sessions
- Collect worker statistics
- Monitor queue depth and processing rate
- Track retry counts and failure patterns
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from orchestrator.cache_manager import CacheManager

logger = logging.getLogger(__name__)

_METRICS_TTL_SECONDS = 1.0


class _TTLCache:
    """Tiny TTL cache: `(value, expires_at)` per key. No eviction, single
    process — fine for the small fixed set of metric keys we use."""

    __slots__ = ("_store",)

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: float = _METRICS_TTL_SECONDS) -> None:
        self._store[key] = (time.monotonic() + ttl, value)


class MetricsCollector:
    """
    Collects and aggregates system metrics for the monitoring dashboard.

    Tracks:
    - Session lifecycle metrics (active, completed, failed)
    - Worker performance and health
    - Queue depth and processing rates
    - Failure and retry patterns
    """

    def __init__(self):
        """
        Initialize MetricsCollector
        """
        self.redis_client = CacheManager()
        self.metrics_prefix = "metrics:"
        self._system_cache = _TTLCache()
        logger.info("MetricsCollector initialized")

    def get_system_metrics(self) -> dict[str, Any]:
        """
        Get comprehensive system-wide metrics

        Returns:
            Dict with system-wide metrics
        """
        cached = self._system_cache.get("metrics")
        if cached is not None:
            return cached
        try:
            session_metrics = self._get_session_metrics()
            worker_metrics = self._get_worker_metrics()
            queue_metrics = self._get_queue_metrics()

            # Determine system health
            health_status = "healthy"
            if session_metrics.get("failed_count", 0) > session_metrics.get("completed_count", 0) * 0.1:
                health_status = "degraded"

            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_health": health_status,
                "session_metrics": session_metrics,
                "worker_metrics": worker_metrics,
                "queue_metrics": queue_metrics,
                "uptime_seconds": self._get_uptime(),
            }
            self._system_cache.set("metrics", payload)
            return payload
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e!s}")
            return {}

    def _get_session_metrics(self) -> dict[str, Any]:
        """Get session-related metrics"""
        try:
            if not self.redis_client:
                return {}

            # Count sessions in each state
            active_count = 0
            completed_count = 0
            failed_count = 0

            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match="session:*", count=100)

                for key in keys:
                    try:
                        session_data = self.redis_client.get(key)
                        if session_data:
                            session = json.loads(session_data)
                            status = session.get("status", "unknown")

                            if status == "PROCESSING":
                                active_count += 1
                            elif status == "COMPLETED":
                                completed_count += 1
                            elif status == "FAILED":
                                failed_count += 1
                    except Exception:
                        continue

                if cursor == 0:
                    break

            total = active_count + completed_count + failed_count

            return {
                "active": active_count,
                "completed": completed_count,
                "failed": failed_count,
                "total": total,
                "completion_rate": (completed_count / (total - active_count) * 100)
                if (total - active_count) > 0
                else 0,
                "failure_rate": (failed_count / (total - active_count) * 100)
                if (total - active_count) > 0
                else 0,
            }

        except Exception as e:
            logger.error(f"Error getting session metrics: {e!s}")
            return {}

    def _get_worker_metrics(self) -> dict[str, Any]:
        """Get worker-related metrics"""
        try:
            if not self.redis_client:
                return {}

            total_workers = 0
            healthy_workers = 0
            total_capacity = 0
            active_tasks = 0

            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match="worker:*", count=100)

                for key in keys:
                    try:
                        worker_data = self.redis_client.get(key)
                        if worker_data:
                            worker = json.loads(worker_data)
                            total_workers += 1

                            if worker.get("health_status") == "healthy":
                                healthy_workers += 1

                            total_capacity += worker.get("capacity", 0)
                            active_tasks += worker.get("active_tasks", 0)
                    except Exception:
                        continue

                if cursor == 0:
                    break

            utilization = (active_tasks / total_capacity * 100) if total_capacity > 0 else 0

            return {
                "total_workers": total_workers,
                "healthy_workers": healthy_workers,
                "unhealthy_workers": total_workers - healthy_workers,
                "total_capacity": total_capacity,
                "active_tasks": active_tasks,
                "available_slots": total_capacity - active_tasks,
                "utilization_percent": round(utilization, 2),
                "health_percent": (healthy_workers / total_workers * 100) if total_workers > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Error getting worker metrics: {e!s}")
            return {}

    def _get_queue_metrics(self) -> dict[str, Any]:
        """Get queue-related metrics"""
        try:
            if not self.redis_client:
                return {}

            queue_length = self.redis_client.llen("celery_queue") if self.redis_client else 0

            return {
                "queue_length": queue_length,
                "pending_tasks": queue_length,
                "threshold": 1000,
                "backlog_percent": (queue_length / 1000 * 100) if queue_length > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Error getting queue metrics: {e!s}")
            return {}

    def get_worker_metrics(self, worker_registry) -> dict[str, Any]:
        """
        Get detailed worker performance metrics

        Args:
            worker_registry: WorkerRegistry instance

        Returns:
            Dict with worker metrics
        """
        try:
            all_workers = worker_registry.get_all_workers()

            workers_list = []
            for worker_id, worker_data in all_workers.items():
                workers_list.append(
                    {
                        "worker_id": worker_id,
                        "capacity": worker_data.get("capacity", 0),
                        "active_tasks": worker_data.get("active_tasks", 0),
                        "available": worker_data.get("capacity", 0) - worker_data.get("active_tasks", 0),
                        "utilization": (
                            worker_data.get("active_tasks", 0) / worker_data.get("capacity", 1) * 100
                        ),
                        "last_heartbeat": worker_data.get("last_heartbeat"),
                        "joined_at": worker_data.get("joined_at"),
                    }
                )

            return {
                "total_workers": len(workers_list),
                "workers": workers_list,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting worker metrics: {e!s}")
            return {}

    def get_session_metrics(self, session_tracker) -> dict[str, Any]:
        """
        Get detailed session activity metrics

        Args:
            session_tracker: SessionTracker instance

        Returns:
            Dict with session metrics
        """
        try:
            session_stats = session_tracker.get_session_statistics()

            return {
                "active_sessions": session_stats.get("active_count", 0),
                "completed_sessions": session_stats.get("completed_count", 0),
                "failed_sessions": session_stats.get("failed_count", 0),
                "avg_processing_time": session_stats.get("avg_processing_time", 0),
                "min_risk_score": session_stats.get("min_risk_score", 0),
                "max_risk_score": session_stats.get("max_risk_score", 0),
                "avg_risk_score": session_stats.get("avg_risk_score", 0),
                "high_risk_count": session_stats.get("high_risk_count", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting session metrics: {e!s}")
            return {}

    def get_failure_metrics(self, fault_manager) -> dict[str, Any]:
        """
        Get failure and recovery metrics

        Args:
            fault_manager: FaultManager instance

        Returns:
            Dict with failure metrics
        """
        try:
            fault_stats = fault_manager.get_system_fault_stats()

            return {
                "total_failures": fault_stats.get("total_failures", 0),
                "failures_by_type": fault_stats.get("failures_by_type", {}),
                "recovery_queue_size": fault_stats.get("recovery_queue_size", 0),
                "dead_letter_queue_size": fault_stats.get("dead_letter_queue_size", 0),
                "last_failures": fault_stats.get("last_failures", [])[:5],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting failure metrics: {e!s}")
            return {}

    def get_retry_metrics(self, retry_manager) -> dict[str, Any]:
        """
        Get retry attempt metrics

        Args:
            retry_manager: RetryManager instance

        Returns:
            Dict with retry metrics
        """
        try:
            retry_stats = retry_manager.get_retry_statistics()

            return {
                "total_scheduled_retries": retry_stats.get("total_scheduled_retries", 0),
                "retry_strategy": retry_stats.get("retry_strategy", "unknown"),
                "max_retries": retry_stats.get("max_retries", 0),
                "recent_retries": retry_stats.get("scheduled_retries", [])[:5],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting retry metrics: {e!s}")
            return {}

    def get_performance_metrics(self, session_tracker) -> dict[str, Any]:
        """
        Get system performance metrics

        Args:
            session_tracker: SessionTracker instance

        Returns:
            Dict with performance metrics
        """
        try:
            stats = session_tracker.get_session_statistics()

            return {
                "avg_processing_time_seconds": stats.get("avg_processing_time", 0),
                "total_sessions": stats.get("active_count", 0) + stats.get("completed_count", 0),
                "throughput_per_minute": self._calculate_throughput(),
                "peak_concurrent_sessions": stats.get("peak_concurrent", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e!s}")
            return {}

    def _calculate_throughput(self) -> float:
        """Calculate sessions processed per minute"""
        try:
            if not self.redis_client:
                return 0.0

            # Get completed sessions from last minute
            one_minute_ago = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()

            count = 0
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match="session:*", count=100)

                for key in keys:
                    try:
                        session_data = self.redis_client.get(key)
                        if session_data:
                            session = json.loads(session_data)
                            if session.get("status") == "COMPLETED":
                                end_time = session.get("end_time", "")
                                if end_time and end_time > one_minute_ago:
                                    count += 1
                    except Exception:
                        continue

                if cursor == 0:
                    break

            return float(count)

        except Exception as e:
            logger.warning(f"Error calculating throughput: {e!s}")
            return 0.0

    def _get_uptime(self) -> int:
        """Get system uptime in seconds"""
        try:
            if not self.redis_client:
                return 0

            uptime_key = "system:start_time"
            start_time_str = self.redis_client.get(uptime_key)

            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str)
                uptime = (datetime.now(timezone.utc) - start_time).total_seconds()
                return int(uptime)

            return 0

        except Exception as e:
            logger.warning(f"Error getting uptime: {e!s}")
            return 0
    from monitoring.prometheus_metrics import get_session_metrics

    def _get_session_metrics(self):
      metrics = get_session_metrics()

      total = (
        metrics["completed"]
        + metrics["failed"]
        + metrics["active"]
      )

      return {
        "active": metrics["active"],
        "completed": metrics["completed"],
        "failed": metrics["failed"],
        "total": total,
      }        
