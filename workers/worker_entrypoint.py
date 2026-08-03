"""
Worker entrypoint — runs the worker agent (registration + heartbeats) alongside
the Celery worker, with active task count tracked via Celery signals.
"""

import logging
import os
import sys
import threading

from celery.signals import task_postrun, task_prerun, worker_shutdown

from config import WORKER_CONCURRENCY
from workers.celery_app import celery_app
from workers.metrics_server import start_worker_metrics
from workers.worker_agent import WorkerAgent

logger = logging.getLogger(__name__)

SUPPORTED_POOL = "solo"

agent = None


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

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Validate required configuration settings right at startup (Issue 1)
    required_settings = ["API_URL", "API_TOKEN"]
    missing_settings = [setting for setting in required_settings if not os.getenv(setting)]

    if missing_settings:
        logger.error(f"Startup failed: Missing required environment variables: {', '.join(missing_settings)}")
        return 1

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
        logger.error("Could not register worker; exiting")
        return 1

    # Track active Celery tasks
    @task_prerun.connect
    def _on_prerun(**_):
        agent.increment_active()

    @task_postrun.connect
    def _on_postrun(**_):
        agent.decrement_active()

    # Start the heartbeat loop managed by WorkerAgent
    heartbeat_thread = threading.Thread(
        target=agent.heartbeat_loop,
        daemon=True,
    )
    heartbeat_thread.start()

    @worker_shutdown.connect
    def _on_worker_shutdown(**kwargs):
        logger.info("Shutting down worker")

        agent.deregister()

        heartbeat_thread.join(timeout=5)

        if heartbeat_thread.is_alive():
            logger.warning("Heartbeat thread did not stop within timeout.")

    logger.info("Worker entrypoint ready; starting Celery")

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
