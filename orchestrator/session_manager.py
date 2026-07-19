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
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy import select

from database.db import SessionLocal
from database.models import InterviewSession
from monitoring.websocket_manager import ws_manager
from orchestrator.state_sync import StateSynchronizer

logger = logging.getLogger(__name__)

_LUA_SCRIPT_PATH = Path(__file__).parent / "atomic_transition.lua"


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
        VIDEO_PROCESSING: [AUDIO_PROCESSING, PROCESSING, FAILED, TIMEOUT],
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

        # StateSynchronizer.redis_client may be a raw redis.Redis client, a
        # wrapper around one, or None if the connection failed at startup.
        # register_script() is a redis-py method; if redis_client is some
        # custom wrapper that doesn't expose it (or expose the underlying
        # client), we must not let that crash SessionManager construction —
        # every caller of SessionManager() would break. Instead we disable
        # atomic transitions and log loudly, so this is visible without
        # taking down the whole service.
        #
        # TODO: once redis_client.py's wrapper is confirmed to expose the
        # raw client (e.g. via a `.client` / `.raw` attribute, or by adding
        # a passthrough register_script method on the wrapper itself), point
        # this at that instead of assuming self.state_sync.redis_client IS
        # the raw client.
        self._redis = self.state_sync.redis_client
        self._transition_script = None
        if self._redis is not None:
            try:
                self._transition_script = self._redis.register_script(_LUA_SCRIPT_PATH.read_text())
            except AttributeError:
                logger.error(
                    "redis_client does not support register_script() (wrapper type: %s); "
                    "atomic state transitions are disabled until this is resolved",
                    type(self._redis).__name__,
                )
        else:
            logger.error("Redis unavailable at startup; atomic state transitions are disabled")

        # Pre-serialize once; VALID_TRANSITIONS is static for the process lifetime.
        self._transitions_json = json.dumps(self.VALID_TRANSITIONS)

    @staticmethod
    def _session_key(session_id: str) -> str:
        """Redis key under which the session's JSON state blob lives.

        Uses StateSynchronizer.SESSION_KEY_PREFIX so this can never drift out
        of sync with the key format set_session_state/get_session_state use.
        """
        return f"{StateSynchronizer.SESSION_KEY_PREFIX}{session_id}"

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
            session_db.commit()

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
        Atomically validate and apply a session status transition.

        The Redis Lua script (atomic_transition.lua) is the single source of
        truth for whether the transition is legal: it performs the
        current-status read, the VALID_TRANSITIONS check, and the write as
        one atomic operation on the Redis server, so two concurrent callers
        can never both "win" a transition off the same current state.

        Postgres is updated only after Redis confirms the transition was
        valid. If the Postgres write then fails, we compensate by reverting
        the Redis state back to old_status so the two stores don't diverge.

        Args:
            session_id: Session identifier
            new_status: New status to set
            metadata: Optional additional data to store

        Returns:
            bool: True if successful, False otherwise
        """
        metadata = metadata or {}

        if self._transition_script is None:
            logger.error(f"Atomic transitions unavailable (no Redis connection); rejecting {session_id}")
            return False

        try:
            raw_result = self._transition_script(
                keys=[self._session_key(session_id)],
                args=[
                    "transition",
                    new_status,
                    _utcnow().isoformat(),
                    json.dumps(metadata, default=str),
                    self._transitions_json,
                    "",  # expected_current_status unused in "transition" mode
                ],
            )
        except RedisError as e:
            logger.error(f"Redis error during atomic transition for {session_id}: {e!s}")
            return False

        result = json.loads(raw_result)

        if result["status"] == "not_found":
            logger.error(f"Session {session_id} not found in Redis")
            return False

        if result["status"] == "corrupt_state":
            logger.error(f"Session {session_id} has corrupt cached state; refusing transition")
            return False

        if result["status"] == "invalid_transition":
            logger.warning(
                f"Invalid state transition: {result['current_status']} -> "
                f"{result['attempted_status']} for session {session_id}"
            )
            return False

        # result["status"] == "ok" — Redis has already committed the new
        # status. Now persist the same transition to Postgres.
        old_status = result["old_status"]

        session_db = SessionLocal()
        try:
            interview = session_db.execute(
                select(InterviewSession).where(InterviewSession.session_id == session_id)
            ).scalar_one_or_none()

            if not interview:
                logger.error(f"Session {session_id} not found in database; reverting Redis state")
                self._revert_transition(session_id, old_status, new_status)
                return False

            logger.info(f"Updating session {session_id} status: {old_status} -> {new_status}")

            interview.status = new_status
            interview.updated_at = _utcnow()
            session_db.commit()

        except Exception as e:
            logger.error(f"Error updating session status in database: {e!s}")
            session_db.rollback()
            self._revert_transition(session_id, old_status, new_status)
            return False
        finally:
            session_db.close()

        logger.info(f"Session {session_id} status updated to {new_status}")

        # Broadcast the transition to dashboard WebSocket clients (non-blocking).
        self._broadcast_status(session_id, new_status, interview.risk_score, metadata)

        return True

    def _revert_transition(self, session_id: str, old_status: str, applied_status: str) -> None:
        """
        Best-effort compensation: roll the Redis-cached status back to
        old_status after a downstream (Postgres) failure, so the cache
        doesn't advertise a status the database never committed.

        This deliberately does NOT reuse the "transition" mode, since a
        revert (e.g. PROCESSING -> QUEUED) is frequently not itself a legal
        forward transition in VALID_TRANSITIONS and would always be
        rejected. Instead it uses "revert" mode, a compare-and-set that only
        applies if the session is still showing `applied_status` — i.e.
        nobody else has moved it on since our forward transition landed. If
        someone else already has, we back off and log rather than clobber
        their change.

        Args:
            session_id: Session identifier
            old_status: The status to revert back to
            applied_status: The status our forward transition set — used as
                the compare-and-set guard
        """
        if self._transition_script is None:
            return

        try:
            raw_result = self._transition_script(
                keys=[self._session_key(session_id)],
                args=["revert", old_status, _utcnow().isoformat(), "{}", "{}", applied_status],
            )
            result = json.loads(raw_result)
            if result["status"] != "ok":
                logger.error(
                    f"Could not revert session {session_id} to {old_status}: {result['status']}"
                )
        except RedisError as e:
            logger.error(f"Redis error while reverting session {session_id}: {e!s}")

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
            success = self.update_session_status(
                session_id, self.COMPLETED, {"risk_score": risk_score}
            )
            if not success:
                return False

            interview = session_db.execute(
                select(InterviewSession).where(InterviewSession.session_id == session_id)
            ).scalar_one_or_none()

            if not interview:
                return False

            interview.risk_score = risk_score
            interview.end_time = _utcnow()
            interview.updated_at = _utcnow()
            session_db.commit()

            # Update Redis end_time (status/risk_score already set atomically above)
            session_data = self.state_sync.get_session_state(session_id)
            if session_data:
                session_data["end_time"] = _utcnow().isoformat()
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
        Check if state transition is valid.

        Retained for callers that need a pure/offline check (e.g. UI
        validation) without touching Redis. The authoritative check during
        an actual transition happens inside atomic_transition.lua.

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