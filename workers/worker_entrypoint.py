"""
Worker entrypoint — runs the worker agent (registration + heartbeats) alongside
the Celery worker, with active task count tracked via Celery signals.

Drain mode:
- Celery already supports a graceful ("warm") shutdown on SIGTERM: it stops
  pulling new tasks and waits for the current task to finish before exiting.
- We hook into Celery's `worker_shutting_down` signal (fired the moment that
  graceful shutdown begins) to tell our WorkerAgent to enter drain mode at
  the same time, so the orchestrator also stops routing new work here.
- `worker_shutdown` fires after Celery has fully stopped, so we use it to
  deregister the worker once everything is done.
"""

import logging
import os
import sys
import threading

from celery.signals import task_postrun, task_prerun, worker_shutdown, worker_shutting_down

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
    threading.Thread(target=agent.heartbeat_loop, daemon=True).start()

    # Celery begins its own graceful ("warm") shutdown here: it stops
    # accepting new tasks and waits for the current task to finish.
    # Put the agent into drain mode at the same moment so the orchestrator
    # also stops routing new work to this worker while it winds down.
    @worker_shutting_down.connect
    def _on_worker_shutting_down(sig=None, how=None, exitcode=None, **kwargs):
        logger.info(
            "Celery %s shutdown initiated (signal=%s) — draining worker %s",
            how,
            sig,
            worker_id,
        )
        agent.enter_drain_mode()

    @worker_shutdown.connect
    def _on_worker_shutdown(**kwargs):
        logger.info("Shutting down worker")
        agent.deregister()

    logger.info("Worker entrypoint ready; starting Celery")

    _run_celery()

    return 0


if __name__ == "__main__":
    sys.exit(main())
