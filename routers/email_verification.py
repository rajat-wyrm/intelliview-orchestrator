"""Email Verification Router"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Candidate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Email Verification"])


@router.get("/verify-email")
async def verify_email(
    token: str = Query(..., description="The secure email verification token"),
    db: Session = Depends(get_db),
):
    """
    Handle candidate email verification link.
    Validates token, checks expiration, and updates verification status.
    """
    if not token or not token.strip():
        raise HTTPException(status_code=400, detail="Invalid token")

    try:
        # Find candidate with this token
        candidate = db.execute(
            select(Candidate).where(Candidate.verification_token == token)
        ).scalar_one_or_none()

        if not candidate:
            logger.warning(f"Verification attempt with invalid token: {token[:8]}...")
            raise HTTPException(status_code=400, detail="Invalid token")

        # Check expiration
        now_utc = datetime.now(timezone.utc)
        expires_at = candidate.verification_token_expires_at
        if expires_at:
            # Ensure expires_at is timezone-aware
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if now_utc > expires_at:
                logger.warning(
                    f"Verification attempt with expired token for candidate {candidate.candidate_id}"
                )
                raise HTTPException(
                    status_code=400, detail="Verification token has expired"
                )

        # Mark candidate as verified and clear token fields
        candidate.email_verified = True
        candidate.verification_token = None
        candidate.verification_token_expires_at = None

        db.commit()
        db.refresh(candidate)

        logger.info(f"Candidate {candidate.candidate_id} verified successfully")
        return {"message": "Email verified successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during email verification: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during verification"
        )
