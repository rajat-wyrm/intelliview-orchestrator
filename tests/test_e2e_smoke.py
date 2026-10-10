"""
End-to-end smoke tests against a running stack.

Run the stack first:
    docker compose up -d
    pip install -r requirements.txt
    pytest tests/test_e2e_smoke.py -v

Set API_BASE_URL to override the default http://localhost:8000.
"""

import time
import uuid

import httpx
import pytest


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


def _wait_for_worker(base_url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base_url}/system-health", timeout=2.0)
            if r.status_code == 200:
                body = r.json()
                if (
                    body.get("components", {})
                    .get("workers", {})
                    .get("healthy_workers", 0)
                    >= 1
                ):
                    return
        except Exception as e:
            last_err = e
        time.sleep(1.0)
    pytest.fail(f"Worker not ready at {base_url}: {last_err}")


@pytest.mark.e2e
def test_health(api_base_url):
    _wait_for_api(api_base_url)
    r = httpx.get(f"{api_base_url}/health", timeout=5.0)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "system running"
    assert body["timestamp"]  # non-null now


@pytest.mark.e2e
def test_start_interview_and_get_status(api_base_url, api_token):
    _wait_for_api(api_base_url)
    # The worker pool may take a few seconds to become available after startup.
    # Retry a few times and retain the successful response to avoid duplicate sessions.
    r = None
    for _ in range(5):
        r = httpx.post(
            f"{api_base_url}/start-interview",
            headers={"X-API-Token": api_token},
            json={"candidate_id": f"cand-{uuid.uuid4().hex[:8]}", "priority": "high"},
            timeout=30.0,
        )
        if r.status_code == 200:
            break
        time.sleep(3)

    if r is None or r.status_code != 200:
        # Fallback / final attempt if all retries failed
        r = httpx.post(
            f"{api_base_url}/start-interview",
            json={"candidate_id": f"cand-{uuid.uuid4().hex[:8]}", "priority": "high"},
            headers={"X-API-Token": api_token},
            timeout=30.0,
        )

    _wait_for_worker(api_base_url)

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


@pytest.mark.e2e
def test_system_health(api_base_url):
    _wait_for_api(api_base_url)
    r = httpx.get(f"{api_base_url}/system-health", timeout=5.0)
    assert r.status_code == 200
    body = r.json()
    assert "overall_status" in body
    assert "components" in body
    assert "redis" in body["components"]


@pytest.mark.e2e
def test_worker_register_requires_token(api_base_url, api_token):
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
        headers={"X-API-Token": api_token},
        timeout=5.0,
    )
    assert r.status_code == 200, r.text


@pytest.mark.e2e
def test_full_pipeline_completes(api_base_url, api_token):
    """End-to-end: start an interview, wait for the worker to process it."""
    _wait_for_api(api_base_url)
    r = None
    for _ in range(5):
        r = httpx.post(
            f"{api_base_url}/start-interview",
            headers={"X-API-Token": api_token},
            json={"candidate_id": f"e2e-{uuid.uuid4().hex[:8]}", "priority": "medium"},
            timeout=30.0,
        )
        if r.status_code == 200:
            break
        time.sleep(3)

    if r is None or r.status_code != 200:
        r = httpx.post(
            f"{api_base_url}/start-interview",
            json={"candidate_id": f"e2e-{uuid.uuid4().hex[:8]}", "priority": "medium"},
            headers={"X-API-Token": api_token},
            timeout=30.0,
        )

    _wait_for_worker(api_base_url)

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
