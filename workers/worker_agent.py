"""
Worker Agent — runs alongside the Celery worker process.

Responsibilities:
- Register this worker with the orchestrator API on startup.
- Periodically send heartbeats with the current active task count.
- Deregister on graceful shutdown.
- Support "drain mode": stop accepting new tasks while letting
  in-progress tasks finish normally before shutting down.
"""

import logging
import os
import signal
import sys
import time
from threading import Thread

import httpx

from config import API_TOKEN, WORKER_CONCURRENCY

logger = logging.getLogger(__name__)


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

        self._stop = False
        self._headers = {
            "X-API-Token": API_TOKEN,
            "Content-Type": "application/json",
        }

        # --- Drain mode state ---
        # When True, the worker stops accepting new tasks but keeps
        # running any tasks already in progress until they finish.
        self.draining = False
        self._drain_complete = False

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
                logger.warning("API %s returned %s, retrying", path, r.status_code)
            except Exception as exc:
                logger.warning("API %s failed (%s), retrying", path, exc)
            time.sleep(min(2**attempt, 15))
        return False

    def register(self) -> bool:
        ok = self._post("/register-worker", {"worker_id": self.worker_id, "capacity": self.capacity})
        if ok:
            logger.info("Worker %s registered with %s", self.worker_id, self.api_url)
        else:
            logger.error("Failed to register worker %s", self.worker_id)
        return ok

    def deregister(self) -> None:
        try:
            httpx.delete(
                f"{self.api_url}/deregister-worker/{self.worker_id}",
                headers=self._headers,
                timeout=5.0,
            )
        except Exception as exc:
            logger.debug("Deregister failed: %s", exc)

    def heartbeat_loop(self) -> None:
        while not self._stop:
            # The orchestrator's heartbeat endpoint doesn't accept a
            # "status" field, so a draining worker reports itself as
            # already at full capacity. That's enough for the
            # orchestrator's existing "active_tasks < capacity" check
            # to stop routing new work here, without needing any
            # orchestrator-side change.
            reported_active_tasks = self.capacity if self.draining else self.active_tasks

            self._post(
                "/worker/heartbeat",
                {"worker_id": self.worker_id, "active_tasks": reported_active_tasks},
            )
            time.sleep(self.heartbeat_interval)

    def enter_drain_mode(self) -> None:
        """Stop accepting new tasks; let in-progress tasks finish normally."""
        if self.draining:
            logger.info("Worker %s is already draining", self.worker_id)
            return

        self.draining = True
        logger.info(
            "Worker %s ENTERING DRAIN MODE (%d task(s) still in progress) — no new tasks will be accepted",
            self.worker_id,
            self.active_tasks,
        )

        if self.active_tasks == 0:
            self._finish_draining()

    def _finish_draining(self) -> None:
        """Called once every in-progress task has completed."""
        if self._drain_complete:
            return
        self._drain_complete = True
        logger.info(
            "Worker %s FINISHED DRAINING — all in-progress tasks complete, safe to shut down now",
            self.worker_id,
        )
        self._stop = True
        self.deregister()

    def _handle_shutdown(self, signum, frame) -> None:
        if not self.draining:
            logger.info(
                "Received signal %s — starting graceful drain for worker %s",
                signum,
                self.worker_id,
            )
            self.enter_drain_mode()
        else:
            logger.warning(
                "Received signal %s again while draining — forcing immediate shutdown of worker %s",
                signum,
                self.worker_id,
            )
            self._stop = True
            self.deregister()

    def start(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        if not self.register():
            sys.exit(1)
        Thread(target=self.heartbeat_loop, daemon=True).start()
        logger.info("Worker agent started for %s", self.worker_id)

    def increment_active(self) -> None:
        self.active_tasks += 1

    def decrement_active(self) -> None:
        self.active_tasks = max(0, self.active_tasks - 1)
        # If we were waiting to drain and the last in-progress task
        # just finished, drain is now complete.
        if self.draining and self.active_tasks == 0:
            self._finish_draining()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_url = os.getenv("API_URL", "http://fastapi:8000")
    worker_id = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
    agent = WorkerAgent(api_url=api_url, worker_id=worker_id)
    agent.start()

    # Block main thread until shutdown signal is received
    while not agent._stop:
        time.sleep(1)

    logger.info("Worker agent %s has shut down cleanly", agent.worker_id)
