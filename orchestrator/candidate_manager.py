"""
Candidate Manager
Manages candidate profiles, interview history, and scoring.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select

from database.db import get_db_session
from database.models import Candidate, InterviewSession
from orchestrator.time_utils import utcnow

logger = logging.getLogger(__name__)


class CandidateManager:
    """Manages candidate profiles, history, and scoring."""

    def create_candidate(
        self,
        name: str,
        email: str,
        resume_text: str | None = None,
        skills: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new candidate profile."""

        candidate_id = f"candidate_{uuid.uuid4().hex[:12]}"
        now = utcnow()

        with get_db_session() as db:
            candidate = Candidate(
                candidate_id=candidate_id,
                name=name.strip(),
                email=email.strip().lower(),
                resume_text=resume_text,
                skills=skills or [],
                interview_history=[],
                avg_score=None,
                total_interviews=0,
                created_at=now,
                updated_at=now,
            )
            db.add(candidate)

        logger.info("Created candidate %s: %s", candidate_id, name)

        return {
            "candidate_id": candidate_id,
            "name": name.strip(),
            "email": email.strip().lower(),
            "resume_text": resume_text,
            "skills": skills or [],
            "interview_history": [],
            "avg_score": None,
            "total_interviews": 0,
            "created_at": now.isoformat(),
        }

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        """Get candidate by ID."""

        with get_db_session() as db:
            candidate = db.execute(
                select(Candidate).where(Candidate.candidate_id == candidate_id)
            ).scalar_one_or_none()

            if candidate is None:
                return None

            return {
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "email": candidate.email,
                "resume_text": candidate.resume_text,
                "skills": candidate.skills or [],
                "interview_history": candidate.interview_history or [],
                "avg_score": candidate.avg_score,
                "total_interviews": candidate.total_interviews,
                "created_at": (candidate.created_at.isoformat() if candidate.created_at else None),
                "updated_at": (candidate.updated_at.isoformat() if candidate.updated_at else None),
            }

    def list_candidates(self, limit: int = 100) -> list[dict[str, Any]]:
        """List all candidates."""

        with get_db_session() as db:
            rows = (
                db.execute(select(Candidate).order_by(Candidate.created_at.desc()).limit(limit))
                .scalars()
                .all()
            )

            return [
                {
                    "candidate_id": c.candidate_id,
                    "name": c.name,
                    "email": c.email,
                    "skills": c.skills or [],
                    "avg_score": c.avg_score,
                    "total_interviews": c.total_interviews,
                    "created_at": (c.created_at.isoformat() if c.created_at else None),
                }
                for c in rows
            ]

    def update_candidate_score(
        self,
        candidate_id: str,
        session_id: str,
        score: float,
    ) -> bool:
        """Update a candidate's running average score."""

        with get_db_session() as db:
            candidate = db.execute(
                select(Candidate).where(Candidate.candidate_id == candidate_id)
            ).scalar_one_or_none()

            if candidate is None:
                return False

            history = list(candidate.interview_history or [])
            history.append(
                {
                    "session_id": session_id,
                    "score": score,
                    "completed_at": utcnow().isoformat(),
                }
            )

            total = candidate.total_interviews + 1

            if candidate.avg_score is None:
                candidate.avg_score = score
            else:
                candidate.avg_score = (candidate.avg_score * candidate.total_interviews + score) / total

            candidate.interview_history = history
            candidate.total_interviews = total
            candidate.updated_at = utcnow()

            return True

    def get_interview_history(
        self,
        candidate_id: str,
    ) -> list[dict[str, Any]]:
        """Get interview history for a candidate."""

        with get_db_session() as db:
            rows = (
                db.execute(
                    select(InterviewSession)
                    .where(InterviewSession.candidate_id == candidate_id)
                    .order_by(InterviewSession.created_at.desc())
                )
                .scalars()
                .all()
            )

            return [
                {
                    "session_id": row.session_id,
                    "status": row.status,
                    "overall_score": row.overall_score,
                    "risk_score": row.risk_score,
                    "start_time": (row.start_time.isoformat() if row.start_time else None),
                    "end_time": (row.end_time.isoformat() if row.end_time else None),
                    "created_at": (row.created_at.isoformat() if row.created_at else None),
                }
                for row in rows
            ]


candidate_manager = CandidateManager()
