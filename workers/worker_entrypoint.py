"""
Worker entrypoint — runs the worker agent (registration + heartbeats) alongside
the Celery worker, with active task count tracked via Celery signals.
"""

import logging
import os
import signal
import sys
import threading

from celery.signals import task_postrun, task_prerun

from config import WORKER_CONCURRENCY
from workers.celery_app import celery_app
from workers.worker_agent import WorkerAgent

logger = logging.getLogger(__name__)


def _run_celery() -> None:
    argv = [
        "-A",
        "workers.celery_app",
        "worker",
        "--loglevel=info",
        f"--concurrency={os.getenv('WORKER_CONCURRENCY', WORKER_CONCURRENCY)}",
        "--time-limit=1800",
        "--soft-time-limit=1500",
    ]
    celery_app.worker_main(argv)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    api_url = os.getenv("API_URL", "http://fastapi:8000")
    worker_id = os.getenv("WORKER_ID", f"worker-{os.uname().nodename}-{os.getpid()}")

    agent = WorkerAgent(
        api_url=api_url,
        worker_id=worker_id,
        capacity=WORKER_CONCURRENCY,
    )

    agent.start()

    # Wire Celery signals to track active task count
    @task_prerun.connect
    def _on_prerun(**_):
        agent.increment_active()

    @task_postrun.connect
    def _on_postrun(**_):
        agent.decrement_active()

=======
>>>>>>> pr-314-head
    logger.info("Worker entrypoint ready; starting Celery")
    _run_celery()
    return 0


if __name__ == "__main__":
    sys.exit(main())




