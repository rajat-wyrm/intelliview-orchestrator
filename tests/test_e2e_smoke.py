"""
End-to-end smoke tests against a running stack.

Run the stack first:
    docker compose up -d
    pip install -r requirements.txt
    pytest tests/test_e2e_smoke.py -v

Set API_BASE_URL to override the default http://localhost:8000.
"""

import os
import time
import uuid

import httpx
import pytest

API_HEADERS = {"X-API-Token": os.getenv("API_TOKEN", "dev-token-change-me")}

pytestmark = pytest.mark.e2e


def _wait_for_api(base_url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base_url}/health", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception as e:
            last_err = e
        time.sleep(1.0)
    pytest.fail(f"API not reachable at {base_url}: {last_err}")


def test_health(api_base_url):
    _wait_for_api(api_base_url)
    r = httpx.get(f"{api_base_url}/health", timeout=5.0)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "system running"
    assert body["timestamp"]  # non-null now


def test_start_interview_and_get_status(api_base_url):
    _wait_for_api(api_base_url)
    r = httpx.post(
        f"{api_base_url}/start-interview",
        headers=API_HEADERS,
        json={"candidate_id": f"cand-{uuid.uuid4().hex[:8]}", "priority": "high"},
        timeout=10.0,
    )
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]
    assert session_id.startswith("session_")

    r = httpx.get(f"{api_base_url}/session-status/{session_id}", timeout=5.0)
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == session_id
    assert body["status"] in {
        "CREATED",
        "QUEUED",
        "PROCESSING",
        "VIDEO_PROCESSING",
        "AUDIO_PROCESSING",
        "EVALUATING",
        "COMPLETED",
        "FAILED",
    }


def test_system_health(api_base_url):
    _wait_for_api(api_base_url)
    r = httpx.get(f"{api_base_url}/system-health", timeout=5.0)
    assert r.status_code == 200
    body = r.json()
    assert "overall_status" in body
    assert "components" in body
    assert "redis" in body["components"]


def test_worker_register_requires_token(api_base_url):
    _wait_for_api(api_base_url)
    # Without token — should be 401
    r = httpx.post(
        f"{api_base_url}/register-worker",
        json={"worker_id": "test-w", "capacity": 2},
        timeout=5.0,
    )
    assert r.status_code == 401
    # With token — should succeed
    r = httpx.post(
        f"{api_base_url}/register-worker",
        json={"worker_id": "test-w", "capacity": 2},
        headers=API_HEADERS,
        timeout=5.0,
    )
    assert r.status_code == 200, r.text


def test_full_pipeline_completes(api_base_url):
    """End-to-end: start an interview, wait for the worker to process it."""
    _wait_for_api(api_base_url)
    r = httpx.post(
        f"{api_base_url}/start-interview",
        headers=API_HEADERS,
        json={"candidate_id": f"e2e-{uuid.uuid4().hex[:8]}", "priority": "medium"},
        timeout=10.0,
    )
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    # Poll for terminal state (worker is a stub pipeline so this is fast)
    deadline = time.time() + 60
    last = None
    while time.time() < deadline:
        r = httpx.get(f"{api_base_url}/session-status/{session_id}", timeout=5.0)
        assert r.status_code == 200
        last = r.json()
        if last["status"] in {"COMPLETED", "FAILED"}:
            break
        time.sleep(1.0)
    assert last is not None
    assert last["status"] in {
        "COMPLETED",
        "FAILED",
    }, f"Session stuck in {last['status']}"


def test_candidate_lifecycle(api_base_url):
    """End-to-end: create a candidate, then fetch it back by id, then list it."""
    _wait_for_api(api_base_url)
    email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
    r = httpx.post(
        f"{api_base_url}/candidates",
        json={
            "name": "E2E Test Candidate",
            "email": email,
            "skills": ["python", "testing"],
        },
        timeout=10.0,
    )
    assert r.status_code == 200, r.text
    candidate = r.json()
    candidate_id = candidate["candidate_id"]

    r = httpx.get(f"{api_base_url}/candidates/{candidate_id}", timeout=5.0)
    assert r.status_code == 200
    assert r.json()["candidate_id"] == candidate_id

    r = httpx.get(f"{api_base_url}/candidates/{candidate_id}/history", timeout=5.0)
    assert r.status_code == 200
    assert r.json()["candidate_id"] == candidate_id

    # A non-existent candidate should 404, not 500.
    r = httpx.get(f"{api_base_url}/candidates/does-not-exist", timeout=5.0)
    assert r.status_code == 404


def test_worker_lifecycle(api_base_url):
    """End-to-end: register a worker, send a heartbeat, see it listed, then deregister it."""
    _wait_for_api(api_base_url)
    worker_id = f"e2e-worker-{uuid.uuid4().hex[:8]}"
    headers = API_HEADERS

    r = httpx.post(
        f"{api_base_url}/register-worker",
        json={"worker_id": worker_id, "capacity": 2},
        headers=headers,
        timeout=5.0,
    )
    assert r.status_code == 200, r.text

    r = httpx.post(
        f"{api_base_url}/worker/heartbeat",
        json={"worker_id": worker_id, "active_tasks": 0},
        headers=headers,
        timeout=5.0,
    )
    assert r.status_code == 200, r.text

    r = httpx.get(f"{api_base_url}/workers", timeout=5.0)
    assert r.status_code == 200
    worker_ids = {w.get("worker_id") for w in r.json().get("workers", [])}
    assert worker_id in worker_ids

    r = httpx.delete(
        f"{api_base_url}/deregister-worker/{worker_id}",
        headers=headers,
        timeout=5.0,
    )
    assert r.status_code == 200, r.text


def test_dead_letter_queue_reachable(api_base_url):
    """The dead letter queue endpoint should always respond, even when empty."""
    _wait_for_api(api_base_url)
    r = httpx.get(f"{api_base_url}/dead-letter-queue", timeout=5.0)
    assert r.status_code == 200
    body = r.json()
    assert "dead_letter_queue" in body
    assert isinstance(body["dead_letter_queue"], list)
