"""
Health Monitor Module

Continuously monitors system and worker health to detect failures early.

Responsibilities:
- Detect inactive/unhealthy workers
- Detect stuck/failed sessions
- Monitor queue backlog
- Trigger alerts and recovery actions
- Deep dependency health checks (Redis, Postgres, Celery)
- Kubernetes-style readiness and liveness probes
- Dependency status tracking with latency measurements
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from orchestrator.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class HealthStatus(str):
    """Health status indicators"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class DependencyStatus:
    """Tracks the health and latency of a single dependency."""

    __slots__ = ("error", "healthy", "last_check", "latency_ms", "metadata", "name")

    def __init__(self, name: str) -> None:
        self.name = name
        self.healthy = False
        self.latency_ms = 0.0
        self.last_check: str = ""
        self.error: str | None = None
        self.metadata: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "healthy": self.healthy,
            "latency_ms": round(self.latency_ms, 2),
            "last_check": self.last_check,
            "error": self.error,
            "metadata": self.metadata,
        }


class HealthMonitor:
    """
    Monitors system and component health to detect failures and trigger recovery.

    Monitors:
    - Worker node heartbeats and responsiveness
    - Session processing timeouts
    - Queue backlog and delays
    - System resource utilization
    - Deep dependency checks (Redis, Postgres, Celery broker)
    """

    def __init__(
        self,
        heartbeat_timeout: int = 60,
        session_timeout: int = 1800,
        queue_threshold: int = 1000,
    ):
        self.heartbeat_timeout = heartbeat_timeout
        self.session_timeout = session_timeout
        self.queue_threshold = queue_threshold
        self.redis_client = get_redis_client()
        self.health_status_key = "system:health_status"
        self.last_check_key = "system:last_health_check"
        self._dep_status: dict[str, DependencyStatus] = {}

        logger.info(
            "HealthMonitor initialized: heartbeat_timeout=%ds, session_timeout=%ds, queue_threshold=%d",
            heartbeat_timeout,
            session_timeout,
            queue_threshold,
        )

    # ------------------------------------------------------------------
    # Readiness probe (Kubernetes-style)
    # ------------------------------------------------------------------

    def readiness_check(self) -> dict[str, Any]:
        """Return true readiness — all critical dependencies must be up.

        Use this for k8s readinessProbe: the service only receives
        traffic when this returns ready=True.
        """
        deps = self._check_all_dependencies()
        ready = all(d["healthy"] for d in deps.values())
        return {
            "ready": ready,
            "status": HealthStatus.HEALTHY if ready else HealthStatus.UNHEALTHY,
            "dependencies": deps,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Liveness probe (Kubernetes-style)
    # ------------------------------------------------------------------

    def liveness_check(self) -> dict[str, Any]:
        """Return whether the process itself is alive and responsive.

        This only checks that the Python process can respond — it does
        NOT check downstream dependencies. Use for k8s livenessProbe.
        """
        return {
            "alive": True,
            "status": HealthStatus.HEALTHY,
            "uptime_seconds": self._get_uptime(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Deep dependency health checks
    # ------------------------------------------------------------------

    def _check_all_dependencies(self) -> dict[str, dict[str, Any]]:
        """Check every critical dependency and return its status."""
        results: dict[str, dict[str, Any]] = {}

        # Redis
        results["redis"] = self._deep_check_redis()

        # PostgreSQL
        results["postgres"] = self._deep_check_postgres()

        # Celery broker (Redis-backed)
        results["celery_broker"] = self._deep_check_celery_broker()

        return results

    def _deep_check_redis(self) -> dict[str, Any]:
        """Ping Redis, measure latency, and report server info."""
        dep = DependencyStatus("redis")
        start = time.monotonic()
        try:
            if not self.redis_client:
                dep.error = "Redis client not initialized"
                self._dep_status["redis"] = dep
                return dep.to_dict()

            self.redis_client.ping()
            dep.latency_ms = (time.monotonic() - start) * 1000
            dep.healthy = True

            info = self.redis_client.info()
            dep.metadata = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
            }
            dep.last_check = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            dep.healthy = False
            dep.error = str(exc)
            dep.latency_ms = (time.monotonic() - start) * 1000
            logger.warning("Redis deep check failed: %s", exc)

        self._dep_status["redis"] = dep
        return dep.to_dict()

    def _deep_check_postgres(self) -> dict[str, Any]:
        """Execute a lightweight query against Postgres."""
        dep = DependencyStatus("postgres")
        start = time.monotonic()
        try:
            from database.db import engine

            with engine.connect() as conn:
                result = conn.execute(__import__("sqlalchemy").text("SELECT 1 AS ok"))
                row = result.fetchone()
                dep.healthy = row is not None and row[0] == 1
            dep.latency_ms = (time.monotonic() - start) * 1000
            dep.last_check = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            dep.healthy = False
            dep.error = str(exc)
            dep.latency_ms = (time.monotonic() - start) * 1000
            logger.warning("Postgres deep check failed: %s", exc)

        self._dep_status["postgres"] = dep
        return dep.to_dict()

    def _deep_check_celery_broker(self) -> dict[str, Any]:
        """Check that the Celery broker (Redis) is accepting connections."""
        dep = DependencyStatus("celery_broker")
        start = time.monotonic()
        try:
            if not self.redis_client:
                dep.error = "Redis client not available"
                self._dep_status["celery_broker"] = dep
                return dep.to_dict()

            self.redis_client.ping()
            dep.latency_ms = (time.monotonic() - start) * 1000
            dep.healthy = True
            dep.last_check = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            dep.healthy = False
            dep.error = str(exc)
            dep.latency_ms = (time.monotonic() - start) * 1000
            logger.warning("Celery broker deep check failed: %s", exc)

        self._dep_status["celery_broker"] = dep
        return dep.to_dict()

    # ------------------------------------------------------------------
    # Existing health methods (unchanged API)
    # ------------------------------------------------------------------

    def check_system_health(self, worker_registry=None, session_manager=None) -> dict[str, Any]:
        """Perform comprehensive system health check."""
        try:
            logger.debug("Performing comprehensive system health check")

            health_status = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": HealthStatus.HEALTHY,
                "components": {},
            }

            redis_status = self._check_redis_health()
            health_status["components"]["redis"] = redis_status
            if redis_status["status"] != HealthStatus.HEALTHY:
                health_status["overall_status"] = HealthStatus.CRITICAL

            if worker_registry:
                worker_status = self.check_worker_health(worker_registry)
                health_status["components"]["workers"] = worker_status
                if (
                    worker_status["status"] in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]
                    and health_status["overall_status"] != HealthStatus.CRITICAL
                ):
                    health_status["overall_status"] = worker_status["status"]

            if session_manager:
                session_status = self.check_session_health(session_manager)
                health_status["components"]["sessions"] = session_status
                if (
                    session_status["status"] in [HealthStatus.CRITICAL, HealthStatus.DEGRADED]
                    and health_status["overall_status"] == HealthStatus.HEALTHY
                ):
                    health_status["overall_status"] = session_status["status"]

            queue_status = self.check_queue_health()
            health_status["components"]["queue"] = queue_status
            if queue_status["status"] == HealthStatus.CRITICAL:
                health_status["overall_status"] = HealthStatus.CRITICAL
            elif queue_status["status"] == HealthStatus.DEGRADED:
                if health_status["overall_status"] == HealthStatus.HEALTHY:
                    health_status["overall_status"] = HealthStatus.DEGRADED

            if self.redis_client:
                self.redis_client.set(self.health_status_key, json.dumps(health_status), ex=300)
                self.redis_client.set(self.last_check_key, datetime.now(timezone.utc).isoformat())

            logger.info("System health check complete: %s", health_status["overall_status"])
            return health_status

        except Exception as e:
            logger.error("Error checking system health: %s", e)
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": HealthStatus.UNHEALTHY,
                "error": str(e),
            }

    def check_worker_health(self, worker_registry) -> dict[str, Any]:
        """Check health of all workers."""
        try:
            logger.debug("Checking worker health")

            all_workers = worker_registry.get_all_workers()
            unhealthy_workers = worker_registry.detect_unhealthy_workers()

            total = len(all_workers)
            healthy = total - len(unhealthy_workers)

            status = HealthStatus.HEALTHY
            if len(unhealthy_workers) > total * 0.5:
                status = HealthStatus.CRITICAL
            elif len(unhealthy_workers) > 0:
                status = HealthStatus.DEGRADED

            return {
                "status": status,
                "total_workers": total,
                "healthy_workers": healthy,
                "unhealthy_workers": len(unhealthy_workers),
                "unhealthy_list": unhealthy_workers[:10],
                "availability_percent": (healthy / total * 100) if total > 0 else 0,
            }

        except Exception as e:
            logger.error("Error checking worker health: %s", e)
            return {"status": HealthStatus.UNHEALTHY, "error": str(e)}

    def check_session_health(self, session_manager) -> dict[str, Any]:
        """Check health of active sessions (detect stuck sessions)."""
        try:
            logger.debug("Checking session health")

            stuck_sessions = []
            active_sessions = (
                session_manager.get_active_sessions()
                if hasattr(session_manager, "get_active_sessions")
                else []
            )

            for session in active_sessions:
                if session.get("status") == "PROCESSING":
                    start_time = session.get("start_time")
                    if start_time:
                        try:
                            start_dt = datetime.fromisoformat(start_time)
                            elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds()
                            if elapsed > self.session_timeout:
                                stuck_sessions.append(
                                    {"session_id": session.get("session_id"), "elapsed_seconds": elapsed}
                                )
                        except Exception:
                            pass

            status = HealthStatus.HEALTHY
            if len(stuck_sessions) > len(active_sessions) * 0.25:
                status = HealthStatus.CRITICAL
            elif len(stuck_sessions) > 0:
                status = HealthStatus.DEGRADED

            return {
                "status": status,
                "total_active": len(active_sessions),
                "stuck_sessions": len(stuck_sessions),
                "stuck_list": stuck_sessions[:5],
                "max_processing_time": max([s.get("elapsed_seconds", 0) for s in stuck_sessions], default=0),
            }

        except Exception as e:
            logger.error("Error checking session health: %s", e)
            return {"status": HealthStatus.UNHEALTHY, "error": str(e)}

    def check_queue_health(self) -> dict[str, Any]:
        """Check Redis queue backlog and health."""
        try:
            logger.debug("Checking queue health")

            if not self.redis_client:
                return {"status": HealthStatus.UNHEALTHY, "error": "Redis not available"}

            queue_length = self.redis_client.llen("celery_queue") if self.redis_client else 0

            status = HealthStatus.HEALTHY
            if queue_length > self.queue_threshold:
                status = HealthStatus.CRITICAL
            elif queue_length > self.queue_threshold * 0.7:
                status = HealthStatus.DEGRADED

            return {
                "status": status,
                "queue_length": queue_length,
                "threshold": self.queue_threshold,
                "backlog_percent": (queue_length / self.queue_threshold * 100)
                if self.queue_threshold > 0
                else 0,
            }

        except Exception as e:
            logger.error("Error checking queue health: %s", e)
            return {"status": HealthStatus.UNHEALTHY, "error": str(e)}

    def _check_redis_health(self) -> dict[str, Any]:
        """Check Redis connectivity and responsiveness."""
        try:
            if not self.redis_client:
                return {"status": HealthStatus.UNHEALTHY, "error": "Redis client not initialized"}

            self.redis_client.ping()
            info = self.redis_client.info()
            connected_clients = info.get("connected_clients", 0)
            used_memory = info.get("used_memory_human", "unknown")

            return {
                "status": HealthStatus.HEALTHY,
                "connected": True,
                "clients": connected_clients,
                "memory": used_memory,
            }

        except Exception as e:
            logger.error("Error checking Redis health: %s", e)
            return {"status": HealthStatus.UNHEALTHY, "error": str(e)}

    def detect_worker_failures(self, worker_registry) -> list[str]:
        """Identify workers that appear to have failed."""
        try:
            logger.debug("Detecting worker failures")
            failed_workers = worker_registry.detect_unhealthy_workers()
            if failed_workers:
                logger.warning("Detected %d failed workers: %s", len(failed_workers), failed_workers)
            return failed_workers

        except Exception as e:
            logger.error("Error detecting worker failures: %s", e)
            return []

    def detect_stuck_sessions(self, session_manager) -> list[str]:
        """Identify sessions stuck in PROCESSING state."""
        try:
            logger.debug("Detecting stuck sessions")

            stuck_sessions = []
            active_sessions = (
                session_manager.get_active_sessions()
                if hasattr(session_manager, "get_active_sessions")
                else []
            )

            for session in active_sessions:
                if session.get("status") == "PROCESSING":
                    start_time = session.get("start_time")
                    if start_time:
                        try:
                            start_dt = datetime.fromisoformat(start_time)
                            elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds()
                            if elapsed > self.session_timeout:
                                stuck_sessions.append(session.get("session_id"))
                                logger.warning(
                                    "Detected stuck session %s: %ds processing",
                                    session.get("session_id"),
                                    int(elapsed),
                                )
                        except Exception:
                            pass

            return stuck_sessions

        except Exception as e:
            logger.error("Error detecting stuck sessions: %s", e)
            return []

    def _get_uptime(self) -> int:
        """Get process uptime in seconds."""
        try:
            import os

            stat = os.stat(f"/proc/{os.getpid()}/stat")
            # field 22 is starttime (clock ticks since boot)
            start_ticks = int(stat.st_mtime)
            return int(time.time() - start_ticks)
        except Exception:
            return 0
