"""
Worker entrypoint — runs the worker agent (registration + heartbeats) alongside
the Celery worker, with active task count tracked via Celery signals.
"""

import json
import logging
import os
import sys
import threading
from typing import Any

from celery.signals import task_postrun, task_prerun, worker_shutdown

from config import WORKER_CONCURRENCY
from workers.celery_app import celery_app
from workers.metrics_server import start_worker_metrics
from workers.worker_agent import WorkerAgent

logger = logging.getLogger(__name__)

SUPPORTED_POOL = "solo"

agent = None


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

    # Clear existing handlers to prevent duplicate output
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root_logger.addHandler(handler)


def _run_celery() -> None:
    # Validate the configured Celery pool before starting.
    pool = os.getenv("CELERY_POOL", SUPPORTED_POOL)

    if pool != SUPPORTED_POOL:
        raise RuntimeError(
            f"Unsupported Celery pool '{pool}'. "
            f"Only '{SUPPORTED_POOL}' is supported because the "
            "active task counter is process-local."
        )

    argv = [
        "-A",
        "workers.celery_app",
        "worker",
        "--loglevel=info",
        "--pool=solo",
        "--concurrency=1",
        "--time-limit=1800",
        "--soft-time-limit=1500",
    ]

    celery_app.worker_main(argv)


def main() -> int:
    global agent

    setup_logging()

    start_worker_metrics()

    api_url = os.getenv("API_URL", "http://fastapi:8000")
    worker_id = os.getenv(
        "WORKER_ID",
        f"worker-{os.uname().nodename}-{os.getpid()}",
    )

    agent = WorkerAgent(
        api_url=api_url,
        worker_id=worker_id,
        capacity=WORKER_CONCURRENCY,
    )

    if not agent.register():
        logger.error("Could not register worker; exiting", extra={"worker_id": worker_id})
        return 1

    # Track active Celery tasks
    @task_prerun.connect
    def _on_prerun(**_):
        agent.increment_active()

    @task_postrun.connect
    def _on_postrun(**_):
        agent.decrement_active()

    # Start the heartbeat loop managed by WorkerAgent
    threading.Thread(target=agent.heartbeat_loop, daemon=True).start()

    @worker_shutdown.connect
    def _on_worker_shutdown(**kwargs):
        logger.info("Shutting down worker", extra={"worker_id": agent.worker_id})
        agent.deregister()

    logger.info(
        "Worker entrypoint ready; starting Celery",
        extra={"worker_id": worker_id},
    )

    _run_celery()

    return 0


@worker_shutdown.connect
def _on_worker_shutdown(**kwargs):
    global agent

    logger.info("Shutting down worker")

    if agent:
        agent.deregister()


if __name__ == "__main__":
    sys.exit(main())
