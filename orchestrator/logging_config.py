r"""
Structured (JSON) logging for the orchestrator.

Two output modes:
- JSON: one line per event, machine-parseable, includes any `extra` fields
- Plain: legacy human-readable format (the default until JSON_LOGGING=1)

Activated via the \`JSON_LOGGING\` env var. Safe to call \`configure_logging()\`
multiple times — it replaces existing handlers.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    """Render each log record as a single-line JSON object.

    Includes the standard LogRecord attributes plus any keyword arguments
    passed via `extra={...}`.
    """

    RESERVED = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Surface any `extra={...}` fields
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str | None = None) -> None:
    """Configure the root logger with the chosen format."""
    chosen_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    json_mode = os.getenv("JSON_LOGGING", "1") == "1"

    root = logging.getLogger()
    root.setLevel(getattr(logging, chosen_level, logging.INFO))
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stdout)
    if json_mode:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """Emit a structured log event with arbitrary fields.

    Example:
        log_event(logger, logging.INFO, "session_completed",
                  session_id=..., risk_score=0.3)
    """
    logger.log(level, event, extra=fields)
