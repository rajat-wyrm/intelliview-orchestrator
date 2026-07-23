"""
Session Manager
Manages the complete lifecycle of interview sessions

Responsibilities:
- Create new interview sessions
- Update session state
- Retrieve session details
- Handle session transitions
- Maintain consistency between Redis and PostgreSQL
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from database.db import SessionLocal
from database.models import InterviewSession
from monitoring.websocket_manager import ws_manager
from orchestrator.state_sync import StateSynchronizer

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionManager:
    """
    Manages interview session lifecycle and state transitions
    """

    # Session states
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    VIDEO_PROCESSING = "VIDEO_PROCESSING"
    AUDIO_PROCESSING = "AUDIO_PROCESSING"
    EVALUATING = "EVALUATING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"

    # Valid state transitions. The pipeline goes through a sequence of
    # granular PROCESSING sub-states before reaching COMPLETED.
    VALID_TRANSITIONS = {
        CREATED: [QUEUED, FAILED, CANCELLED],
        QUEUED: [PROCESSING, VIDEO_PROCESSING, FAILED, CANCELLED],
        PROCESSING: [
            VIDEO_PROCESSING,
            AUDIO_PROCESSING,
            EVALUATING,
            COMPLETED,
            FAILED,
            TIMEOUT,
        ],
        VIDEO_PROCESSING: [ AUDIO_PROCESSING,PROCESSING,EVALUATING,COMPLETED,FAILED,TIMEOUT,],
        AUDIO_PROCESSING: [EVALUATING, PROCESSING, FAILED, TIMEOUT],
        EVALUATING: [COMPLETED, PROCESSING, FAILED, TIMEOUT],
        COMPLETED: [],
        FAILED: [],
        TIMEOUT: [FAILED],
        CANCELLED: [],
    }

    # Timeout thresholds (in seconds)
    PROCESSING_TIMEOUT = 1800  # 30 minutes
    QUEUED_TIMEOUT = 3600  # 60 minutes

    def __init__(self):
        """Initialize session manager with state synchronizer"""
        self.state_sync = StateSynchronizer()

    def create_session(
        self,
        candidate_id: str,
        position: str | None = None,
        candidate_name: str | None = None,
    ) -> str:
        """
        Create a new interview session

        Args:
            candidate_id: Unique candidate identifier
            position: Job position for the interview
            candidate_name: Candidate's name

        Returns:
            str: Generated session_id
        """
        session_db = SessionLocal()
        try:
            # Generate collision-safe unique session ID
            session_id = f"session_{uuid.uuid4().hex[:16]}"

            logger.info(f"Creating new interview session: {session_id} for candidate {candidate_id}")

            # Create database record
            interview_session = InterviewSession(
                session_id=session_id,
                candidate_id=candidate_id,
                status=self.CREATED,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )

            session_db.add(interview_session)
            
            from monitoring.prometheus_metrics import (SESSIONS_CREATED,SESSIONS_ACTIVE,)
            
            session_db.commit()
            
            SESSIONS_CREATED.inc()
         
           
            SESSIONS_ACTIVE.inc()
            logger.info("Prometheus session metrics updated")

            # Sync to Redis cache
            session_data = {
                "session_id": session_id,
                "candidate_id": candidate_id,
                "candidate_name": candidate_name or "Unknown",
                "position": position or "Unknown",
                "status": self.CREATED,
                "created_at": _utcnow().isoformat(),
                "updated_at": _utcnow().isoformat(),
                "risk_score": None,
                "max_task_retries" : 3,
            }
            self.state_sync.set_session_state(session_id, session_data)

            logger.info(f"Session {session_id} created successfully")
            return session_id

        except Exception as e:
            logger.error(f"Error creating session: {e!s}")
            session_db.rollback()
            raise
        finally:
            session_db.close()

    def update_session_status(
        self,
        session_id: str,
        new_status: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update session status with validation

        Args:
            session_id: Session identifier
            new_status: New status to set
            metadata: Optional additional data to store

        Returns:
            bool: True if successful, False otherwise
        """
        session_db = SessionLocal()
        try:
            # Get current session
            interview = session_db.execute(
                select(InterviewSession).where(InterviewSession.session_id == session_id)
            ).scalar_one_or_none()

            if not interview:
                logger.error(f"Session {session_id} not found")
                return False

            current_status = interview.status

            # Validate state transition
            if not self._is_valid_transition(current_status, new_status):
                logger.warning(
                    f"Invalid state transition: {current_status} -> {new_status} for session {session_id}"
                )
                return False

            logger.info(f"Updating session {session_id} status: {current_status} -> {new_status}")

            # Update database
            interview.status = new_status
            interview.updated_at = _utcnow()
            session_db.commit()
            from monitoring.prometheus_metrics import (SESSIONS_ACTIVE,SESSIONS_COMPLETED,SESSIONS_FAILED,)

            if new_status == self.COMPLETED:
              SESSIONS_COMPLETED.inc()
              SESSIONS_ACTIVE.dec()

            elif new_status == self.FAILED:
              SESSIONS_FAILED.inc()
              SESSIONS_ACTIVE.dec()

            # Update Redis cache
            session_data = self.state_sync.get_session_state(session_id)
            if session_data:
                session_data["status"] = new_status
                session_data["updated_at"] = _utcnow().isoformat()
                if metadata:
                    session_data.update(metadata)
                self.state_sync.set_session_state(session_id, session_data)

            logger.info(f"Session {session_id} status updated to {new_status}")

            # Broadcast the transition to dashboard WebSocket clients (non-blocking).
            self._broadcast_status(session_id, new_status, interview.risk_score, metadata or {})

            return True

        except Exception as e:
            logger.error(f"Error updating session status: {e!s}")
            session_db.rollback()
            return False
        finally:
            session_db.close()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve session details

        Args:
            session_id: Session identifier

        Returns:
            dict: Session details or None if not found
        """
        try:
            # Try to get from Redis cache first (fast path)
            session_data = self.state_sync.get_session_state(session_id)
            if session_data:
                logger.debug(f"Retrieved session {session_id} from cache")
                return session_data

            # Fall back to database
            session_db = SessionLocal()
            try:
                interview = session_db.execute(
                    select(InterviewSession).where(InterviewSession.session_id == session_id)
                ).scalar_one_or_none()

                if not interview:
                    logger.warning(f"Session {session_id} not found")
                    return None

                # Convert to dict for consistency
                session_data = {
                    "session_id": interview.session_id,
                    "candidate_id": interview.candidate_id,
                    "status": interview.status,
                    "risk_score": interview.risk_score,
                    "assigned_node": interview.assigned_node,
                    "start_time": interview.start_time.isoformat() if interview.start_time else None,
                    "end_time": interview.end_time.isoformat() if interview.end_time else None,
                    "created_at": interview.created_at.isoformat() if interview.created_at else None,
                    "updated_at": interview.updated_at.isoformat() if interview.updated_at else None,
                    "video_analysis": interview.video_analysis,
                    "audio_analysis": interview.audio_analysis,
                    "evaluation_analysis": interview.evaluation_analysis,
                }

                # Update Redis cache for next lookup
                self.state_sync.set_session_state(session_id, session_data)

                logger.debug(f"Retrieved session {session_id} from database")
                return session_data

            finally:
                session_db.close()

        except Exception as e:
            logger.error(f"Error retrieving session: {e!s}")
            return None

    def mark_session_failed(self, session_id: str, error_message: str) -> bool:
        """
        Mark a session as failed with error details

        Args:
            session_id: Session identifier
            error_message: Error message describing the failure

        Returns:
            bool: True if successful
        """
        from monitoring.prometheus_metrics import (SESSIONS_FAILED,SESSIONS_ACTIVE,)
        SESSIONS_FAILED.inc()
        print("SESSIONS_FAILED =", SESSIONS_FAILED._value.get())
        SESSIONS_ACTIVE.dec()
        logger.warning(f"Marking session {session_id} as failed: {error_message}")

        return self.update_session_status(session_id, self.FAILED, {"error_message": error_message})

    def mark_session_completed(self, session_id: str, risk_score: float) -> bool:
        """
        Mark a session as completed with final risk score

        Args:
            session_id: Session identifier
            risk_score: Final calculated risk score

        Returns:
            bool: True if successful
        """
        logger.info(f"Marking session {session_id} as completed with risk score {risk_score}")

        session_db = SessionLocal()
        try:
            interview = session_db.execute(
                select(InterviewSession).where(InterviewSession.session_id == session_id)
            ).scalar_one_or_none()

            if not interview:
                return False

            interview.status = self.COMPLETED
            interview.risk_score = risk_score
            interview.end_time = _utcnow()
            interview.updated_at = _utcnow()
           
            from monitoring.prometheus_metrics import (SESSIONS_COMPLETED,SESSIONS_ACTIVE,RISK_SCORE,SESSION_PROCESSING_DURATION,)
            session_db.commit()
            SESSIONS_COMPLETED.inc()
            print("SESSIONS_COMPLETED =", SESSIONS_COMPLETED._value.get())
            SESSIONS_ACTIVE.dec()

            RISK_SCORE.observe(risk_score)

            if interview.start_time:
              duration = (
              interview.end_time - interview.start_time
              ).total_seconds()
              SESSION_PROCESSING_DURATION.observe(duration)

            # Update Redis
            session_data = self.state_sync.get_session_state(session_id)
            if session_data:
                session_data["status"] = self.COMPLETED
                session_data["risk_score"] = risk_score
                session_data["end_time"] = _utcnow().isoformat()
                session_data["updated_at"] = _utcnow().isoformat()
                self.state_sync.set_session_state(session_id, session_data)

            logger.info(f"Session {session_id} marked as completed")
            return True

        except Exception as e:
            logger.error(f"Error marking session completed: {e!s}")
            session_db.rollback()
            return False
        finally:
            session_db.close()

    def _is_valid_transition(self, current_status: str, new_status: str) -> bool:
        """
        Check if state transition is valid

        Args:
            current_status: Current session status
            new_status: New status to transition to

        Returns:
            bool: True if transition is valid
        """
        if current_status not in self.VALID_TRANSITIONS:
            return False

        return new_status in self.VALID_TRANSITIONS[current_status]

    @staticmethod
    def _broadcast_status(
        session_id: str, status: str, risk_score: float | None, details: dict[str, Any]
    ) -> None:
        """Schedule a non-blocking WebSocket broadcast (fire-and-forget)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no loop in tests / scripts — silently skip

        async def _emit() -> None:
            try:
                await ws_manager.broadcast_session_update(
                    session_id=session_id,
                    status=status,
                    details=details,
                    risk_score=risk_score,
                )
            except Exception as exc:
                logger.debug("ws broadcast failed for %s: %s", session_id, exc)

        # The task is intentionally fire-and-forget; we keep a reference to
        # avoid RUF006 ("Store a reference to the return value") but don't
        # await it because callers don't block on broadcasts.
        task = loop.create_task(_emit())
        task.add_done_callback(lambda _t: None)
