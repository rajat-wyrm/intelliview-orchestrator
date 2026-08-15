"""
Dashboard API Module

Exposes monitoring data via REST API endpoints for dashboard visualization.

Endpoints:
- GET /metrics/system - System-wide metrics
- GET /metrics/workers - Worker performance
- GET /metrics/sessions - Session activity
- GET /metrics/queue - Queue statistics
- GET /metrics/failures - Failure metrics
- GET /metrics/retries - Retry statistics
- GET /metrics/performance - Performance metrics
- WebSocket /ws/metrics - Real-time updates
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from config import API_TOKEN
from orchestrator import http_cache

logger = logging.getLogger(__name__)


def create_dashboard_routes(
    metrics_collector,
    session_manager,
    worker_registry,
    session_tracker,
    fault_manager,
    retry_manager,
    health_monitor,
    ws_manager,
) -> APIRouter:
    """
    Create dashboard API routes

    Args:
        metrics_collector: MetricsCollector instance
        session_manager: SessionManager instance
        worker_registry: WorkerRegistry instance
        session_tracker: SessionTracker instance
        fault_manager: FaultManager instance
        retry_manager: RetryManager instance
        health_monitor: HealthMonitor instance
        ws_manager: WebSocketManager instance

    Returns:
        APIRouter with dashboard routes
    """

    router = APIRouter()

    # ========== System Metrics Endpoint ==========

    @router.get("/metrics/system")
    @http_cache.cached("monitoring.metrics.system", ttl=2)
    async def get_system_metrics():
        """
        Get comprehensive system-wide metrics

        Returns:
            dict: System metrics including sessions, workers, queue, health
        """
        try:
            logger.debug("Fetching system metrics")

            system_metrics = metrics_collector.get_system_metrics()
            health_check = health_monitor.check_system_health(
                worker_registry=worker_registry, session_manager=session_manager
            )

            return {
                "status": "success",
                "metrics": system_metrics,
                "health_check": health_check,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching system metrics: {e!s}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # ========== Worker Metrics Endpoint ==========

    @router.get("/metrics/workers")
    @http_cache.cached("monitoring.metrics.workers", ttl=2)
    async def get_worker_metrics_endpoint():
        """
        Get detailed worker performance metrics

        Returns:
            dict: Worker metrics including utilization, health, capacity
        """
        try:
            logger.debug("Fetching worker metrics")

            worker_metrics = metrics_collector.get_worker_metrics(worker_registry)

            return {
                "status": "success",
                "metrics": worker_metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching worker metrics: {e!s}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # ========== Session Metrics Endpoint ==========

    @router.get("/metrics/sessions")
    @http_cache.cached("monitoring.metrics.sessions", ttl=2)
    async def get_session_metrics_endpoint():
        """
        Get session activity metrics

        Returns:
            dict: Session metrics including active, completed, failed, risk scores
        """
        try:
            logger.debug("Fetching session metrics")

            session_metrics = metrics_collector.get_session_metrics(session_tracker)

            return {
                "status": "success",
                "metrics": session_metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching session metrics: {e!s}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # ========== Queue Metrics Endpoint ==========

    @router.get("/metrics/queue")
    @http_cache.cached("monitoring.metrics.queue", ttl=2)
    async def get_queue_metrics():
        """
        Get queue statistics and backlog information

        Returns:
            dict: Queue metrics including length, pending tasks, backlog percentage
        """
        try:
            logger.debug("Fetching queue metrics")

            queue_metrics = metrics_collector._get_queue_metrics()

            return {
                "status": "success",
                "metrics": queue_metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching queue metrics: {e!s}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # ========== Failure Metrics Endpoint ==========

    @router.get("/metrics/failures")
    @http_cache.cached("monitoring.metrics.failures", ttl=2)
    async def get_failure_metrics_endpoint():
        """
        Get failure and recovery metrics

        Returns:
            dict: Failure metrics including counts, types, DLQ size
        """
        try:
            logger.debug("Fetching failure metrics")

            failure_metrics = metrics_collector.get_failure_metrics(fault_manager)

            return {
                "status": "success",
                "metrics": failure_metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching failure metrics: {e!s}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # ========== Retry Metrics Endpoint ==========

    @router.get("/metrics/retries")
    @http_cache.cached("monitoring.metrics.retries", ttl=2)
    async def get_retry_metrics_endpoint():
        """
        Get retry attempt metrics

        Returns:
            dict: Retry metrics including scheduled retries, strategy, statistics
        """
        try:
            logger.debug("Fetching retry metrics")

            retry_metrics = metrics_collector.get_retry_metrics(retry_manager)

            return {
                "status": "success",
                "metrics": retry_metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching retry metrics: {e!s}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # ========== Performance Metrics Endpoint ==========

    @router.get("/metrics/performance")
    @http_cache.cached("monitoring.metrics.performance", ttl=2)
    async def get_performance_metrics():
        """
        Get system performance metrics

        Returns:
            dict: Performance metrics including throughput, processing time, concurrency
        """
        try:
            logger.debug("Fetching performance metrics")

            performance_metrics = metrics_collector.get_performance_metrics(
                session_tracker
            )

            return {
                "status": "success",
                "metrics": performance_metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching performance metrics: {e!s}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # ========== Dashboard Summary Endpoint ==========

    @router.get("/metrics/dashboard")
    @http_cache.cached("monitoring.metrics.dashboard", ttl=2)
    async def get_dashboard_summary():
        """
        Get comprehensive dashboard summary with all metrics

        Returns:
            dict: Complete dashboard data for visualization
        """
        try:
            logger.debug("Fetching dashboard summary")

            system = metrics_collector.get_system_metrics()
            workers = metrics_collector.get_worker_metrics(worker_registry)
            sessions = metrics_collector.get_session_metrics(session_tracker)
            queue = metrics_collector._get_queue_metrics()
            failures = metrics_collector.get_failure_metrics(fault_manager)
            retries = metrics_collector.get_retry_metrics(retry_manager)
            performance = metrics_collector.get_performance_metrics(session_tracker)

            return {
                "status": "success",
                "dashboard": {
                    "system": system,
                    "workers": workers,
                    "sessions": sessions,
                    "queue": queue,
                    "failures": failures,
                    "retries": retries,
                    "performance": performance,
                    "connections": ws_manager.get_connection_stats(),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error generating dashboard summary: {e!s}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # ========== WebSocket Real-Time Metrics Endpoint ==========

    @router.websocket("/ws/metrics")
    async def websocket_metrics(websocket: WebSocket):
        """
        WebSocket endpoint for real-time metrics push

        Streams:
        - System metrics every 5 seconds
        - Session updates
        - Worker alerts
        - Failure notifications

        Auth: pass ?token=<API_TOKEN> as a query parameter.
        """
        token = websocket.query_params.get("token")
        if token != API_TOKEN:
            await websocket.close(code=1008, reason="invalid token")
            return
        await ws_manager.connect(websocket)
        # Send a hello immediately so the client knows the connection is live.
        await ws_manager.send_to_connection(
            websocket,
            {"type": "hello", "timestamp": datetime.now(timezone.utc).isoformat()},
        )

        try:
            while True:
                try:
                    # Receive any client messages (for heartbeat/keep-alive)
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)

                    # Echo received message (for ping/pong)
                    if data:
                        await websocket.send_json(
                            {
                                "type": "pong",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                except asyncio.TimeoutError:
                    # Send periodic metrics so dashboards see live updates.
                    try:
                        metrics = {
                            "system": metrics_collector.get_system_metrics(),
                            "workers": metrics_collector.get_worker_metrics(
                                worker_registry
                            ),
                            "sessions": metrics_collector.get_session_metrics(
                                session_tracker
                            ),
                        }
                        await ws_manager.send_to_connection(
                            websocket,
                            {
                                "type": "metrics",
                                "data": metrics,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                    except Exception as e:
                        logger.error(f"Error sending metrics: {e!s}")
                        break
        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket)
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e!s}")
            await ws_manager.disconnect(websocket)

    return router
