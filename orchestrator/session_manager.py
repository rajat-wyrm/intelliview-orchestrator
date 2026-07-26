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

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from database.db import get_db_session
from database.models import InterviewSession
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
        VIDEO_PROCESSING: [
            AUDIO_PROCESSING,
            PROCESSING,
            EVALUATING,
            COMPLETED,
            FAILED,
            TIMEOUT,
        ],
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
        with get_db_session() as session_db:
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

            from monitoring.prometheus_metrics import (
                SESSIONS_ACTIVE,
                SESSIONS_CREATED,
            )

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
                "max_task_retries": 3,
            }
            self.state_sync.set_session_state(session_id, session_data)

            logger.info(f"Session {session_id} created successfully")
            return session_id

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
        with get_db_session() as session_db:
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

            from monitoring.prometheus_metrics import (
                SESSIONS_ACTIVE,
                SESSIONS_COMPLETED,
                SESSIONS_FAILED,
            )

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
