#!/usr/bin/env python3
"""End-to-end smoke that hits every backend endpoint and every frontend page.

Exits 0 only if every check passes. Prints a single PASS/FAIL line per check.

Run while the stack is up:
    python scripts/audit_e2e.py
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

API = "http://localhost:8000"
WEB = "http://localhost:3000"
TOKEN = "dev-token-change-me"

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
results: list[tuple[str, bool, str]] = []


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: Any = None,
    timeout: float = 10.0,
) -> tuple[int, dict[str, str], Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                payload = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                payload = raw.decode("utf-8", errors="replace")
            return r.status, dict(r.headers), payload
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = raw.decode("utf-8", errors="replace")
        return e.code, dict(e.headers), payload


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    mark = PASS if ok else FAIL
    print(f"  [{mark}] {name}" + (f"  ({detail})" if detail else ""))


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ----------------------- Backend endpoints ----------------------------------


def backend() -> None:
    section("Backend — read endpoints")
    s, _, _ = request("GET", f"{API}/health")
    check("GET /health", s == 200, f"HTTP {s}")

    for path in [
        "/system-health",
        "/worker-health",
        "/worker-statistics",
        "/scheduling-status",
        "/load-status",
        "/workers",
        "/active-sessions",
        "/completed-sessions?limit=5",
        "/failed-sessions?limit=5",
        "/stuck-sessions",
        "/session-statistics",
        "/worker-distribution",
        "/high-risk-sessions?threshold=0.5",
        "/cache-stats",
        "/recovery-queue",
        "/failure-log?limit=3",
        "/dead-letter-queue?limit=3",
        "/fault-statistics",
        "/interviews?limit=5",
        "/dashboard",
    ]:
        s, _, _ = request("GET", f"{API}{path}")
        check(f"GET {path}", s == 200, f"HTTP {s}")

    section("Backend — auth gates (no token)")
    for method, path in [
        ("POST", "/start-interview"),
        ("POST", "/switch-strategy?strategy=ROUND_ROBIN"),
        ("POST", "/detect-failures"),
        ("POST", "/retry-session/abc"),
        ("DELETE", "/clear-cache"),
        ("POST", "/register-worker"),
        ("DELETE", "/deregister-worker/abc"),
        ("POST", "/worker/heartbeat"),
        ("POST", "/sync-to-database"),
    ]:
        s, _, _ = request(method, f"{API}{path}", body={})
        check(f"{method} {path} unauth", s == 401, f"HTTP {s}")

    section("Backend — auth gates (with token)")
    hdr = {"X-API-Token": TOKEN}

    s, _, body = request(
        "POST",
        f"{API}/start-interview",
        headers=hdr,
        body={"candidate_id": "cand-audit", "priority": "medium"},
    )
    sid = body["session_id"] if s == 200 and isinstance(body, dict) else None
    check("POST /start-interview (auth)", s == 200, f"HTTP {s}, sid={sid}")

    if sid:
        # Wait for processing
        for _ in range(10):
            s, _, body = request("GET", f"{API}/session-status/{sid}")
            if (
                s == 200
                and isinstance(body, dict)
                and body.get("status")
                in (
                    "COMPLETED",
                    "FAILED",
                )
            ):
                break
            time.sleep(1)
        check(
            "GET /session-status/{id}",
            s == 200,
            f"final status={body.get('status') if isinstance(body, dict) else 'n/a'}",
        )

    s, _, _ = request("POST", f"{API}/switch-strategy?strategy=QUEUE_BASED", headers=hdr)
    check("POST /switch-strategy", s == 200, f"HTTP {s}")

    s, _, _ = request("POST", f"{API}/switch-strategy?strategy=LEAST_LOADED", headers=hdr)
    check("POST /switch-strategy reset", s == 200, f"HTTP {s}")

    s, _, _ = request("POST", f"{API}/detect-failures", headers=hdr)
    check("POST /detect-failures", s == 200, f"HTTP {s}")

    s, _, _ = request("POST", f"{API}/sync-to-database", headers=hdr)
    check("POST /sync-to-database", s == 200, f"HTTP {s}")

    s, _, _ = request(
        "POST", f"{API}/register-worker", headers=hdr, body={"worker_id": "audit-w", "capacity": 2}
    )
    check("POST /register-worker", s == 200, f"HTTP {s}")

    s, _, _ = request(
        "POST", f"{API}/worker/heartbeat", headers=hdr, body={"worker_id": "audit-w", "active_tasks": 0}
    )
    check("POST /worker/heartbeat", s == 200, f"HTTP {s}")

    s, _, _ = request("DELETE", f"{API}/deregister-worker/audit-w", headers=hdr)
    check("DELETE /deregister-worker", s == 200, f"HTTP {s}")

    section("Backend — validation")
    # Missing candidate_id → 422
    s, _, _ = request("POST", f"{API}/start-interview", headers=hdr, body={"priority": "medium"})
    check("POST /start-interview missing candidate_id", s == 422, f"HTTP {s}")

    # Invalid candidate_id (bad chars) → 422
    s, _, _ = request(
        "POST",
        f"{API}/start-interview",
        headers=hdr,
        body={"candidate_id": "bad id with spaces!", "priority": "medium"},
    )
    check("POST /start-interview bad candidate_id", s == 422, f"HTTP {s}")

    # Invalid priority → 422
    s, _, _ = request(
        "POST",
        f"{API}/start-interview",
        headers=hdr,
        body={"candidate_id": "cand-x", "priority": "urgent"},
    )
    check("POST /start-interview bad priority", s == 422, f"HTTP {s}")

    # Invalid switch strategy → 400
    s, _, _ = request("POST", f"{API}/switch-strategy?strategy=NOPE", headers=hdr)
    check("POST /switch-strategy invalid strategy", s == 400, f"HTTP {s}")

    # Invalid worker_id heartbeat → 200 (returns success but is no-op for unknown)
    s, _, _ = request(
        "POST",
        f"{API}/worker/heartbeat",
        headers=hdr,
        body={"worker_id": "ghost", "active_tasks": 0},
    )
    check("POST /worker/heartbeat (unknown)", s == 200, f"HTTP {s}")


# ----------------------- Monitoring router ----------------------------------


def monitoring() -> None:
    section("Monitoring router (/monitoring/*)")
    for path in [
        "/metrics/system",
        "/metrics/workers",
        "/metrics/sessions",
        "/metrics/queue",
        "/metrics/failures",
        "/metrics/retries",
        "/metrics/performance",
    ]:
        s, _, _ = request("GET", f"{API}/monitoring{path}")
        check(f"GET /monitoring{path}", s == 200, f"HTTP {s}")

    s, _, _ = request("GET", f"{API}/monitoring/metrics/dashboard")
    check("GET /monitoring/metrics/dashboard", s == 200, f"HTTP {s}")


# ----------------------- Frontend pages --------------------------------------


def frontend() -> None:
    section("Frontend pages")
    for path in [
        "/",
        "/sessions",
        "/workers",
        "/analytics",
        "/settings",
        "/not-a-real-page",  # 404
    ]:
        s, _, _ = request("GET", f"{WEB}{path}")
        check(
            f"GET {path} ({'page' if path != '/not-a-real-page' else '404'})",
            s == 200 if path != "/not-a-real-page" else s == 404,
            f"HTTP {s}",
        )

    section("Frontend — static assets")
    for path in ["/_next/static/chunks/", "/favicon.ico"]:
        s, _, _ = request("GET", f"{WEB}{path}")
        check(f"GET {path}", s in (200, 404), f"HTTP {s}")


# ----------------------- WebSocket ------------------------------------------


def websocket() -> None:
    section("WebSocket /monitoring/ws/metrics")
    try:
        import websockets  # type: ignore
    except ImportError:
        check("WS libs available", False, "pip install websockets")
        return

    import asyncio

    async def run() -> None:
        url = f"ws://localhost:8000/monitoring/ws/metrics?token={TOKEN}"
        try:
            async with websockets.connect(url, open_timeout=5) as ws:
                msgs = []
                try:
                    for _ in range(3):
                        m = await asyncio.wait_for(ws.recv(), timeout=8)
                        msgs.append(json.loads(m))
                except asyncio.TimeoutError:
                    logger.debug("Timed out waiting for WebSocket messages")
                check("WS connects", True, "")
                check("WS receives hello", any(m.get("type") == "hello" for m in msgs), f"{len(msgs)} msgs")
                check(
                    "WS receives metrics", any(m.get("type") == "metrics" for m in msgs), f"{len(msgs)} msgs"
                )
        except Exception as exc:
            check("WS connects", False, str(exc))

    asyncio.run(run())


def main() -> int:
    backend()
    monitoring()
    websocket()
    frontend()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'=' * 60}\n{passed}/{total} checks passed")
    if passed != total:
        failed = [name for name, ok, _ in results if not ok]
        print("Failed checks:")
        for n in failed:
            print(f"  - {n}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
