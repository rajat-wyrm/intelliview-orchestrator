"""
Worker entrypoint — runs the worker agent (registration + heartbeats)
alongside the Celery worker, with active task count tracked via
Celery signals.
"""

import logging
import os
import platform
import sys
import threading

from celery.signals import task_postrun, task_prerun, worker_shutdown

from config import WORKER_CONCURRENCY
from workers.celery_app import celery_app
from workers.worker_agent import WorkerAgent

logger = logging.getLogger(__name__)

SUPPORTED_POOL = "solo"

agent = None


def _run_celery() -> None:
    """
    Start the Celery worker.
    """

    pool = os.getenv("CELERY_POOL", SUPPORTED_POOL)

    if pool != SUPPORTED_POOL:
        raise RuntimeError(
            f"Unsupported Celery pool '{pool}'. "
            f"Only '{SUPPORTED_POOL}' is supported because "
            "the active task counter is process-local."
        )

    argv = [
        "-A",
        "workers.celery_app",
        "worker",
        "--loglevel=info",

        # Required for Flower monitoring
        "--events",

        # Worker configuration
        "--pool=solo",
        "--concurrency=1",

        # Task limits
        "--time-limit=1800",
        "--soft-time-limit=1500",
    ]

    celery_app.worker_main(argv)


def main() -> int:
    """
    Register worker, start heartbeat, then launch Celery.
    """

    global agent

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    api_url = os.getenv(
        "API_URL",
        "http://fastapi:8000"
    )

    worker_id = os.getenv(
        "WORKER_ID",
        f"worker-{platform.node()}-{os.getpid()}",
    )

    agent = WorkerAgent(
        api_url=api_url,
        worker_id=worker_id,
        capacity=WORKER_CONCURRENCY,
    )

    # Register worker with FastAPI orchestrator
    if not agent.register():
        logger.error("Worker registration failed.")
        return 1

    logger.info("Worker registered successfully.")

    # Track active tasks

    @task_prerun.connect
    def _on_task_start(**kwargs):
        if agent:
            agent.increment_active()


    @task_postrun.connect
    def _on_task_finish(**kwargs):
        if agent:
            agent.decrement_active()


    # Start heartbeat thread

    threading.Thread(
        target=agent.heartbeat_loop,
        daemon=True,
    ).start()


    logger.info("Heartbeat thread started.")
    logger.info("Starting Celery worker with events enabled...")


    _run_celery()

    return 0



@worker_shutdown.connect
def _shutdown(**kwargs):
    """
    Deregister worker when Celery shuts down.
    """

    global agent

    logger.info("Worker shutting down.")

    if agent:
        agent.deregister()



if __name__ == "__main__":
    sys.exit(main())
