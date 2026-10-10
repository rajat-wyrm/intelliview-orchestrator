"""Candidate profile routes."""

import logging
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db
from orchestrator.email_service import email_service

logger = logging.getLogger(__name__)


class CreateCandidateRequest(BaseModel):
    """Request model for creating a candidate profile"""

    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1, max_length=255)
    resume_text: str | None = None
    skills: list[str] | None = None
    status: str | None = "unverified"
    role: str | None = None


class UpdateCandidateRequest(BaseModel):
    """Request model for updating a candidate profile."""

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
    status: str | None = "unverified"


class BulkCandidateRequest(BaseModel):
    """Request model for bulk candidate import"""

    candidates: list[BulkCandidateItem] = Field(min_length=1)


class VerifyCandidateRequest(BaseModel):
    """Request model for candidate email verification"""

    email: str = Field(..., description="Candidate email address")
    token: str = Field(..., description="Verification OTP token")


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

    @router.get("/candidates")
    async def list_candidates(
        search: str | None = Query(default=None),
        status: str | None = Query(default=None),
        role: str | None = Query(default=None),
        limit: int = 100,
        session_db: Session = Depends(get_db),
    ):
        """List all candidates with search and filter support"""
        try:
            candidates = candidate_manager.list_candidates(
                search=search, status=status, role=role, limit=limit
            )
            return {"count": len(candidates), "candidates": candidates}
        except Exception as e:
            logger.error(f"Error listing candidates: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error listing candidates",
            )

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
                status=request.status,
                role=request.role,
            )
            # Send verification email
            if candidate.get("verification_token") and candidate.get("email"):
                email_service.send_verification_email(
                    candidate_name=candidate["name"],
                    candidate_email=candidate["email"],
                    token=candidate["verification_token"],
                )
            return candidate
        except Exception as e:
            logger.error(f"Error creating candidate: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error creating candidate",
            )

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
        seen_emails = set()

        for index, item in enumerate(request.candidates):
            try:
                email_lower = item.email.strip().lower() if item.email else ""

                if email_lower in seen_emails:
                    raise ValueError("Duplicate email address in import request.")
                seen_emails.add(email_lower)


                candidate = candidate_manager.create_candidate(
                    name=item.name,
                    email=item.email,
                    status=item.status or "unverified",
                    role=item.position,
                )
                candidate["position"] = item.position
                candidate["phone"] = item.phone

                if candidate.get("verification_token") and candidate.get("email"):
                    email_service.send_verification_email(
                        candidate_name=candidate["name"],
                        candidate_email=candidate["email"],
                        token=candidate["verification_token"],
                    )
                created.append(candidate)
            except Exception as e:
                logger.error(f"Error creating candidate at row {index}: {e!s}")
                errors.append({"index": index, "email": item.email, "error": str(e)})
                 

        for index, item in enumerate(request.candidates):
            try:
                candidate = candidate_manager.create_candidate(
                    name=item.name,
                    email=item.email,
                    status=item.status or "unverified",
                    role=item.position,
                )

                # Echo back the non-persisted fields for frontend visibility only.
                candidate["position"] = item.position
                candidate["phone"] = item.phone

                # Send verification email
                if candidate.get("verification_token") and candidate.get("email"):
                    email_service.send_verification_email(
                        candidate_name=candidate["name"],
                        candidate_email=candidate["email"],
                        token=candidate["verification_token"],
                    )

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

    @router.post("/candidates/verify")
    async def verify_candidate(
        request: VerifyCandidateRequest,
        session_db: Session = Depends(get_db),
    ):
        """Verify candidate email profile with OTP"""
        try:
            success = candidate_manager.verify_candidate(
                email=request.email,
                token=request.token,
            )
            if not success:
                raise HTTPException(
                    status_code=400, detail="Invalid email or verification token"
                )
            return {"message": "Candidate verified successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying candidate: {e!s}")
            raise HTTPException(status_code=500, detail="Error verifying candidate")

    @router.post("/candidates/import-csv")
    async def import_candidates_csv(file: UploadFile = File(...)):
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are allowed",
            )

        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded CSV file is empty",
            )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".csv",
        ) as temp_file:
            temp_file.write(contents)
            temp_file_path = temp_file.name

        try:
            result = candidate_manager.import_candidates_from_csv(temp_file_path)
            return result
        except ValueError as e:
            logger.error(f"Invalid CSV for import: {e!s}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error importing candidates CSV: {e!s}")
            raise HTTPException(
                status_code=400,
                detail="Error importing candidates from CSV",
            )
        finally:
            os.unlink(temp_file_path)

    @router.get("/candidates/{candidate_id}")
    async def get_candidate(
        candidate_id: str,
        session_db: Session = Depends(get_db),
    ):
        """Get candidate details by ID"""
        try:
            candidate = candidate_manager.get_candidate(candidate_id)

            if not candidate:
                raise HTTPException(
                    status_code=404,
                    detail="Candidate not found",
                )

            return candidate

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Error fetching candidate: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error fetching candidate",
            )

    @router.put("/candidates/{candidate_id}")
    async def update_candidate(
        candidate_id: str,
        request: UpdateCandidateRequest,
        session_db: Session = Depends(get_db),
    ):
        """Update editable candidate profile fields."""
        try:
            candidate = candidate_manager.update_candidate(
                candidate_id=candidate_id,
                name=request.name,
                email=request.email,
                resume_text=request.resume_text,
                skills=request.skills,
            )

            if not candidate:
                raise HTTPException(
                    status_code=404,
                    detail="Candidate not found",
                )

            return candidate

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Error updating candidate: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error updating candidate",
            )

    @router.get("/candidates/{candidate_id}/history")
    async def get_candidate_history(
        candidate_id: str,
        session_db: Session = Depends(get_db),
    ):
        """Get candidate interview history"""
        try:
            candidate = candidate_manager.get_candidate(candidate_id)

            if not candidate:
                raise HTTPException(
                    status_code=404,
                    detail="Candidate not found",
                )

            history = candidate_manager.get_interview_history(candidate_id)

            return {
                "candidate_id": candidate_id,
                "history": history,
            }

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Error fetching candidate history: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error fetching candidate history",
            )

    return router
