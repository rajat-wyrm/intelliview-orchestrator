"""
Worker entrypoint — runs the worker agent (registration + heartbeats) alongside
the Celery worker, with active task count tracked via Celery signals.
"""

import logging
import os
import signal
import sys
import threading

from celery.signals import task_postrun, task_prerun, worker_shutdown
from config import WORKER_CONCURRENCY
from workers.celery_app import celery_app
from workers.worker_agent import WorkerAgent
from workers.metrics_server import start_worker_metrics

logger = logging.getLogger(__name__)
SUPPORTED_POOL = "solo"



def _run_celery() -> None:
    # Validate the configured Celery pool before starting.
    # The active task counter is process-local, so only the
    # solo pool is supported.
    pool = os.getenv("CELERY_POOL", SUPPORTED_POOL)

    if pool != SUPPORTED_POOL:
        raise RuntimeError(
            f"Unsupported Celery pool '{pool}'. "
            f"Only '{SUPPORTED_POOL}' is supported because the "
            "active task counter is process-local and cannot be "
            "reported accurately across multiple worker processes."
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    start_worker_metrics()

    api_url = os.getenv("API_URL", "http://fastapi:8000")
    worker_id = os.getenv("WORKER_ID", f"worker-{os.uname().nodename}-{os.getpid()}")

    agent = WorkerAgent(api_url=api_url, worker_id=worker_id, capacity=WORKER_CONCURRENCY)
    if not agent.register():
        logger.error("Could not register worker; exiting")
        return 1

    # Wire Celery signals to track active task count
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
    logger.info("Shutting down worker")
    agent.deregister()
    stop_event.set()

    logger.info("Worker entrypoint ready; starting Celery")
    _run_celery()
    return 0

if __name__ == "__main__":
    sys.exit(main())
