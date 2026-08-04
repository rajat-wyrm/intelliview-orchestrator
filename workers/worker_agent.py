"""
Worker Agent — runs alongside the Celery worker process.

Responsibilities:
- Register this worker with the orchestrator API on startup.
- Periodically send heartbeats with the current active task count.
- Deregister on graceful shutdown.
"""

import json
import logging
import os
import signal
import sys
import time
from threading import Thread
from typing import Any

import httpx

from config import API_TOKEN, WORKER_CONCURRENCY

logger = logging.getLogger(__name__)


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "worker_id"):
            log_record["worker_id"] = record.worker_id
        if hasattr(record, "session_id"):
            log_record["session_id"] = record.session_id

        return json.dumps(log_record)


def setup_logging() -> None:
    """Configure logging based on LOG_FORMAT environment variable."""
    log_format = os.getenv("LOG_FORMAT", "text").lower()
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root_logger.addHandler(handler)


class WorkerAgent:
    def __init__(
        self,
        api_url: str,
        worker_id: str,
        capacity: int = WORKER_CONCURRENCY,
        heartbeat_interval: int = 15,
    ):
        self.api_url = api_url.rstrip("/")
        self.worker_id = worker_id
        self.capacity = capacity
        self.heartbeat_interval = heartbeat_interval

        # Process-local counter used for worker heartbeats.
        # This is accurate only when running with the 'solo' pool.
        self.active_tasks = 0

        self.tasks_completed = 0  # track total completed tasks
        self.max_tasks_before_restart = int(os.getenv("MAX_TASKS_BEFORE_RESTART", "100"))  # restart limit
        self._restart_requested = False  # restart flag

        self._stop = False
        self._headers = {
            "X-API-Token": API_TOKEN,
            "Content-Type": "application/json",
        }

        # Read the configured Celery worker pool.
        # Default to 'solo' if not explicitly configured.
        self.pool = os.getenv("CELERY_POOL", "solo")

        # Fail fast if an unsupported pool is used.
        # In prefork mode, each worker process has its own
        # copy of active_tasks, making heartbeat counts inaccurate.
        if self.pool != "solo":
            raise RuntimeError(
                f"Unsupported Celery pool '{self.pool}'. "
                "This worker only supports the 'solo' pool because "
                "the active_tasks counter is process-local and is not "
                "accurate with multiple worker processes."
            )

    def _post(self, path: str, payload: dict, retries: int = 5) -> bool:
        for attempt in range(1, retries + 1):
            try:
                r = httpx.post(
                    f"{self.api_url}{path}",
                    json=payload,
                    headers=self._headers,
                    timeout=5.0,
                )
                if r.status_code < 500:
                    return r.status_code < 400
                logger.warning(
                    "API %s returned %s, retrying",
                    path,
                    r.status_code,
                    extra={"worker_id": self.worker_id},
                )
            except Exception as exc:
                logger.warning(
                    "API %s failed (%s), retrying",
                    path,
                    exc,
                    extra={"worker_id": self.worker_id},
                )
            time.sleep(min(2**attempt, 15))
        return False

    def register(self) -> bool:
        ok = self._post(
            "/register-worker",
            {"worker_id": self.worker_id, "capacity": self.capacity},
        )
        if ok:
            logger.info(
                "Worker %s registered with %s",
                self.worker_id,
                self.api_url,
                extra={"worker_id": self.worker_id},
            )
        else:
            logger.error(
                "Failed to register worker %s",
                self.worker_id,
                extra={"worker_id": self.worker_id},
            )
        return ok

    def deregister(self) -> None:
        try:
            httpx.delete(
                f"{self.api_url}/deregister-worker/{self.worker_id}",
                headers=self._headers,
                timeout=5.0,
            )
        except Exception as exc:
            logger.debug(
                "Deregister failed: %s",
                exc,
                extra={"worker_id": self.worker_id},
            )

    def heartbeat_loop(self) -> None:
        while not self._stop:
            self._post(
                "/worker/heartbeat",
                {
                    "worker_id": self.worker_id,
                    "active_tasks": self.active_tasks,
                },
            )
            time.sleep(self.heartbeat_interval)

    def _handle_shutdown(self, signum, frame) -> None:
        logger.info(
            "Received signal %s, shutting down worker %s",
            signum,
            self.worker_id,
            extra={"worker_id": self.worker_id},
        )
        self._stop = True
        self.deregister()

    def start(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        if not self.register():
            sys.exit(1)
        Thread(target=self.heartbeat_loop, daemon=True).start()
        logger.info(
            "Worker agent started for %s",
            self.worker_id,
            extra={"worker_id": self.worker_id},
        )

    def increment_active(self) -> None:
        self.active_tasks += 1

    def decrement_active(self) -> None:
        self.active_tasks = max(0, self.active_tasks - 1)


if __name__ == "__main__":
    setup_logging()

    api_url = os.getenv("API_URL", "http://fastapi:8000")
    worker_id = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
    agent = WorkerAgent(api_url=api_url, worker_id=worker_id)
    agent.start()

    # Block main thread until shutdown signal is received
    while not agent._stop:
        time.sleep(1)

    logger.info(
        "Worker agent %s has shut down cleanly",
        agent.worker_id,
        extra={"worker_id": agent.worker_id},
    )
