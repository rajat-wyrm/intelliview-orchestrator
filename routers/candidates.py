"""Candidate profile routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db

logger = logging.getLogger(__name__)


class CreateCandidateRequest(BaseModel):
    """Request model for creating a candidate profile"""

    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1, max_length=255)
    resume_text: str | None = None
    skills: list[str] | None = None


class BulkCandidateItem(BaseModel):
    """A single candidate row within a bulk import request.

    Note: `position` and `phone` are accepted from the frontend CSV import
    payload but are NOT persisted, since the Candidate model has no
    corresponding database columns. They are echoed back in the response
    only.
    """

    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1, max_length=255)
    position: str | None = None
    phone: str | None = None


class BulkCandidateRequest(BaseModel):
    """Request model for bulk candidate import"""

    candidates: list[BulkCandidateItem] = Field(min_length=1)


class CandidateStatsResponse(BaseModel):
    """Stats aggregation response for candidate dashboard"""

    total_candidates: int = Field(ge=0, description="Total number of candidates")
    pending_review: int = Field(
        ge=0, description="Candidates with active/pending interview sessions"
    )
    completed: int = Field(
        ge=0, description="Candidates with at least one completed session"
    )
    active_now: int = Field(
        ge=0, description="Total active interview sessions across all candidates"
    )


def create_candidate_routes(candidate_manager) -> APIRouter:
    """Create candidate profile routes.

    Args:
        candidate_manager: CandidateManager instance

    Returns:
        APIRouter with candidate routes
    """

    router = APIRouter()

    @router.get("/candidates/stats")
    async def get_candidate_stats(
        session_db: Session = Depends(get_db),
    ) -> CandidateStatsResponse:
        """Get aggregated statistics for the candidate dashboard.

        Returns:
            CandidateStatsResponse with counts for total_candidates, pending_review,
            completed, and active_now. All fields are guaranteed to be non-negative integers.
            Returns 0 for all counts on empty database.
        """
        try:
            candidates = candidate_manager.list_candidates(limit=10000)

            total_candidates = len(candidates)

            # Count candidates with active sessions (pending_review)
            pending_review = sum(
                1 for c in candidates if c.get("active_sessions", 0) > 0
            )

            # Count candidates with at least one completed session
            completed = sum(1 for c in candidates if c.get("completed_sessions", 0) > 0)

            # Sum all active sessions across all candidates
            active_now = sum(c.get("active_sessions", 0) for c in candidates)

            return CandidateStatsResponse(
                total_candidates=total_candidates,
                pending_review=pending_review,
                completed=completed,
                active_now=active_now,
            )
        except Exception as e:
            logger.error(f"Error fetching candidate stats: {e!s}")
            raise HTTPException(
                status_code=500, detail="Error fetching candidate stats"
            )

    @router.get("/candidates")
    async def list_candidates(
        limit: int = 100,
        session_db: Session = Depends(get_db),
    ):
        """List all candidates"""
        try:
            candidates = candidate_manager.list_candidates(limit=limit)
            return {"count": len(candidates), "candidates": candidates}
        except Exception as e:
            logger.error(f"Error listing candidates: {e!s}")
            raise HTTPException(status_code=500, detail="Error listing candidates")

    @router.post("/candidates")
    async def create_candidate(
        request: CreateCandidateRequest,
        session_db: Session = Depends(get_db),
    ):
        """Create a new candidate profile"""
        try:
            candidate = candidate_manager.create_candidate(
                name=request.name,
                email=request.email,
                resume_text=request.resume_text,
                skills=request.skills,
            )
            return candidate
        except Exception as e:
            logger.error(f"Error creating candidate: {e!s}")
            raise HTTPException(status_code=500, detail="Error creating candidate")

    @router.post("/candidates/bulk")
    async def bulk_create_candidates(
        request: BulkCandidateRequest,
        session_db: Session = Depends(get_db),
    ):
        """Bulk-create candidate profiles from a CSV import.

        Each candidate is processed independently: a failure on one row
        does not prevent the others from being created. `position` and
        `phone` are accepted but not persisted, since the Candidate model
        has no corresponding columns.
        """
        created = []
        errors = []

        for index, item in enumerate(request.candidates):
            try:
                candidate = candidate_manager.create_candidate(
                    name=item.name,
                    email=item.email,
                )
                # Echo back the non-persisted fields for frontend visibility only.
                candidate["position"] = item.position
                candidate["phone"] = item.phone
                created.append(candidate)
            except Exception as e:
                logger.error(f"Error creating candidate at row {index}: {e!s}")
                errors.append(
                    {
                        "index": index,
                        "email": item.email,
                        "error": str(e),
                    }
                )

        return {
            "imported": len(created),
            "failed": len(errors),
            "candidates": created,
            "errors": errors,
        }

    @router.get("/candidates/{candidate_id}")
    async def get_candidate(
        candidate_id: str,
        session_db: Session = Depends(get_db),
    ):
        """Get candidate details by ID"""
        try:
            candidate = candidate_manager.get_candidate(candidate_id)
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")
            return candidate
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching candidate: {e!s}")
            raise HTTPException(status_code=500, detail="Error fetching candidate")

    @router.get("/candidates/{candidate_id}/history")
    async def get_candidate_history(
        candidate_id: str,
        session_db: Session = Depends(get_db),
    ):
        """Get candidate interview history"""
        try:
            candidate = candidate_manager.get_candidate(candidate_id)
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")
            history = candidate_manager.get_interview_history(candidate_id)
            return {"candidate_id": candidate_id, "history": history}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching candidate history: {e!s}")
            raise HTTPException(
                status_code=500, detail="Error fetching candidate history"
            )

    return router
