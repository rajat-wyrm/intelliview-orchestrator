"""Aggregated hiring analytics for the dashboard."""

import logging
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Candidate, InterviewSession, InterviewTemplate

logger = logging.getLogger(__name__)

router = APIRouter()

PASS_SCORE_THRESHOLD = 70.0
LEADERBOARD_LIMIT = 10

RISK_BUCKETS = [
    ("Low", 0.0, 0.3),
    ("Medium", 0.3, 0.6),
    ("High", 0.6, 0.8),
    ("Critical", 0.8, float("inf")),
]


@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Aggregate real interview and candidate data for the analytics dashboard."""
    try:
        sessions = db.execute(select(InterviewSession)).scalars().all()
        candidates = db.execute(select(Candidate)).scalars().all()
        templates = {
            t.template_id: t.name
            for t in db.execute(select(InterviewTemplate)).scalars().all()
        }

        completed = [s for s in sessions if s.status == "COMPLETED"]
        scored = [s for s in completed if s.overall_score is not None]
        risk_scored = [s for s in sessions if s.risk_score is not None]
        durations = [
            (s.end_time - s.start_time).total_seconds() / 60.0
            for s in completed
            if s.start_time and s.end_time
        ]

        passed = [s for s in scored if s.overall_score >= PASS_SCORE_THRESHOLD]
        kpis = {
            "total_interviews": len(sessions),
            "completed_interviews": len(completed),
            "total_candidates": len(candidates),
            "pass_rate": round(len(passed) / len(scored) * 100, 1) if scored else 0.0,
            "average_score": round(sum(s.overall_score for s in scored) / len(scored), 1)
            if scored
            else 0.0,
            "average_risk_score": round(
                sum(s.risk_score for s in risk_scored) / len(risk_scored), 3
            )
            if risk_scored
            else 0.0,
            "average_duration_minutes": round(sum(durations) / len(durations), 1)
            if durations
            else 0.0,
        }

        by_day = defaultdict(lambda: {"total": 0, "passed": 0})
        for s in scored:
            ts = s.updated_at or s.created_at
            if not ts:
                continue
            day = ts.strftime("%Y-%m-%d")
            by_day[day]["total"] += 1
            if s.overall_score >= PASS_SCORE_THRESHOLD:
                by_day[day]["passed"] += 1
        pass_rate_over_time = [
            {
                "period": day,
                "pass_rate": round(v["passed"] / v["total"] * 100, 1),
                "total": v["total"],
            }
            for day, v in sorted(by_day.items())
        ]

        by_position = defaultdict(list)
        for s in scored:
            position = templates.get(s.template_id, "Unspecified")
            by_position[position].append(s.overall_score)
        score_by_position = [
            {"position": pos, "avg_score": round(sum(vals) / len(vals), 1), "count": len(vals)}
            for pos, vals in sorted(by_position.items())
        ]

        risk_distribution = [
            {
                "label": label,
                "value": sum(1 for s in risk_scored if lo <= s.risk_score < hi),
            }
            for label, lo, hi in RISK_BUCKETS
        ]

        by_month = defaultdict(list)
        for s in completed:
            if s.start_time and s.end_time:
                month = s.start_time.strftime("%Y-%m")
                by_month[month].append((s.end_time - s.start_time).total_seconds() / 60.0)
        duration_by_month = [
            {"month": m, "average_duration_minutes": round(sum(vals) / len(vals), 1)}
            for m, vals in sorted(by_month.items())
        ]

        ranked_candidates = sorted(
            (c for c in candidates if c.avg_score is not None),
            key=lambda c: c.avg_score,
            reverse=True,
        )[:LEADERBOARD_LIMIT]
        leaderboard = [
            {
                "candidate_id": c.candidate_id,
                "name": c.name,
                "avg_score": round(c.avg_score, 1),
                "total_interviews": c.total_interviews,
            }
            for c in ranked_candidates
        ]

        return {
            "kpis": kpis,
            "pass_rate_over_time": pass_rate_over_time,
            "score_by_position": score_by_position,
            "risk_distribution": risk_distribution,
            "duration_by_month": duration_by_month,
            "leaderboard": leaderboard,
        }
    except Exception as e:
        logger.error(f"Error computing analytics: {e!s}")
        raise HTTPException(status_code=500, detail="Error computing analytics")
