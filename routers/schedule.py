"""
Interview Schedule API Router.
Handles schedule creation, calendar listings, upcoming events, and triggering email notifications.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Candidate, InterviewSchedule
from orchestrator.email_service import email_service
from orchestrator.notification_manager import NotificationManager

logger = logging.getLogger(__name__)

ALLOWED_STATUSES = {"scheduled", "completed", "cancelled", "rescheduled"}


class CreateScheduleRequest(BaseModel):
    """Payload for creating a new interview schedule."""

    candidate_id: str = Field(..., description="ID of the candidate")
    interviewer_id: str = Field(
        ..., description="Name or ID of the assigned interviewer"
    )
    scheduled_at: datetime = Field(
        ..., description="ISO datetime string for the scheduled interview"
    )
    notes: str | None = Field(
        default=None, description="Optional interview notes or description"
    )
    send_email: bool = Field(
        default=True, description="Whether to send confirmation email via smtplib"
    )


class UpdateScheduleRequest(BaseModel):
    """Payload for updating schedule status or details."""

    schedule_id: str | None = Field(
        default=None, description="Optional schedule ID in payload"
    )
    status: str | None = Field(default=None, description="New schedule status")
    notes: str | None = Field(default=None, description="Updated notes")
    scheduled_at: datetime | None = Field(
        default=None, description="Rescheduled datetime"
    )
    new_scheduled_at: datetime | None = Field(
        default=None, description="Rescheduled datetime alias"
    )


def create_schedule_routes() -> APIRouter:
    """Create APIRouter for interview scheduling."""

    router = APIRouter(prefix="/api/schedule", tags=["Schedule"])

    @router.post("", status_code=201)
    async def create_schedule(
        payload: CreateScheduleRequest,
        db: Session = Depends(get_db),
    ):
        """
        Create a new interview schedule and trigger an email notification to the candidate.
        Validates future date/time and candidate existence.
        """
        try:
            # Check candidate existence
            candidate = db.execute(
                select(Candidate).where(Candidate.candidate_id == payload.candidate_id)
            ).scalar_one_or_none()

            if not candidate:
                raise HTTPException(
                    status_code=404,
                    detail=f"Candidate with ID '{payload.candidate_id}' not found.",
                )

            # Ensure datetime is timezone-aware
            scheduled_at = payload.scheduled_at
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

            # Validate that scheduled_at is in the future
            now_utc = datetime.now(timezone.utc)
            if scheduled_at <= now_utc:
                raise HTTPException(
                    status_code=400,
                    detail="Scheduled date and time must be in the future.",
                )

            # Create Schedule ORM entry
            schedule = InterviewSchedule(
                candidate_id=payload.candidate_id,
                interviewer_id=payload.interviewer_id,
                scheduled_at=scheduled_at,
                status="scheduled",
                notes=payload.notes,
            )

            db.add(schedule)
            db.commit()
            db.refresh(schedule)

            # Send Email Notification
            email_sent = False
            email_msg = "Email notification disabled."

            if payload.send_email and candidate.email:
                date_str = scheduled_at.strftime("%B %d, %Y")
                time_str = scheduled_at.strftime("%I:%M %p %Z").strip()

                email_sent, email_msg = email_service.send_interview_confirmation(
                    candidate_name=candidate.name,
                    candidate_email=candidate.email,
                    interview_date=date_str,
                    interview_time=time_str,
                    interviewer_name=payload.interviewer_id,
                    schedule_id=schedule.id,
                    notes=payload.notes,
                )

            return {
                "message": "Interview scheduled successfully.",
                "schedule": {
                    "id": schedule.id,
                    "candidate_id": schedule.candidate_id,
                    "candidate_name": candidate.name,
                    "candidate_email": candidate.email,
                    "interviewer_id": schedule.interviewer_id,
                    "scheduled_at": schedule.scheduled_at.isoformat(),
                    "status": schedule.status,
                    "notes": schedule.notes,
                    "created_at": schedule.created_at.isoformat(),
                },
                "email_notification": {
                    "sent": email_sent,
                    "detail": email_msg,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error scheduling interview: {e!s}")
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to schedule interview: {e!s}"
            )

    @router.get("")
    async def list_schedules(
        candidate_id: str | None = Query(default=None),
        status: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        db: Session = Depends(get_db),
    ):
        """List all interview schedules with candidate details."""
        try:
            stmt = select(InterviewSchedule, Candidate).join(
                Candidate, InterviewSchedule.candidate_id == Candidate.candidate_id
            )

            if candidate_id:
                stmt = stmt.where(InterviewSchedule.candidate_id == candidate_id)

            if status:
                clean_status = status.strip().lower()
                stmt = stmt.where(InterviewSchedule.status == clean_status)

            stmt = stmt.order_by(InterviewSchedule.scheduled_at.asc()).limit(limit)
            results = db.execute(stmt).all()

            schedules_data = []

            for sched, cand in results:
                schedules_data.append(
                    {
                        "id": sched.id,
                        "candidate_id": sched.candidate_id,
                        "candidate_name": cand.name,
                        "candidate_email": cand.email,
                        "interviewer_id": sched.interviewer_id,
                        "scheduled_at": sched.scheduled_at.isoformat(),
                        "status": sched.status,
                        "notes": sched.notes,
                        "created_at": sched.created_at.isoformat(),
                    }
                )

            return {
                "count": len(schedules_data),
                "schedules": schedules_data,
            }

        except Exception as e:
            logger.error(f"Error fetching schedules: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error fetching interview schedules",
            )

    @router.get("/upcoming")
    async def list_upcoming_schedules(
        limit: int = Query(default=10, ge=1, le=50),
        db: Session = Depends(get_db),
    ):
        """List upcoming scheduled interviews from the current time onwards."""
        try:
            now = datetime.now(timezone.utc)

            stmt = (
                select(InterviewSchedule, Candidate)
                .join(
                    Candidate,
                    InterviewSchedule.candidate_id == Candidate.candidate_id,
                )
                .where(InterviewSchedule.scheduled_at >= now)
                .where(InterviewSchedule.status == "scheduled")
                .order_by(InterviewSchedule.scheduled_at.asc())
                .limit(limit)
            )

            results = db.execute(stmt).all()

            upcoming_data = []

            for sched, cand in results:
                upcoming_data.append(
                    {
                        "id": sched.id,
                        "candidate_id": sched.candidate_id,
                        "candidate_name": cand.name,
                        "candidate_email": cand.email,
                        "interviewer_id": sched.interviewer_id,
                        "scheduled_at": sched.scheduled_at.isoformat(),
                        "status": sched.status,
                        "notes": sched.notes,
                    }
                )

            return {
                "count": len(upcoming_data),
                "upcoming": upcoming_data,
            }

        except Exception as e:
            logger.error(f"Error fetching upcoming schedules: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error fetching upcoming schedules",
            )

    @router.get("/{schedule_id}")
    async def get_schedule(
        schedule_id: str,
        db: Session = Depends(get_db),
    ):
        """Get details for a specific interview schedule."""
        try:
            stmt = (
                select(InterviewSchedule, Candidate)
                .join(
                    Candidate,
                    InterviewSchedule.candidate_id == Candidate.candidate_id,
                )
                .where(InterviewSchedule.id == schedule_id)
            )

            result = db.execute(stmt).first()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail="Schedule not found",
                )

            sched, cand = result

            return {
                "id": sched.id,
                "candidate_id": sched.candidate_id,
                "candidate_name": cand.name,
                "candidate_email": cand.email,
                "interviewer_id": sched.interviewer_id,
                "scheduled_at": sched.scheduled_at.isoformat(),
                "status": sched.status,
                "notes": sched.notes,
                "created_at": sched.created_at.isoformat(),
            }

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Error getting schedule: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error getting schedule details",
            )

    @router.patch("/{schedule_id}")
    async def update_schedule(
        schedule_id: str,
        payload: UpdateScheduleRequest,
        db: Session = Depends(get_db),
    ):
        """
        Update interview schedule status or datetime with strict validation.

        When the status actually changes to 'cancelled' or 'rescheduled',
        exactly one corresponding notification is created.
        """
        try:
            schedule = db.execute(
                select(InterviewSchedule).where(InterviewSchedule.id == schedule_id)
            ).scalar_one_or_none()

            if not schedule:
                raise HTTPException(
                    status_code=404,
                    detail="Schedule not found",
                )

            # Store the original status before making any changes.
            # This is required to detect a real status transition and prevent
            # duplicate notifications when the same status is submitted again.
            old_status = schedule.status

            clean_status = None

            # Validate status input
            if payload.status is not None:
                clean_status = payload.status.strip().lower()

                if clean_status not in ALLOWED_STATUSES:
                    allowed_str = ", ".join(sorted(ALLOWED_STATUSES))

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Invalid status '{payload.status}'. "
                            f"Allowed statuses are: {allowed_str}"
                        ),
                    )

            # Support both `scheduled_at` and the `new_scheduled_at` alias.
            target_scheduled_at = (
                payload.new_scheduled_at
                if payload.new_scheduled_at is not None
                else payload.scheduled_at
            )

            if (
                clean_status in {"cancelled", "completed"}
                and target_scheduled_at is not None
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"scheduled_at cannot be provided when status is '{clean_status}'.",
                )

            if target_scheduled_at is not None:
                sched_at = target_scheduled_at

                # Treat timezone-naive values as UTC for consistency
                # with the existing POST endpoint.
                if sched_at.tzinfo is None:
                    sched_at = sched_at.replace(tzinfo=timezone.utc)

                now_utc = datetime.now(timezone.utc)

                if sched_at <= now_utc:
                    raise HTTPException(
                        status_code=400,
                        detail="Scheduled date and time must be in the future.",
                    )

                schedule.scheduled_at = sched_at

                # If no explicit status was provided alongside a new date,
                # infer that this is a reschedule.
                if clean_status is None:
                    clean_status = "rescheduled"

            if clean_status is not None:
                schedule.status = clean_status

            if payload.notes is not None:
                schedule.notes = payload.notes

            # Save the schedule changes first.
            db.commit()
            db.refresh(schedule)

            new_status = clean_status

            # Trigger notification only for an actual transition to
            # 'cancelled' or 'rescheduled'.
            #
            # Examples:
            # scheduled -> cancelled     = notification
            # scheduled -> rescheduled   = notification
            # cancelled -> cancelled     = no notification
            # rescheduled -> rescheduled = no notification
            # scheduled -> completed     = no notification
            if (
                new_status is not None
                and old_status != new_status
                and new_status in {"cancelled", "rescheduled"}
            ):
                notification_manager = NotificationManager(db=db)

                notification_manager.notify_schedule_status_change(
                    user_id=schedule.candidate_id,
                    new_status=new_status,
                )

            return {
                "message": "Schedule updated successfully",
                "schedule": {
                    "id": schedule.id,
                    "candidate_id": schedule.candidate_id,
                    "status": schedule.status,
                    "scheduled_at": schedule.scheduled_at.isoformat(),
                    "notes": schedule.notes,
                    "updated_at": (
                        schedule.updated_at.isoformat() if schedule.updated_at else None
                    ),
                },
            }

        except HTTPException:
            db.rollback()
            raise

        except Exception as e:
            logger.error(f"Error updating schedule: {e!s}")
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Error updating schedule",
            )

    return router
