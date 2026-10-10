"""Question bank routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db

logger = logging.getLogger(__name__)


class AddQuestionRequest(BaseModel):
    """Request model for adding a question to the bank"""

    text: str = Field(min_length=1, max_length=1000)
    category: str
    difficulty: str = "medium"
    tags: list[str] | None = None


def create_question_routes(question_bank) -> APIRouter:
    """Create question bank routes.

    Args:
        question_bank: QuestionBank instance

    Returns:
        APIRouter with question routes
    """

    router = APIRouter()

    @router.get("/questions")
    async def list_questions(
        category: str | None = None,
        difficulty: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        session_db: Session = Depends(get_db),
    ):
        """List questions with optional category/difficulty filter"""
        try:
            questions = question_bank.get_questions(
                category=category, difficulty=difficulty, limit=limit
            )
            return {"count": len(questions), "questions": questions}
        except Exception as e:
            logger.error(f"Error listing questions: {e!s}")
            raise HTTPException(status_code=500, detail="Error listing questions")

    @router.post("/questions")
    async def add_question(
        request: AddQuestionRequest,
        session_db: Session = Depends(get_db),
    ):
        """Add a new question to the bank"""
        try:
            question = question_bank.add_question(
                text=request.text,
                category=request.category,
                difficulty=request.difficulty,
                tags=request.tags,
            )
            return question
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error adding question: {e!s}")
            raise HTTPException(status_code=500, detail="Error adding question")

    return router
