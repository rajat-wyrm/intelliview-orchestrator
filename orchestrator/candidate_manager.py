"""
Candidate Manager
Manages candidate profiles, interview history, and scoring
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select

from database.db import SessionLocal
from database.models import Candidate, InterviewSession
from orchestrator.time_utils import utcnow

logger = logging.getLogger(__name__)


class CandidateManager:
    """Manages candidate profiles, history, and scoring"""

    def __init__(self):
        pass

    def create_candidate(
        self,
        name: str,
        email: str,
        resume_text: str | None = None,
        skills: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new candidate profile"""
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

            logger.info(f"Created candidate {candidate_id}: {name}")
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
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating candidate: {e}")
            raise
        finally:
            db.close()

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        """Get candidate by ID"""
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
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
        finally:
            db.close()

    def list_candidates(self, limit: int = 100) -> list[dict[str, Any]]:
        """List all candidates"""
        db = SessionLocal()
        try:
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
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in rows
            ]
        finally:
            db.close()

    def update_candidate_score(self, candidate_id: str, session_id: str, score: float) -> bool:
        """Update candidate's running average score after an interview"""
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

    def get_interview_history(self, candidate_id: str) -> list[dict[str, Any]]:
        """Get interview history for a candidate"""
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
                    "start_time": r.start_time.isoformat() if r.start_time else None,
                    "end_time": r.end_time.isoformat() if r.end_time else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        finally:
            db.close()


candidate_manager = CandidateManager()
