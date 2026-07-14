"""
Session Tracker
Monitors and tracks interview session progress and status

Responsibilities:
- Track running sessions
- Detect stuck or inactive sessions
- Provide session statistics
- Monitor session health
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from database.db import SessionLocal
from database.models import InterviewSession

logger = logging.getLogger(__name__)


class SessionTracker:
    """
    Tracks and monitors interview sessions across the system
    """

    def __init__(self):
        """Initialize session tracker"""
    def get_active_sessions(
        self,
        status=None,
        since=None,
        sort_by="start_time",
        order="desc",
    ) -> list[dict[str, Any]]:
        """
        Get all currently active sessions (CREATED, QUEUED, PROCESSING)

        Returns:
            list: List of active session details
        """
        session_db = SessionLocal()
        try:
            active_statuses = [
                "CREATED",
                "QUEUED",
                "PROCESSING",
                "VIDEO_PROCESSING",
                "AUDIO_PROCESSING",
                "EVALUATING",
            ]
            
            # 1. Start with the baseline query for active statuses
            stmt = select(InterviewSession).where(InterviewSession.status.in_(active_statuses))

            # 2. Filter by status subset if provided
            if status:
                stmt = stmt.where(InterviewSession.status == status.upper())

            # 3. Filter by date cutoff if provided
            if since:
                try:
                    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                    stmt = stmt.where(InterviewSession.start_time > since_dt)
                except ValueError:
                    logger.error(f"Invalid ISO datetime string format passed: {since}")

            # 4. Handle dynamic column sorting safely
            sort_column = getattr(InterviewSession, sort_by, InterviewSession.start_time)
            if order.lower() == "desc":
                stmt = stmt.order_by(sort_column.desc().nullslast())
            else:
                stmt = stmt.order_by(sort_column.asc().nullslast())

            # 5. Execute the constructed statement
            sessions = session_db.execute(stmt).scalars().all()

            result = []
            for s in sessions:
                result.append(
                    {
                        "session_id": s.session_id,
                        "candidate_id": s.candidate_id,
                        "status": s.status,
                        "assigned_node": s.assigned_node,
                        "start_time": s.start_time.isoformat() if hasattr(s, "start_time") and s.start_time else None,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                    }
                )

            logger.debug(f"Retrieved {len(result)} active sessions")
            return result

        except Exception as e:
            logger.error(f"Error getting active sessions: {e!s}")
            return []
        finally:
            session_db.close()

    
    def get_completed_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get recently completed sessions

        Args:
            limit: Maximum number of sessions to retrieve

        Returns:
            list: List of completed session details
        """
        session_db = SessionLocal()
        try:
            rows = (
                session_db.execute(
                    select(InterviewSession)
                    .where(InterviewSession.status == "COMPLETED")
                    .order_by(InterviewSession.end_time.desc().nullslast())
                    .limit(limit)
                )
                .scalars()
                .all()
            )

            return [
                {
                    "session_id": s.session_id,
                    "candidate_id": s.candidate_id,
                    "status": s.status,
                    "risk_score": s.risk_score,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "duration_seconds": (
                        (s.end_time - s.start_time).total_seconds() if s.start_time and s.end_time else None
                    ),
                }
                for s in rows
            ]
        except Exception as e:
            logger.error(f"Error getting completed sessions: {e}")
            return []
        finally:
            session_db.close()

    def get_session_statistics(self) -> dict[str, Any]:
        """
        Compute aggregate session statistics across all sessions.

        Returns:
            dict: Comprehensive session statistics
        """
        session_db = SessionLocal()
        try:
            total_sessions = (
                session_db.execute(select(func.count()).select_from(InterviewSession)).scalar() or 0
            )

            status_rows = session_db.execute(
                select(InterviewSession.status, func.count()).group_by(InterviewSession.status)
            ).all()
            status_counts: dict[str, int] = {row[0]: row[1] for row in status_rows}

            completed_sessions = (
                session_db.execute(
                    select(InterviewSession).where(
                        InterviewSession.status == "COMPLETED",
                        InterviewSession.start_time.isnot(None),
                        InterviewSession.end_time.isnot(None),
                    )
                )
                .scalars()
                .all()
            )

            durations = [(s.end_time - s.start_time).total_seconds() for s in completed_sessions]
            avg_duration = sum(durations) / len(durations) if durations else 0

            risk_scores_list = list(
                session_db.execute(
                    select(InterviewSession.risk_score).where(InterviewSession.risk_score.isnot(None))
                )
                .scalars()
                .all()
            )
            avg_risk = sum(risk_scores_list) / len(risk_scores_list) if risk_scores_list else 0
            max_risk = max(risk_scores_list) if risk_scores_list else 0
            min_risk = min(risk_scores_list) if risk_scores_list else 0

            high_risk_count = (
                session_db.execute(
                    select(func.count())
                    .select_from(InterviewSession)
                    .where(InterviewSession.risk_score >= 0.8)
                ).scalar()
                or 0
            )

            active_states = (
                "PROCESSING",
                "QUEUED",
                "VIDEO_PROCESSING",
                "AUDIO_PROCESSING",
                "EVALUATING",
            )
            active_sessions = sum(status_counts.get(s, 0) for s in active_states)

            return {
                "total_sessions": total_sessions,
                "status_breakdown": status_counts,
                "active_sessions": active_sessions,
                "completed_sessions": status_counts.get("COMPLETED", 0),
                "failed_sessions": status_counts.get("FAILED", 0),
                "processing_stats": {
                    "average_duration_seconds": round(avg_duration, 2),
                    "completed_session_count": len(completed_sessions),
                },
                "risk_score_stats": {
                    "average_risk_score": round(avg_risk, 3),
                    "max_risk_score": round(max_risk, 3),
                    "min_risk_score": round(min_risk, 3),
                    "high_risk_sessions": high_risk_count,
                },
            }
        except Exception as e:
            logger.error(f"Error generating statistics: {e}")
            return {}
        finally:
            session_db.close()

    def get_stuck_sessions(self, timeout_minutes: int = 30) -> list[dict[str, Any]]:
        """
        Detect sessions that are stuck (in PROCESSING state beyond timeout)

        Args:
            timeout_minutes: Timeout threshold in minutes

        Returns:
            list: List of stuck session details
        """
        session_db = SessionLocal()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

            stuck_sessions = (
                session_db.execute(
                    select(InterviewSession).where(
                        InterviewSession.status == "PROCESSING",
                        InterviewSession.start_time < cutoff_time,
                    )
                )
                .scalars()
                .all()
            )

            result = []
            for s in stuck_sessions:
                elapsed_time = (datetime.now(timezone.utc) - s.start_time).total_seconds()
                result.append(
                    {
                        "session_id": s.session_id,
                        "candidate_id": s.candidate_id,
                        "status": s.status,
                        "assigned_node": s.assigned_node,
                        "start_time": s.start_time.isoformat() if s.start_time else None,
                        "elapsed_seconds": round(elapsed_time, 2),
                    }
                )

            if result:
                logger.warning(f"Found {len(result)} stuck sessions (timeout > {timeout_minutes} minutes)")

            return result

        except Exception as e:
            logger.error(f"Error detecting stuck sessions: {e!s}")
            return []
        finally:
            session_db.close()

    def get_worker_distribution(self) -> dict[str, int]:
        """
        Get distribution of active sessions across worker nodes

        Returns:
            dict: Worker node -> active session count mapping
        """
        session_db = SessionLocal()
        try:
            active_statuses = [
                "PROCESSING",
                "VIDEO_PROCESSING",
                "AUDIO_PROCESSING",
                "EVALUATING",
            ]
            sessions = (
                session_db.execute(
                    select(InterviewSession).where(InterviewSession.status.in_(active_statuses))
                )
                .scalars()
                .all()
            )

            distribution = {}
            for s in sessions:
                node = s.assigned_node or "unassigned"
                distribution[node] = distribution.get(node, 0) + 1

            logger.debug(f"Worker distribution: {distribution}")
            return distribution

        except Exception as e:
            logger.error(f"Error getting worker distribution: {e!s}")
            return {}
        finally:
            session_db.close()

    def get_high_risk_sessions(self, threshold: float = 0.8, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get high-risk sessions that completed

        Args:
            threshold: Risk score threshold (0-1)
            limit: Maximum number of sessions to retrieve

        Returns:
            list: List of high-risk sessions
        """
        session_db = SessionLocal()
        try:
            sessions = (
                session_db.execute(
                    select(InterviewSession)
                    .where(
                        InterviewSession.risk_score >= threshold,
                        InterviewSession.status == "COMPLETED",
                    )
                    .order_by(InterviewSession.risk_score.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )

            result = []
            for s in sessions:
                result.append(
                    {
                        "session_id": s.session_id,
                        "candidate_id": s.candidate_id,
                        "risk_score": s.risk_score,
                        "status": s.status,
                        "completed_at": s.end_time.isoformat() if s.end_time else None,
                    }
                )

            logger.debug(f"Retrieved {len(result)} high-risk sessions (threshold: {threshold})")
            return result

        except Exception as e:
            logger.error(f"Error getting high-risk sessions: {e!s}")
            return []
        finally:
            session_db.close()

    def get_failed_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get sessions that ended in a non-success terminal state
        (FAILED, TIMEOUT, or CANCELLED), newest first.

        Args:
            limit: Maximum number of sessions to retrieve.

        Returns:
            list: Failed session summaries.
        """
        session_db = SessionLocal()
        try:
            sessions = (
                session_db.execute(
                    select(InterviewSession)
                    .where(InterviewSession.status.in_(["FAILED", "TIMEOUT", "CANCELLED"]))
                    .order_by(InterviewSession.updated_at.desc().nullslast())
                    .limit(limit)
                )
                .scalars()
                .all()
            )

            result = [
                {
                    "session_id": s.session_id,
                    "candidate_id": s.candidate_id,
                    "status": s.status,
                    "risk_score": s.risk_score,
                    "assigned_node": s.assigned_node,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in sessions
            ]
            return result
        except Exception as e:
            logger.error(f"Error getting failed sessions: {e!s}")
            return []
        finally:
            session_db.close()
