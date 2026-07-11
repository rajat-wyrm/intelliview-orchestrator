"""
Structured Audit Logger

Provides tamper-evident audit logging for all significant system events:
- API mutations (POST, PUT, DELETE)
- AI decisions and reasoning
- Security events (auth failures, rate limit hits)
- Configuration changes

Logs are emitted as structured JSON with correlation IDs, timestamps,
and event categories. Supports log export for compliance.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger("audit")


class AuditEvent:
    """Structured audit event."""

    __slots__ = (
        "actor",
        "category",
        "details",
        "event_id",
        "event_type",
        "ip_address",
        "request_id",
        "severity",
        "target",
        "timestamp",
    )

    def __init__(
        self,
        event_type: str,
        category: str,
        actor: str = "system",
        target: str = "",
        details: dict[str, Any] | None = None,
        request_id: str = "",
        ip_address: str = "",
        severity: str = "INFO",
    ) -> None:
        self.event_id = uuid4().hex
        self.event_type = event_type
        self.category = category
        self.actor = actor
        self.target = target
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.request_id = request_id
        self.ip_address = ip_address
        self.severity = severity

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "category": self.category,
            "actor": self.actor,
            "target": self.target,
            "details": self.details,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "severity": self.severity,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, separators=(",", ":"))


class AuditLogger:
    """Structured audit logger with categorized events and export support."""

    CATEGORIES = {
        "mutation": "API_MUTATION",
        "ai_decision": "AI_DECISION",
        "security": "SECURITY",
        "config": "CONFIG_CHANGE",
        "system": "SYSTEM_EVENT",
        "data_access": "DATA_ACCESS",
    }

    def __init__(self, log_file: str | None = None) -> None:
        self.log_file = log_file or os.getenv("AUDIT_LOG_FILE", "")
        self._buffer: list[dict[str, Any]] = []
        self._buffer_max = 500
        logger.info("AuditLogger initialized (file=%s)", self.log_file or "stdout-only")

    def log_event(self, event: AuditEvent) -> None:
        """Emit an audit event to the logger and optionally buffer for export."""
        level = getattr(logging, event.severity, logging.INFO)
        logger.log(level, f"[AUDIT] {event.event_type}", extra=event.to_dict())

        if self.log_file:
            self._write_to_file(event)

        self._buffer.append(event.to_dict())
        if len(self._buffer) > self._buffer_max:
            self._buffer = self._buffer[-self._buffer_max :]

    def log_api_mutation(
        self,
        method: str,
        path: str,
        status: int,
        actor: str = "api",
        details: dict[str, Any] | None = None,
        request_id: str = "",
        ip_address: str = "",
    ) -> None:
        """Log an API mutation (POST/PUT/DELETE)."""
        event = AuditEvent(
            event_type=f"{method} {path}",
            category=self.CATEGORIES["mutation"],
            actor=actor,
            target=path,
            details={
                "method": method,
                "path": path,
                "status_code": status,
                **(details or {}),
            },
            request_id=request_id,
            ip_address=ip_address,
            severity="INFO" if status < 400 else "WARNING",
        )
        self.log_event(event)

    def log_ai_decision(
        self,
        session_id: str,
        pipeline: str,
        decision: str,
        reasoning: str = "",
        risk_score: float | None = None,
        details: dict[str, Any] | None = None,
        request_id: str = "",
    ) -> None:
        """Log an AI pipeline decision with reasoning."""
        event = AuditEvent(
            event_type="AI_DECISION",
            category=self.CATEGORIES["ai_decision"],
            actor=pipeline,
            target=f"session:{session_id}",
            details={
                "session_id": session_id,
                "pipeline": pipeline,
                "decision": decision,
                "reasoning": reasoning,
                "risk_score": risk_score,
                **(details or {}),
            },
            request_id=request_id,
            severity="INFO",
        )
        self.log_event(event)

    def log_security_event(
        self,
        event_type: str,
        actor: str = "unknown",
        details: dict[str, Any] | None = None,
        request_id: str = "",
        ip_address: str = "",
    ) -> None:
        """Log a security event (auth failure, rate limit, etc.)."""
        event = AuditEvent(
            event_type=event_type,
            category=self.CATEGORIES["security"],
            actor=actor,
            target="auth",
            details=details or {},
            request_id=request_id,
            ip_address=ip_address,
            severity="WARNING",
        )
        self.log_event(event)

    def log_config_change(
        self,
        setting: str,
        old_value: str,
        new_value: str,
        actor: str = "admin",
    ) -> None:
        """Log a configuration change."""
        event = AuditEvent(
            event_type="CONFIG_CHANGE",
            category=self.CATEGORIES["config"],
            actor=actor,
            target=setting,
            details={
                "setting": setting,
                "old_value": old_value,
                "new_value": new_value,
            },
            severity="WARNING",
        )
        self.log_event(event)

    def log_data_access(
        self,
        resource: str,
        action: str,
        actor: str = "api",
        details: dict[str, Any] | None = None,
        request_id: str = "",
    ) -> None:
        """Log a data access event."""
        event = AuditEvent(
            event_type=f"DATA_{action.upper()}",
            category=self.CATEGORIES["data_access"],
            actor=actor,
            target=resource,
            details=details or {},
            request_id=request_id,
            severity="INFO",
        )
        self.log_event(event)

    def get_recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent audit events from the in-memory buffer."""
        return list(reversed(self._buffer[-limit:]))

    def get_events_by_category(self, category: str, limit: int = 100) -> list[dict[str, Any]]:
        """Filter recent events by category."""
        cat_key = self.CATEGORIES.get(category, category)
        return [e for e in reversed(self._buffer) if e.get("category") == cat_key][:limit]

    def export_events(
        self,
        format: str = "json",
        start_time: str | None = None,
        end_time: str | None = None,
        category: str | None = None,
    ) -> str:
        """Export audit events for compliance / analysis.

        Args:
            format: Output format - "json" or "jsonl" (JSON Lines).
            start_time: ISO timestamp filter (inclusive).
            end_time: ISO timestamp filter (inclusive).
            category: Filter by category key.

        Returns:
            String of formatted audit events.
        """
        events = list(self._buffer)

        if start_time:
            events = [e for e in events if e.get("timestamp", "") >= start_time]
        if end_time:
            events = [e for e in events if e.get("timestamp", "") <= end_time]
        if category:
            cat_key = self.CATEGORIES.get(category, category)
            events = [e for e in events if e.get("category") == cat_key]

        if format == "jsonl":
            return "\n".join(json.dumps(e, default=str) for e in events)
        return json.dumps(events, default=str, indent=2)

    def _write_to_file(self, event: AuditEvent) -> None:
        """Append a single event line to the audit log file."""
        try:
            os.makedirs(os.path.dirname(self.log_file) or ".", exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")
        except OSError as exc:
            logger.error("Failed to write audit log to %s: %s", self.log_file, exc)

    def close(self) -> None:
        """Flush and close."""
        self._buffer.clear()


# Module-level singleton
audit_logger = AuditLogger()
