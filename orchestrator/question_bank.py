"""
Question Bank Module
Manages interview questions by category, difficulty, and usage statistics
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select

from database.db import SessionLocal
from database.models import Question
from orchestrator.time_utils import utcnow

logger = logging.getLogger(__name__)


class QuestionBank:
    """Manages interview question storage, retrieval, and usage tracking"""

    CATEGORIES = ["technical", "behavioral", "situational"]
    DIFFICULTIES = ["easy", "medium", "hard"]

    def __init__(self):
        pass

    def add_question(
        self,
        text: str,
        category: str,
        difficulty: str = "medium",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a new question to the bank"""
        category = category.strip().lower()
        difficulty = difficulty.strip().lower()

        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category: {category}. Must be one of: {self.CATEGORIES}")
        if difficulty not in self.DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {difficulty}. Must be one of: {self.DIFFICULTIES}")

        question_id = f"q_{uuid.uuid4().hex[:12]}"
        now = utcnow()

        db = SessionLocal()
        try:
            question = Question(
                question_id=question_id,
                text=text,
                category=category,
                difficulty=difficulty,
                tags=tags or [],
                usage_count=0,
                avg_score=None,
                created_at=now,
                updated_at=now,
            )
            db.add(question)
            db.commit()

            logger.info(f"Added question {question_id} [{category}/{difficulty}]")
            return {
                "question_id": question_id,
                "text": text,
                "category": category,
                "difficulty": difficulty,
                "tags": tags or [],
                "usage_count": 0,
                "avg_score": None,
                "created_at": now.isoformat(),
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding question: {e}")
            raise
        finally:
            db.close()

    def get_questions(
        self,
        category: str | None = None,
        difficulty: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List questions with optional filters"""
        db = SessionLocal()
        try:
            stmt = select(Question)
            if category:
                stmt = stmt.where(Question.category == category.strip().lower())
            if difficulty:
                stmt = stmt.where(Question.difficulty == difficulty.strip().lower())
            stmt = stmt.order_by(Question.created_at.desc()).limit(limit)
            rows = db.execute(stmt).scalars().all()

            return [
                {
                    "question_id": r.question_id,
                    "text": r.text,
                    "category": r.category,
                    "difficulty": r.difficulty,
                    "tags": r.tags or [],
                    "usage_count": r.usage_count,
                    "avg_score": r.avg_score,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        finally:
            db.close()

    def get_question(self, question_id: str) -> dict[str, Any] | None:
        """Get a single question by ID"""
        db = SessionLocal()
        try:
            q = db.execute(select(Question).where(Question.question_id == question_id)).scalar_one_or_none()
            if not q:
                return None
            return {
                "question_id": q.question_id,
                "text": q.text,
                "category": q.category,
                "difficulty": q.difficulty,
                "tags": q.tags or [],
                "usage_count": q.usage_count,
                "avg_score": q.avg_score,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
        finally:
            db.close()

    def get_next_question(
        self,
        category: str | None = None,
        exclude_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Get next question, preferring less-used ones, optional category filter"""
        exclude_ids = exclude_ids or []
        db = SessionLocal()
        try:
            stmt = select(Question)
            if category:
                stmt = stmt.where(Question.category == category.strip().lower())
            stmt = stmt.order_by(Question.usage_count.asc(), Question.created_at.desc())
            rows = db.execute(stmt).scalars().all()

            for q in rows:
                if q.question_id not in exclude_ids:
                    return {
                        "question_id": q.question_id,
                        "text": q.text,
                        "category": q.category,
                        "difficulty": q.difficulty,
                        "tags": q.tags or [],
                        "usage_count": q.usage_count,
                    }
            return None
        finally:
            db.close()

    def record_usage(self, question_id: str, score: float | None = None) -> bool:
        """Increment usage count and optionally update running average score"""
        db = SessionLocal()
        try:
            q = db.execute(select(Question).where(Question.question_id == question_id)).scalar_one_or_none()
            if not q:
                return False

            q.usage_count = (q.usage_count or 0) + 1
            if score is not None:
                if q.avg_score is None:
                    q.avg_score = score
                else:
                    count = q.usage_count
                    q.avg_score = ((q.avg_score * (count - 1)) + score) / count
            q.updated_at = utcnow()
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error recording usage for {question_id}: {e}")
            return False
        finally:
            db.close()


question_bank = QuestionBank()
