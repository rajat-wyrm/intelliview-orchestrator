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
    api_url = os.getenv("API_URL", "http://fastapi:8000")
    worker_id = os.getenv("WORKER_ID", f"worker-{os.uname().nodename}-{os.getpid()}")

    from orchestrator.logging_config import configure_logging
    configure_logging(service="worker", worker_id=worker_id)

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

    # Heartbeat thread
    stop_event = threading.Event()

    def _hb_loop():
        while not stop_event.is_set():
            try:
                agent._post(
                    "/worker/heartbeat",
                    {
                        "worker_id": agent.worker_id,
                        "active_tasks": agent.active_tasks,
                    },
                )
            except Exception as exc:
                logger.debug("Heartbeat error: %s", exc)
            stop_event.wait(agent.heartbeat_interval)

    threading.Thread(target=_hb_loop, daemon=True).start()

    def _shutdown(*_):
        logger.info("Shutting down worker")
        agent.deregister()
        stop_event.set()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Worker entrypoint ready; starting Celery")
    _run_celery()
    return 0


if __name__ == "__main__":
    sys.exit(main())