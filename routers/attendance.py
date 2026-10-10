"""Attendance and no-show detection routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import InterviewSchedule, InterviewSession


def create_attendance_routes() -> APIRouter:
    """Create attendance and no-show routes."""

    router = APIRouter()

    @router.post("/attendance/check-no-shows")
    async def check_no_shows(session_db: Session = Depends(get_db)):
        """Mark overdue scheduled interviews with no activity as no-shows."""

        now = datetime.now(timezone.utc)

        schedules = (
            session_db.execute(
                select(InterviewSchedule).where(
                    InterviewSchedule.scheduled_at < now,
                    InterviewSchedule.status == "scheduled",
                )
            )
            .scalars()
            .all()
        )

        marked_no_shows = []

        for schedule in schedules:
            has_activity = session_db.scalar(
                select(
                    exists().where(
                        InterviewSession.candidate_id == schedule.candidate_id,
                        InterviewSession.start_time.is_not(None),
                        InterviewSession.start_time >= schedule.scheduled_at,
                    )
                )
            )

            if not has_activity:
                schedule.status = "no-show"
                marked_no_shows.append(schedule.id)

        session_db.commit()

        return {
            "message": "No-show detection completed.",
            "marked_no_shows": marked_no_shows,
            "count": len(marked_no_shows),
        }

    @router.get("/attendance/no-show-counts")
    async def get_no_show_counts(session_db: Session = Depends(get_db)):
        """Return the number of no-shows for each candidate."""

        results = session_db.execute(
            select(
                InterviewSchedule.candidate_id,
                func.count(InterviewSchedule.id).label("no_show_count"),
            )
            .where(InterviewSchedule.status == "no-show")
            .group_by(InterviewSchedule.candidate_id)
        ).all()

        return [
            {
                "candidate_id": candidate_id,
                "no_show_count": no_show_count,
            }
            for candidate_id, no_show_count in results
        ]

    return router
