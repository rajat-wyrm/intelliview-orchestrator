#!/usr/bin/env python3
"""
Seed the database with a realistic demo dataset so the UI has something
to show on first boot.

Run with:
    python scripts/seed.py            # idempotent: only inserts missing rows
    python scripts/seed.py --reset    # wipe & reseed
    python scripts/seed.py --keepalive  # keep demo workers alive in foreground
    AUTO_SEED_DEMO_DATA=true           # automatic on app startup

What gets seeded:
    - 3 workers (mix of healthy / loaded / idle)
    - 12 completed sessions with varied risk scores
    - 4 active sessions spread across the lifecycle
    - 2 failed sessions in the DLQ
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make the project root importable when run as a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import get_settings  # noqa: E402
from database.db import Base, engine, get_db_session  # noqa: E402
from database.models import InterviewSession  # noqa: E402
from orchestrator.worker_registry import WorkerRegistry  # noqa: E402

WORKER_FIXTURES = [
    {"worker_id": "worker-alpha", "capacity": 4, "active_tasks": 2, "status": "healthy"},
    {"worker_id": "worker-beta", "capacity": 8, "active_tasks": 1, "status": "healthy"},
    {"worker_id": "worker-gamma", "capacity": 2, "active_tasks": 0, "status": "healthy"},
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def seed_workers() -> None:
    """Register demo workers. Idempotent: re-registers only new ones."""
    registry = WorkerRegistry()
    for spec in WORKER_FIXTURES:
        existing = registry.get_worker(spec["worker_id"])
        if existing is None:
            registry.register_worker(spec["worker_id"], capacity=spec["capacity"])
            print(f"  + worker {spec['worker_id']} (capacity={spec['capacity']})")
        registry.heartbeat(spec["worker_id"], active_tasks=spec["active_tasks"])


def seed_sessions(reset: bool = False) -> None:
    """Insert a realistic mix of completed, active, and failed sessions."""
    with get_db_session() as db:
        Base.metadata.create_all(bind=engine)

        if reset:
            deleted = db.query(InterviewSession).delete()
            print(f"  - deleted {deleted} existing sessions")

        existing_ids = {row.session_id for row in db.query(InterviewSession.session_id).all()}
        if existing_ids:
            print(f"  = {len(existing_ids)} sessions already present; skipping insert")
            return

        rng = random.Random(42)
        now = _now()
        rows: list[InterviewSession] = []

        # 12 completed sessions, varied risk scores.
        for i in range(12):
            duration_minutes = rng.randint(8, 35)
            risk = round(rng.uniform(0.05, 0.95), 3)
            end = now - timedelta(minutes=rng.randint(5, 240))
            rows.append(
                InterviewSession(
                    session_id=f"seed-done-{i:03d}",
                    candidate_id=f"cand-{rng.randint(1000, 9999)}",
                    status="COMPLETED",
                    risk_score=risk,
                    assigned_node=rng.choice([w["worker_id"] for w in WORKER_FIXTURES]),
                    start_time=end - timedelta(minutes=duration_minutes),
                    end_time=end,
                    created_at=end - timedelta(minutes=duration_minutes + 2),
                    updated_at=end,
                    video_analysis={
                        "candidate_name": rng.choice(
                            ["Ava Patel", "Liam Chen", "Noah Kim", "Mia Rossi", "Yuki Sato", "Omar Hassan"]
                        ),
                        "position": rng.choice(
                            ["Senior Backend Engineer", "ML Engineer", "Frontend Engineer", "DevOps Lead"]
                        ),
                        "face_detected": True,
                        "multiple_persons_detected": False,
                        "risk_score": round(risk * 0.7, 3),
                    },
                    audio_analysis={
                        "text": "transcribed sample",
                        "background_voices_detected": False,
                        "risk_score": round(risk * 0.5, 3),
                    },
                    evaluation_analysis={
                        "overall_quality_score": round((1 - risk) * 100, 2),
                        "risk_score": round(risk * 0.8, 3),
                    },
                )
            )

        # 4 active sessions spread across the pipeline.
        active_states = ["QUEUED", "VIDEO_PROCESSING", "AUDIO_PROCESSING", "EVALUATING"]
        for i, status in enumerate(active_states):
            rows.append(
                InterviewSession(
                    session_id=f"seed-live-{i:03d}",
                    candidate_id=f"cand-{rng.randint(1000, 9999)}",
                    status=status,
                    assigned_node=rng.choice([w["worker_id"] for w in WORKER_FIXTURES]),
                    start_time=now - timedelta(seconds=rng.randint(20, 600)) if status != "QUEUED" else None,
                    end_time=None,
                    created_at=now - timedelta(seconds=rng.randint(20, 1200)),
                    updated_at=now - timedelta(seconds=rng.randint(5, 60)),
                )
            )

        # 2 failed sessions.
        for i in range(2):
            rows.append(
                InterviewSession(
                    session_id=f"seed-fail-{i:03d}",
                    candidate_id=f"cand-{rng.randint(1000, 9999)}",
                    status="FAILED",
                    assigned_node="worker-alpha",
                    start_time=now - timedelta(minutes=rng.randint(30, 90)),
                    end_time=now - timedelta(minutes=rng.randint(5, 20)),
                    created_at=now - timedelta(minutes=rng.randint(35, 100)),
                    updated_at=now - timedelta(minutes=rng.randint(5, 20)),
                )
            )

        db.add_all(rows)
        print(f"  + inserted {len(rows)} demo sessions")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the demo dataset.")
    parser.add_argument("--reset", action="store_true", help="wipe existing rows first")
    parser.add_argument(
        "--keepalive",
        action="store_true",
        help="after seeding, periodically heartbeat the demo workers so they stay healthy (blocks)",
    )
    args = parser.parse_args()

    print(f"Seeding demo data into {get_settings().database_url} …")
    seed_workers()
    seed_sessions(reset=args.reset)
    print("Done.")

    if args.keepalive:
        print("Keeping demo workers alive (Ctrl-C to exit) …")
        registry = WorkerRegistry()
        while True:
            for spec in WORKER_FIXTURES:
                registry.heartbeat(spec["worker_id"], active_tasks=spec["active_tasks"])
            time.sleep(15)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
