"""
Candidate Manager
Manages candidate profiles, interview history, and scoring
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Text, cast, or_, select

from database.db import SessionLocal
from database.models import Candidate, InterviewSession
from orchestrator.time_utils import utcnow

logger = logging.getLogger(__name__)


class CandidateManager:
    """Manages candidate profiles, history, and scoring."""

    def __init__(self):
        pass

    def create_candidate(
        self,
        name: str,
        email: str,
        resume_text: str | None = None,
        skills: list[str] | None = None,
    ) -> dict[str, Any]:

        candidate_id = f"candidate_{uuid.uuid4().hex[:12]}"
        now = utcnow()
        db = SessionLocal()

        try:
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
            db.commit()

            return {
                "candidate_id": candidate_id,
                "name": candidate.name,
                "email": candidate.email,
                "resume_text": resume_text,
                "skills": skills or [],
                "interview_history": [],
                "avg_score": None,
                "total_interviews": 0,
                "created_at": now.isoformat(),
            }

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_candidate(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:

        db = SessionLocal()

        try:
            c = db.execute(
                select(Candidate).where(Candidate.candidate_id == candidate_id)
            ).scalar_one_or_none()

            if not c:
                return None

            return {
                "candidate_id": c.candidate_id,
                "name": c.name,
                "email": c.email,
                "resume_text": c.resume_text,
                "skills": c.skills or [],
                "interview_history": c.interview_history or [],
                "avg_score": c.avg_score,
                "total_interviews": c.total_interviews,
                "created_at": (c.created_at.isoformat() if c.created_at else None),
                "updated_at": (c.updated_at.isoformat() if c.updated_at else None),
            }

        finally:
            db.close()

    def list_candidates(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        skill: str | None = None,
        position: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:

        db = SessionLocal()

        try:

            query = select(Candidate)

            if search and search.strip():
                value = search.strip()

                query = query.where(
                    or_(
                        Candidate.name.ilike(f"%{value}%"),
                        Candidate.email.ilike(f"%{value}%"),
                    )
                )

            if skill and skill.strip():

                query = query.where(
                    cast(Candidate.skills, Text).ilike(f"%{skill.strip()}%")
                )
            # Position filter
            if position and position.strip():
                query = query.where(
                    Candidate.interview_sessions.any(
                        InterviewSession.position.ilike(f"%{position.strip()}%")
                    )
                )

            # Date range filter
            if date_from:
                start_date = datetime.fromisoformat(date_from)
                query = query.where(Candidate.created_at >= start_date)

            if date_to:
                end_date = datetime.fromisoformat(date_to) + timedelta(days=1)
                query = query.where(Candidate.created_at < end_date)

            rows = (
                db.execute(
                    query.order_by(Candidate.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
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

        except Exception as e:
            logger.error(f"Error listing candidates: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error listing candidates",
            )

        finally:
            db.close()

    def update_candidate_score(
        self,
        candidate_id: str,
        session_id: str,
        score: float,
    ) -> bool:

        db = SessionLocal()

        try:
            c = db.execute(
                select(Candidate).where(Candidate.candidate_id == candidate_id)
            ).scalar_one_or_none()

            if not c:
                return False

            history = list(c.interview_history or [])

            history.append(
                {
                    "session_id": session_id,
                    "score": score,
                    "completed_at": utcnow().isoformat(),
                }
            )

            total = c.total_interviews + 1

            if c.avg_score is None:
                c.avg_score = score
            else:
                c.avg_score = ((c.avg_score * c.total_interviews) + score) / total

            c.interview_history = history
            c.total_interviews = total
            c.updated_at = utcnow()

            db.commit()
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating candidate score: {e}")
            return False

        finally:
            db.close()

    def get_interview_history(
        self,
        candidate_id: str,
    ) -> list[dict[str, Any]]:

        db = SessionLocal()

        try:
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
                    "session_id": r.session_id,
                    "status": r.status,
                    "overall_score": r.overall_score,
                    "risk_score": r.risk_score,
                    "start_time": (r.start_time.isoformat() if r.start_time else None),
                    "end_time": (r.end_time.isoformat() if r.end_time else None),
                    "created_at": (r.created_at.isoformat() if r.created_at else None),
                }
                for r in rows
            ]

        finally:
            db.close()


candidate_manager = CandidateManager()
