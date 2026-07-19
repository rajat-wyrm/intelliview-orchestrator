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
from monitoring.prometheus_metrics import (
    SESSIONS_ACTIVE,
    SESSIONS_COMPLETED,
    SESSIONS_FAILED,
)
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

        # StateSynchronizer.redis_client may be a raw redis.Redis client, a
        # wrapper around one, or None if the connection failed at startup.
        # register_script() is a redis-py method; if redis_client is some
        # custom wrapper that doesn't expose it (or expose the underlying
        # client), we must not let that crash SessionManager construction —
        # every caller of SessionManager() would break. Instead we disable
        # the atomic cache update and log loudly, so this is visible without
        # taking down the whole service. PostgreSQL remains the source of
        # truth regardless, so this only affects cache freshness, not
        # correctness.
        #
        # TODO: once redis_client.py's wrapper is confirmed to expose the
        # raw client (e.g. via a `.client` / `.raw` attribute, or by adding
        # a passthrough register_script method on the wrapper itself), point
        # this at that instead of assuming self.state_sync.redis_client IS
        # the raw client.
        self._redis = self.state_sync.redis_client.client
        self._transition_script = None
        if self._redis is not None:
            try:
                self._transition_script = self._redis.register_script(_LUA_SCRIPT_PATH.read_text())
            except AttributeError:
                logger.error(
                    "redis_client does not support register_script() (wrapper type: %s); "
                    "atomic cache updates are disabled until this is resolved",
                    type(self._redis).__name__,
                )
        else:
            logger.error("Redis unavailable at startup; atomic cache updates are disabled")

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
        Update session status with validation.

        PostgreSQL is the source of truth: the current status is read from
        the database, validated against VALID_TRANSITIONS, and the new
        status is committed there first — this decision-making is unchanged
        from before.

        Only after that commit succeeds do we update the Redis cache, using
        atomic_transition.lua to apply the already-approved change in a
        single atomic step. This replaces the previous cache-update pattern
        (a separate get_session_state() read followed by a separate
        set_session_state() write), which could race under concurrent
        updates and let one cache write silently clobber another with stale
        data. Redis does not decide validity here; it only mirrors what
        Postgres already committed.

        Args:
            session_id: Session identifier
            new_status: New status to set
            metadata: Optional additional data to store

        Returns:
            bool: True if successful, False otherwise
        """
        metadata = metadata or {}

        session_db = SessionLocal()
        try:
            interview = session_db.execute(
                select(InterviewSession).where(InterviewSession.session_id == session_id)
            ).scalar_one_or_none()

            if not interview:
                logger.error(f"Session {session_id} not found")
                return False

            current_status = interview.status

            if not self._is_valid_transition(current_status, new_status):
                logger.warning(
                    f"Invalid state transition: {current_status} -> {new_status} for session {session_id}"
                )
                return False

            logger.info(f"Updating session {session_id} status: {current_status} -> {new_status}")
            interview.status = new_status
            interview.updated_at = _utcnow()
            session_db.commit()

            self._update_cache_atomic(session_id, new_status, metadata)

            risk_score = interview.risk_score

            if new_status == self.COMPLETED:
                SESSIONS_COMPLETED.inc()
                SESSIONS_ACTIVE.dec()

            elif new_status == self.FAILED:
                SESSIONS_FAILED.inc()
                SESSIONS_ACTIVE.dec()

            logger.info(f"Session {session_id} status updated to {new_status}")

            # Broadcast the transition to dashboard WebSocket clients (non-blocking).
            self._broadcast_status(session_id, new_status, risk_score, metadata or {})

            return True
        except Exception as e:
            logger.error(f"Error updating session status: {e!s}")
            session_db.rollback()
            return False
        finally:
            session_db.close()

        # PostgreSQL commit succeeded — now atomically sync the cache so
        # concurrent cache writers can't produce a lost update.

        logger.info(f"Session {session_id} status updated to {new_status}")

        # Broadcast the transition to dashboard WebSocket clients (non-blocking).
        self._broadcast_status(session_id, new_status, risk_score, metadata)

        return True

    def _update_cache_atomic(self, session_id: str, new_status: str, metadata: dict[str, Any]) -> None:
        """
        Atomically apply an already-approved status/metadata change to the
        Redis-cached session state via atomic_transition.lua.

        This is best-effort and deliberately does not affect the return
        value of the caller: PostgreSQL has already committed by the time
        this runs, so a cache failure here means a stale or missing cache
        entry (which get_session() naturally falls back to the database
        for), not a correctness bug. There is nothing to "revert" here,
        since Redis never made the authoritative decision in the first
        place — Postgres did, before this was ever called.

        Args:
            session_id: Session identifier
            new_status: The status PostgreSQL already committed
            metadata: Optional additional data to merge into the cache
        """
        if self._transition_script is None:
            logger.warning(
                f"Atomic cache update unavailable for {session_id}; "
                "cache may be stale until the next read falls back to the database"
            )
            return

        try:
            raw_result = self._transition_script(
                keys=[self._session_key(session_id)],
                args=[new_status, _utcnow().isoformat(), json.dumps(metadata, default=str)],
            )
            result = json.loads(raw_result)
            if result["status"] != "ok":
                logger.warning(
                    f"Cache update for {session_id} returned '{result['status']}'; "
                    "cache may be stale until the next read falls back to the database"
                )
        except RedisError as e:
            logger.error(f"Redis error updating cache for {session_id}: {e!s}")

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
        from monitoring.prometheus_metrics import (
            SESSIONS_ACTIVE,
            SESSIONS_FAILED,
        )

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

            if not self._is_valid_transition(interview.status, self.COMPLETED):
                logger.warning(
                    f"Invalid state transition: {interview.status} -> {self.COMPLETED} "
                    f"for session {session_id}"
                )
                return False

            interview.status = self.COMPLETED
            interview.risk_score = risk_score
            interview.end_time = _utcnow()
            interview.updated_at = _utcnow()

            from monitoring.prometheus_metrics import (
                RISK_SCORE,
                SESSION_PROCESSING_DURATION,
                SESSIONS_ACTIVE,
                SESSIONS_COMPLETED,
            )

            session_db.commit()
            SESSIONS_COMPLETED.inc()
            print("SESSIONS_COMPLETED =", SESSIONS_COMPLETED._value.get())
            SESSIONS_ACTIVE.dec()

            RISK_SCORE.observe(risk_score)

            if interview.start_time:
                duration = (interview.end_time - interview.start_time).total_seconds()
                SESSION_PROCESSING_DURATION.observe(duration)

        except Exception as e:
            logger.error(f"Error marking session completed: {e!s}")
            session_db.rollback()
            return False
        finally:
            session_db.close()

        # PostgreSQL commit succeeded — atomically sync status, risk_score,
        # and end_time into the cache in one merge instead of a separate
        # get-then-set round trip.
        self._update_cache_atomic(
            session_id,
            self.COMPLETED,
            {"risk_score": risk_score, "end_time": _utcnow().isoformat()},
        )

        logger.info(f"Session {session_id} marked as completed")
        return True

    def _is_valid_transition(self, current_status: str, new_status: str) -> bool:
        """
        Check if state transition is valid against VALID_TRANSITIONS.

        This is the single source of truth for transition validity — used
        directly by update_session_status()/mark_session_completed() against
        PostgreSQL's current state, and safe to call standalone (e.g. for
        UI validation) since it touches neither Redis nor the database.

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
