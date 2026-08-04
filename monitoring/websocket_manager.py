"""WebSocket connection manager for the dashboard.

Holds the active-connection set and offers typed broadcast helpers that
publish lifecycle events to every connected client. The dashboard frontend
connects via `/monitoring/ws/metrics?token=<api_token>` and listens for
typed messages: `metrics`, `session_update`, `worker_alert`, `health_update`,
and `evaluation_token`.

Broadcast helpers are invoked from:
  * `SessionManager.update_session_status` — when a session transitions
  * `WorkerRegistry.heartbeat` — when a worker's status flips
  * `HealthMonitor.check_system_health` — periodic health pings
  * Celery worker tasks — when a pipeline stage completes
  * Evaluation pipeline — when incremental LLM tokens are generated
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WebSocketManager:
    """Manage active dashboard WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self.connection_count: int = 0

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new dashboard client."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_count += 1
        logger.info(
            "WebSocket client connected. Active: %d (total: %d)",
            len(self.active_connections),
            self.connection_count,
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a client (idempotent)."""
        if websocket in self.active_connections:
            self.active_connections.discard(websocket)
            logger.info(
                "WebSocket client disconnected. Active: %d",
                len(self.active_connections),
            )

    async def send_to_connection(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send a message to a single client."""
        try:
            await websocket.send_json(message)
        except Exception as exc:
            logger.debug("send_to_connection failed: %s", exc)
            await self.disconnect(websocket)

    async def _broadcast(self, message: dict[str, Any]) -> None:
        """Send a message to every active connection, dropping dead ones."""
        dead: set[WebSocket] = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.debug("broadcast send failed: %s", exc)
                dead.add(connection)
        for conn in dead:
            await self.disconnect(conn)

    # --- Typed broadcast helpers -----------------------------------------

    async def broadcast_metrics(self, metrics: dict[str, Any]) -> None:
        await self._broadcast({"type": "metrics", "data": metrics, "timestamp": _now().isoformat()})

    async def broadcast_session_update(
        self,
        session_id: str,
        status: str,
        details: dict[str, Any] | None = None,
        risk_score: float | None = None,
    ) -> None:
        await self._broadcast(
            {
                "type": "session_update",
                "session_id": session_id,
                "status": status,
                "risk_score": risk_score,
                "details": details or {},
                "timestamp": _now().isoformat(),
            }
        )

    async def broadcast_worker_alert(self, worker_id: str, alert_type: str, message: str) -> None:
        await self._broadcast(
            {
                "type": "worker_alert",
                "worker_id": worker_id,
                "alert_type": alert_type,
                "message": message,
                "timestamp": _now().isoformat(),
            }
        )

    async def broadcast_health_status(self, health_status: str, details: dict[str, Any]) -> None:
        await self._broadcast(
            {
                "type": "health_update",
                "status": health_status,
                "details": details,
                "timestamp": _now().isoformat(),
            }
        )
        
    async def broadcast_evaluation_token(self, session_id: str, token: str) -> None:
        """Broadcast an incremental evaluation token for real-time streaming."""
        await self._broadcast(
            {
                "type": "evaluation_token",
                "session_id": session_id,
                "token": token,
                "timestamp": _now().isoformat(),
            }
        )

    # --- Inspection ------------------------------------------------------

    def get_connection_stats(self) -> dict[str, Any]:
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self.connection_count,
            "timestamp": _now().isoformat(),
        }

    def close(self) -> None:
        """Best-effort shutdown hook called from FastAPI lifespan."""
        self.active_connections.clear()


# Shared singleton — `from monitoring.websocket_manager import ws_manager`.
ws_manager = WebSocketManager()
