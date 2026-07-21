"""
Question Bank Module
Manages interview questions by category, difficulty, and usage statistics
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select

from database.db import get_db_session
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
            raise ValueError(
                f"Invalid category: {category}. Must be one of: {self.CATEGORIES}"
            )

        if difficulty not in self.DIFFICULTIES:
            raise ValueError(
                f"Invalid difficulty: {difficulty}. Must be one of: {self.DIFFICULTIES}"
            )

        question_id = f"q_{uuid.uuid4().hex[:12]}"
        now = utcnow()

        with get_db_session() as db:
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

    def get_questions(
        self,
        category: str | None = None,
        difficulty: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List questions with optional filters"""

        with get_db_session() as db:
            stmt = select(Question)

            if category:
                stmt = stmt.where(
                    Question.category == category.strip().lower()
                )

            if difficulty:
                stmt = stmt.where(
                    Question.difficulty == difficulty.strip().lower()
                )

            stmt = stmt.order_by(
                Question.created_at.desc()
            ).limit(limit)

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
                    "created_at": (
                        r.created_at.isoformat()
                        if r.created_at
                        else None
                    ),
                }
                for r in rows
            ]

    def get_question(
        self,
        question_id: str,
    ) -> dict[str, Any] | None:
        """Get a single question by ID"""

        with get_db_session() as db:
            question = db.execute(
                select(Question).where(
                    Question.question_id == question_id
                )
            ).scalar_one_or_none()

            if not question:
                return None

            return {
                "question_id": question.question_id,
                "text": question.text,
                "category": question.category,
                "difficulty": question.difficulty,
                "tags": question.tags or [],
                "usage_count": question.usage_count,
                "avg_score": question.avg_score,
                "created_at": (
                    question.created_at.isoformat()
                    if question.created_at
                    else None
                ),
            }

    def get_next_question(
        self,
        category: str | None = None,
        exclude_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Get next question, preferring less-used ones"""

        exclude_ids = exclude_ids or []

        with get_db_session() as db:
            stmt = select(Question)

            if category:
                stmt = stmt.where(
                    Question.category == category.strip().lower()
                )

            stmt = stmt.order_by(
                Question.usage_count.asc(),
                Question.created_at.desc(),
            )

            rows = db.execute(stmt).scalars().all()

            for question in rows:
                if question.question_id not in exclude_ids:
                    return {
                        "question_id": question.question_id,
                        "text": question.text,
                        "category": question.category,
                        "difficulty": question.difficulty,
                        "tags": question.tags or [],
                        "usage_count": question.usage_count,
                    }

            return None

    def record_usage(
        self,
        question_id: str,
        score: float | None = None,
    ) -> bool:
        """Increment usage count and update average score"""

        with get_db_session() as db:
            question = db.execute(
                select(Question).where(
                    Question.question_id == question_id
                )
            ).scalar_one_or_none()

            if not question:
                return False

            question.usage_count = (question.usage_count or 0) + 1

            if score is not None:
                if question.avg_score is None:
                    question.avg_score = score
                else:
                    count = question.usage_count
                    question.avg_score = (
                        (question.avg_score * (count - 1)) + score
                    ) / count

            question.updated_at = utcnow()

            return True


question_bank = QuestionBank()