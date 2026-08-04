"""
Worker Agent — runs alongside the Celery worker process.

Responsibilities:
- Register this worker with the orchestrator API on startup.
- Periodically send heartbeats with the current active task count.
- Deregister on graceful shutdown.
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

        self.tasks_completed = 0  # track total completed tasks
        self.max_tasks_before_restart = int(os.getenv("MAX_TASKS_BEFORE_RESTART", "100"))  # restart limit
        self._restart_requested = False  # restart flag

        self._stop = False
        self._headers = {
            "X-API-Token": API_TOKEN,
            "Content-Type": "application/json",
        }
        self.client = httpx.Client( timeout=5.0, headers=self._headers )

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
                r = self.client.post(
                    f"{self.api_url}{path}",
                    json=payload,
                )

                if r.status_code < 500:
                    return r.status_code < 400
                
                logger.warning(
                    "Worker %s | API %s returned %s | Attempt %d/%d",
                    self.worker_id,
                    path,
                    r.status_code,
                    attempt,
                    retries,
                )

            except Exception as exc:
                logger.warning(
                    "Worker %s | API %s failed: %s | Attempt %d/%d",
                    self.worker_id,
                    path,
                    exc,
                    attempt,
                    retries,
                )
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
            self.client.delete(
                f"{self.api_url}/deregister-worker/{self.worker_id}",
            )
        except Exception as exc:
            logger.debug("Deregister failed: %s", exc)

    def heartbeat_loop(self) -> None:
        while not self._stop:
            ok = self._post(
                "/worker/heartbeat",
                {
                    "worker_id": self.worker_id,
                    "active_tasks": self.active_tasks,
                },
            )

            if not ok:
                logger.warning(
                    "Heartbeat failed. Trying to re-register worker..."
                )

                while not self._stop:
                    if self.register():
                        logger.info(
                            "Worker %s re-registered successfully.",
                            self.worker_id,
                        )
                        break

                    logger.warning(
                        "Re-registration failed. Retrying in %s seconds...",
                        self.heartbeat_interval,
                    )

                    time.sleep(self.heartbeat_interval)


            time.sleep(self.heartbeat_interval)
    

    def shutdown(self, *_):
        logger.info("Shutting down worker agent...")

        self._stop = True

        self.deregister()

        self.client.close()

        sys.exit(0)        

    def _handle_shutdown(self, signum, frame) -> None:
        logger.info("Received signal %s, shutting down worker %s", signum, self.worker_id)
        self._stop = True
        self.deregister()

    def start(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        while not self._stop:
            if self.register():
                break

            logger.warning(
                "Registration failed. Retrying in %s seconds...",
                self.heartbeat_interval,
            )

            time.sleep(self.heartbeat_interval)

        if self._stop:
            return

        Thread(target=self.heartbeat_loop, daemon=True).start()
        logger.info("Worker agent started for %s", self.worker_id)

    def increment_active(self) -> None:
        self.active_tasks += 1

    def decrement_active(self) -> None:
        self.active_tasks = max(0, self.active_tasks - 1)
        self.tasks_completed += 1  # count each completed task

        if self.tasks_completed >= self.max_tasks_before_restart:
            if not self._restart_requested:
                self._restart_requested = True
                logger.info(
                    "Worker %s has processed %d tasks (limit: %d) — requesting graceful restart.",
                    self.worker_id,
                    self.tasks_completed,
                    self.max_tasks_before_restart,
                )
                self._request_restart()

    def _request_restart(self) -> None:
        logger.info(
            "Worker %s initiating graceful shutdown for restart (active tasks remaining: %d)",
            self.worker_id,
            self.active_tasks,
        )
        self.deregister()
        os.kill(os.getpid(), signal.SIGTERM)


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
