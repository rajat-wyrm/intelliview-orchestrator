#!/usr/bin/env python3
"""
Seed the database with a realistic demo dataset so the UI has something
to show on first boot.

Run with:
    python scripts/seed.py
    python scripts/seed.py --reset
    python scripts/seed.py --keepalive

What gets seeded:
    - 3 workers (mix of healthy / loaded / idle)
    - 6 candidates
    - 6 interview schedules
    - 12 completed sessions with varied risk scores
    - 4 active sessions spread across the lifecycle
    - 2 failed sessions in the DLQ
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Make the project root importable when run as a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import get_settings
from database.db import Base, SessionLocal, engine
from database.models import Candidate, InterviewSchedule, InterviewSession
from orchestrator.worker_registry import WorkerRegistry

WORKER_FIXTURES = [
    {
        "worker_id": "worker-alpha",
        "capacity": 4,
        "active_tasks": 2,
        "status": "healthy",
    },
    {
        "worker_id": "worker-beta",
        "capacity": 8,
        "active_tasks": 1,
        "status": "healthy",
    },
    {
        "worker_id": "worker-gamma",
        "capacity": 2,
        "active_tasks": 0,
        "status": "healthy",
    },
]


CANDIDATE_FIXTURES = [
    {
        "candidate_id": "candidate-seed-001",
        "name": "Ava Patel",
        "email": "ava.patel@example.com",
        "resume_text": (
            "ML Engineer with experience in Python, machine learning, "
            "and data analysis."
        ),
        "skills": ["Python", "Machine Learning", "SQL"],
    },
    {
        "candidate_id": "candidate-seed-002",
        "name": "Vidhi Agrawal",
        "email": "vidhi.agrawal@example.com",
        "resume_text": (
            "Backend Engineer experienced in Python APIs, databases, "
            "and distributed systems."
        ),
        "skills": ["Python", "FastAPI", "PostgreSQL"],
    },
    {
        "candidate_id": "candidate-seed-003",
        "name": "Joy Khandelwal",
        "email": "joy.khandelwal@example.com",
        "resume_text": (
            "Frontend Developer with experience building modern " "web applications."
        ),
        "skills": ["JavaScript", "React", "Next.js"],
    },
    {
        "candidate_id": "candidate-seed-004",
        "name": "Ananya Singh",
        "email": "ananya.singh@example.com",
        "resume_text": (
            "Data Scientist with experience in statistics, Python, "
            "and predictive modeling."
        ),
        "skills": ["Python", "Statistics", "SQL"],
    },
    {
        "candidate_id": "candidate-seed-005",
        "name": "Rashi Singhal",
        "email": "rashi.singhal@example.com",
        "resume_text": (
            "Software Engineer experienced in backend development, "
            "REST APIs, and database systems."
        ),
        "skills": ["Python", "REST APIs", "PostgreSQL"],
    },
    {
        "candidate_id": "candidate-seed-006",
        "name": "Neha Gupta",
        "email": "neha.gupta@example.com",
        "resume_text": (
            "DevOps Engineer experienced in cloud infrastructure, "
            "automation, and CI/CD pipelines."
        ),
        "skills": ["AWS", "Docker", "CI/CD"],
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def seed_workers() -> None:
    """Register demo workers. Idempotent: re-registers only new ones."""
    registry = WorkerRegistry()

    for spec in WORKER_FIXTURES:
        existing = registry.get_worker(spec["worker_id"])

        if existing is None:
            registry.register_worker(
                spec["worker_id"],
                capacity=spec["capacity"],
            )
            print(f"  + worker {spec['worker_id']} " f"(capacity={spec['capacity']})")

        registry.heartbeat(
            spec["worker_id"],
            active_tasks=spec["active_tasks"],
        )


def seed_candidates(reset: bool = False) -> None:
    """Insert realistic demo candidates."""
    db = SessionLocal()

    try:
        Base.metadata.create_all(bind=engine)

        candidate_ids = {candidate["candidate_id"] for candidate in CANDIDATE_FIXTURES}

        if reset:
            deleted = (
                db.query(Candidate)
                .filter(Candidate.candidate_id.in_(candidate_ids))
                .delete(synchronize_session=False)
            )
            db.commit()

            print(f"  - deleted {deleted} existing demo candidates")

        existing_ids = {
            row.candidate_id
            for row in (
                db.query(Candidate.candidate_id)
                .filter(Candidate.candidate_id.in_(candidate_ids))
                .all()
            )
        }

        rows = []

        for spec in CANDIDATE_FIXTURES:
            if spec["candidate_id"] in existing_ids:
                continue

            rows.append(
                Candidate(
                    candidate_id=spec["candidate_id"],
                    name=spec["name"],
                    email=spec["email"].lower(),
                    resume_text=spec["resume_text"],
                    skills=spec["skills"],
                    interview_history=[],
                    avg_score=None,
                    total_interviews=0,
                )
            )

        if rows:
            db.add_all(rows)
            db.commit()
            print(f"  + inserted {len(rows)} demo candidates")
        else:
            print("  = demo candidates already present; " "skipping insert")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def seed_schedules(reset: bool = False) -> None:
    """Insert realistic interview schedules for seeded candidates."""
    db = SessionLocal()

    try:
        Base.metadata.create_all(bind=engine)

        candidate_ids = [candidate["candidate_id"] for candidate in CANDIDATE_FIXTURES]

        if reset:
            deleted = (
                db.query(InterviewSchedule)
                .filter(InterviewSchedule.candidate_id.in_(candidate_ids))
                .delete(synchronize_session=False)
            )
            db.commit()

            print(f"  - deleted {deleted} existing demo schedules")

        existing_candidate_ids = {
            row.candidate_id
            for row in (
                db.query(InterviewSchedule.candidate_id)
                .filter(InterviewSchedule.candidate_id.in_(candidate_ids))
                .all()
            )
        }

        now = _now()
        rows = []

        for index, candidate_id in enumerate(candidate_ids):
            if candidate_id in existing_candidate_ids:
                continue

            scheduled_time = now + timedelta(
                days=index + 1,
                hours=10,
            )

            rows.append(
                InterviewSchedule(
                    candidate_id=candidate_id,
                    interviewer_id=f"interviewer-{(index % 3) + 1:03d}",
                    scheduled_at=scheduled_time,
                    status="scheduled",
                    notes="Demo interview schedule",
                )
            )

        if rows:
            db.add_all(rows)
            db.commit()
            print(f"  + inserted {len(rows)} demo schedules")
        else:
            print("  = demo schedules already present; " "skipping insert")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def seed_sessions(reset: bool = False) -> None:
    """Insert a realistic mix of completed, active, and failed sessions."""
    db = SessionLocal()

    try:
        Base.metadata.create_all(bind=engine)

        if reset:
            deleted = db.query(InterviewSession).delete()
            db.commit()
            print(f"  - deleted {deleted} existing sessions")

        existing_ids = {
            row.session_id for row in db.query(InterviewSession.session_id).all()
        }

        if existing_ids:
            print(
                f"  = {len(existing_ids)} sessions already present; " "skipping insert"
            )
            return

        rng = random.Random(42)
        now = _now()

        candidate_ids = [candidate["candidate_id"] for candidate in CANDIDATE_FIXTURES]

        rows: list[InterviewSession] = []

        # 12 completed sessions, varied risk scores.
        for i in range(12):
            duration_minutes = rng.randint(8, 35)
            risk = round(rng.uniform(0.05, 0.95), 3)

            end = now - timedelta(minutes=rng.randint(5, 240))

            candidate_index = i % len(candidate_ids)
            candidate_id = candidate_ids[candidate_index]

            rows.append(
                InterviewSession(
                    session_id=f"seed-done-{i:03d}",
                    candidate_id=candidate_id,
                    status="COMPLETED",
                    risk_score=risk,
                    assigned_node=rng.choice(
                        [worker["worker_id"] for worker in WORKER_FIXTURES]
                    ),
                    start_time=end - timedelta(minutes=duration_minutes),
                    end_time=end,
                    created_at=end - timedelta(minutes=duration_minutes + 2),
                    updated_at=end,
                    video_analysis={
                        "candidate_name": CANDIDATE_FIXTURES[candidate_index]["name"],
                        "position": rng.choice(
                            [
                                "Senior Backend Engineer",
                                "ML Engineer",
                                "Frontend Engineer",
                                "DevOps Lead",
                            ]
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
                        "overall_quality_score": round(
                            (1 - risk) * 100,
                            2,
                        ),
                        "risk_score": round(risk * 0.8, 3),
                    },
                )
            )

        # 4 active sessions spread across the pipeline.
        active_states = [
            "QUEUED",
            "VIDEO_PROCESSING",
            "AUDIO_PROCESSING",
            "EVALUATING",
        ]

        for i, status in enumerate(active_states):
            candidate_id = candidate_ids[(i + 2) % len(candidate_ids)]

            rows.append(
                InterviewSession(
                    session_id=f"seed-live-{i:03d}",
                    candidate_id=candidate_id,
                    status=status,
                    assigned_node=rng.choice(
                        [worker["worker_id"] for worker in WORKER_FIXTURES]
                    ),
                    start_time=(
                        now - timedelta(seconds=rng.randint(20, 600))
                        if status != "QUEUED"
                        else None
                    ),
                    end_time=None,
                    created_at=now - timedelta(seconds=rng.randint(20, 1200)),
                    updated_at=now - timedelta(seconds=rng.randint(5, 60)),
                )
            )

        # 2 failed sessions.
        for i in range(2):
            candidate_id = candidate_ids[(i + 4) % len(candidate_ids)]

            rows.append(
                InterviewSession(
                    session_id=f"seed-fail-{i:03d}",
                    candidate_id=candidate_id,
                    status="FAILED",
                    assigned_node="worker-alpha",
                    start_time=now - timedelta(minutes=rng.randint(30, 90)),
                    end_time=now - timedelta(minutes=rng.randint(5, 20)),
                    created_at=now - timedelta(minutes=rng.randint(35, 100)),
                    updated_at=now - timedelta(minutes=rng.randint(5, 20)),
                )
            )

        db.add_all(rows)
        db.commit()

        print(f"  + inserted {len(rows)} demo sessions")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the demo dataset.")

    parser.add_argument(
        "--reset",
        action="store_true",
        help="wipe existing demo rows first",
    )

    parser.add_argument(
        "--keepalive",
        action="store_true",
        help=(
            "after seeding, periodically heartbeat the demo workers "
            "so they stay healthy (blocks)"
        ),
    )

    args = parser.parse_args()

    print(f"Seeding demo data into " f"{get_settings().database_url} …")

    seed_workers()

    if args.reset:
        seed_sessions(reset=True)
        seed_schedules(reset=True)
        seed_candidates(reset=True)
    else:
        seed_candidates()
        seed_schedules()
        seed_sessions()

    print("Done.")

    if args.keepalive:
        print("Keeping demo workers alive " "(Ctrl-C to exit) …")

        registry = WorkerRegistry()

        while True:
            for spec in WORKER_FIXTURES:
                registry.heartbeat(
                    spec["worker_id"],
                    active_tasks=spec["active_tasks"],
                )

            time.sleep(15)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
