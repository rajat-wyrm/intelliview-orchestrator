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
from typing import Optional

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
        self.active_tasks = 0
        self._stop = False
        self._headers = {"X-API-Token": API_TOKEN, "Content-Type": "application/json"}

    def _request(self, method: str, path: str, payload: Optional[dict] = None, retries: int = 5) -> bool:
        """Shared retry-with-backoff logic for any HTTP call to the orchestrator API."""
        for attempt in range(1, retries + 1):
            try:
                r = httpx.request(
                    method,
                    f"{self.api_url}{path}",
                    json=payload,
                    headers=self._headers,
                    timeout=5.0,
                )
                if r.status_code < 500:
                    return r.status_code < 400
                logger.warning("API %s %s returned %s, retrying (%d/%d)", method, path, r.status_code, attempt, retries)
            except Exception as exc:
                logger.warning("API %s %s failed (%s), retrying (%d/%d)", method, path, exc, attempt, retries)
            if attempt < retries:
                time.sleep(min(2**attempt, 15))
        return False

    def _post(self, path: str, payload: dict, retries: int = 5) -> bool:
        return self._request("POST", path, payload, retries=retries)

    def register(self) -> bool:
        ok = self._post("/register-worker", {"worker_id": self.worker_id, "capacity": self.capacity})
        if ok:
            logger.info("Worker %s registered with %s", self.worker_id, self.api_url)
        else:
            logger.error("Failed to register worker %s", self.worker_id)
        return ok

    def deregister(self, retries: int = 3) -> bool:
        """Tell the orchestrator this worker is going away.

        Uses a shorter retry count than register()/heartbeats (this runs during
        shutdown, so we don't want to hang the process for too long) but still
        retries instead of giving up after a single attempt — this is the last
        chance to tell the API we're gone.
        """
        ok = self._request("DELETE", f"/deregister-worker/{self.worker_id}", retries=retries)
        if ok:
            logger.info("Worker %s deregistered from %s", self.worker_id, self.api_url)
        else:
            logger.warning(
                "Failed to deregister worker %s after %d attempts; "
                "orchestrator may still think this worker is active",
                self.worker_id,
                retries,
            )
        return ok

    def heartbeat_loop(self) -> None:
        while not self._stop:
            self._post(
                "/worker/heartbeat",
                {"worker_id": self.worker_id, "active_tasks": self.active_tasks},
            )
            time.sleep(self.heartbeat_interval)

    def start(self) -> None:
        signal.signal(signal.SIGTERM, lambda *_: self._stop or self.deregister())
        signal.signal(signal.SIGINT, lambda *_: self._stop or self.deregister())
        if not self.register():
            sys.exit(1)
        Thread(target=self.heartbeat_loop, daemon=True).start()
        logger.info("Worker agent started for %s", self.worker_id)

    def increment_active(self) -> None:
        self.active_tasks += 1

    def decrement_active(self) -> None:
        self.active_tasks = max(0, self.active_tasks - 1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    api_url = os.getenv("API_URL", "http://fastapi:8000")
    worker_id = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
    agent = WorkerAgent(api_url=api_url, worker_id=worker_id)
    agent.start()

    # Block main thread
    while True:
        time.sleep(60)
