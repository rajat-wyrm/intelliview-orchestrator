"""
State Synchronizer
Manages state synchronization between Redis cache and PostgreSQL database

Strategy:
- Redis = fast cache for active sessions
- PostgreSQL = source of truth and persistent storage

Every important update:
1. Update Redis (fast cache)
2. Sync to PostgreSQL (persistent)
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from database.db import SessionLocal
from database.models import InterviewSession
from orchestrator.redis_client import get_redis_client, is_circuit_open
from orchestrator.session_payload import (
    deserialize_session_payload,
    serialize_session_payload,
)

logger = logging.getLogger(__name__)


class StateSynchronizer:
    """
    Synchronizes session state between Redis and PostgreSQL
    """

    # Redis key patterns
    SESSION_KEY_PREFIX = "session:"
    ACTIVE_SESSIONS_KEY = "active_sessions"
    SESSION_TTL = 86400  # 24 hours in seconds

    def __init__(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = get_redis_client()
            logger.info("Connected to Redis for state caching")
        except Exception as e:
            logger.error(f"Error initializing Redis connection: {e!s}")
            self.redis_client = None

    def set_session_state(self, session_id: str, session_data: dict[str, Any]) -> bool:
        """
        Store session state in Redis cache

        Args:
            session_id: Session identifier
            session_data: Session data dictionary

        Returns:
            bool: True if successful
        """
        if not self.redis_client:
            logger.warning(
                f"Redis not available, skipping cache for session {session_id}"
            )
            return False

        try:
            key = f"{self.SESSION_KEY_PREFIX}{session_id}"
            value = serialize_session_payload(session_data)

            # Set with TTL
            self.redis_client.set(key, value, ex=self.SESSION_TTL)

            # Add to active sessions set
            self.redis_client.sadd(self.ACTIVE_SESSIONS_KEY, session_id)

            logger.debug(f"Cached session state for {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error setting session state in Redis: {e!s}")
            return False

    def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve session state from Redis cache.

        Falls back to PostgreSQL when the Redis circuit breaker is OPEN
        or when a Redis read raises an exception.

        Args:
            session_id: Session identifier

        Returns:
            dict: Session data or None if not found
        """
        if is_circuit_open() or not self.redis_client:
            logger.info(f"Redis unavailable, reading session {session_id} from PG")
            return self._read_session_from_db(session_id)

        try:
            key = f"{self.SESSION_KEY_PREFIX}{session_id}"
            value = self.redis_client.get(key)

            if not value:
                logger.debug(f"Session {session_id} not found in cache")
                return None

            session_data = deserialize_session_payload(value)
            logger.debug(f"Retrieved cached session state for {session_id}")
            return session_data

        except Exception as e:
            logger.warning(f"Redis read failed, falling back to PG: {e!s}")
            return self._read_session_from_db(session_id)

    def delete_session_state(self, session_id: str) -> bool:
        """
        Delete session state from Redis cache

        Args:
            session_id: Session identifier

        Returns:
            bool: True if successful
        """
        if not self.redis_client:
            return False

        try:
            key = f"{self.SESSION_KEY_PREFIX}{session_id}"
            self.redis_client.delete(key)
            self.redis_client.srem(self.ACTIVE_SESSIONS_KEY, session_id)
            logger.debug(f"Deleted cached session state for {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting session state from Redis: {e!s}")
            return False

    def get_active_sessions(self) -> list:
        """
        Get all active session IDs from cache.

        Falls back to PostgreSQL when the Redis circuit breaker is OPEN
        or when a Redis read raises an exception.

        Returns:
            list: List of active session IDs
        """
        if is_circuit_open() or not self.redis_client:
            logger.info("Redis unavailable, reading active sessions from PG")
            return self._read_active_sessions_from_db()

        try:
            active_sessions = self.redis_client.smembers(self.ACTIVE_SESSIONS_KEY)
            logger.debug(f"Retrieved {len(active_sessions)} active sessions from cache")
            return list(active_sessions)

        except Exception as e:
            logger.warning(f"Redis read failed, falling back to PG: {e!s}")
            return self._read_active_sessions_from_db()

    def _read_session_from_db(self, session_id: str) -> dict[str, Any] | None:
        """Direct PG read — used when Redis is unavailable."""
        session_db = SessionLocal()
        try:
            interview = session_db.execute(
                select(InterviewSession).where(
                    InterviewSession.session_id == session_id
                )
            ).scalar_one_or_none()

            if not interview:
                return None

            return {
                "session_id": interview.session_id,
                "candidate_id": interview.candidate_id,
                "language": interview.language,
                "status": interview.status,
                "risk_score": interview.risk_score,
                "assigned_node": interview.assigned_node,
                "start_time": (
                    interview.start_time.isoformat() if interview.start_time else None
                ),
                "end_time": (
                    interview.end_time.isoformat() if interview.end_time else None
                ),
                "created_at": (
                    interview.created_at.isoformat() if interview.created_at else None
                ),
                "updated_at": (
                    interview.updated_at.isoformat() if interview.updated_at else None
                ),
                "video_analysis": interview.video_analysis,
                "audio_analysis": interview.audio_analysis,
                "evaluation_analysis": interview.evaluation_analysis,
            }
        except Exception as e:
            logger.error(f"PG fallback read failed for session {session_id}: {e!s}")
            return None
        finally:
            session_db.close()

    def _read_active_sessions_from_db(self) -> list:
        """Direct PG read for active session IDs — used when Redis is unavailable."""
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
            rows = (
                session_db.execute(
                    select(InterviewSession.session_id).where(
                        InterviewSession.status.in_(active_statuses)
                    )
                )
                .scalars()
                .all()
            )
            return list(rows)
        except Exception as e:
            logger.error(f"PG fallback read failed for active sessions: {e!s}")
            return []
        finally:
            session_db.close()

    def sync_state_to_db(self, session_id: str, session_data: dict[str, Any]) -> bool:
        """
        Sync session state from cache to database

        Args:
            session_id: Session identifier
            session_data: Session data to sync

        Returns:
            bool: True if successful
        """
        try:
            # Force-load the session row into the DB if it's only in Redis.

            from database.db import SessionLocal
            from database.models import InterviewSession

            session_db = SessionLocal()
            try:
                interview = session_db.execute(
                    select(InterviewSession).where(
                        InterviewSession.session_id == session_id
                    )
                ).scalar_one_or_none()

                if not interview:
                    logger.warning(f"Session {session_id} not found in database")
                    return False

                # Update fields from cache data
                if "status" in session_data:
                    interview.status = session_data["status"]

                if (
                    "risk_score" in session_data
                    and session_data["risk_score"] is not None
                ):
                    interview.risk_score = session_data["risk_score"]

                if "video_analysis" in session_data:
                    interview.video_analysis = session_data["video_analysis"]

                if "audio_analysis" in session_data:
                    interview.audio_analysis = session_data["audio_analysis"]

                if "evaluation_analysis" in session_data:
                    interview.evaluation_analysis = session_data["evaluation_analysis"]

                if "feedback_generated" in session_data:
                    interview.feedback_generated = session_data["feedback_generated"]

                interview.updated_at = datetime.now(timezone.utc)
                session_db.commit()

                logger.info(f"Synced session {session_id} state to database")
                return True

            except Exception as e:
                logger.error(f"Error syncing to database: {e!s}")
                session_db.rollback()
                return False
            finally:
                session_db.close()

        except Exception as e:
            logger.error(f"Error in sync_state_to_db: {e!s}")
            return False

    def clear_cache(self) -> bool:
        """
        Clear all session cache from Redis

        Returns:
            bool: True if successful
        """
        if not self.redis_client:
            return False

        try:
            # Get all active sessions
            active_sessions = self.redis_client.smembers(self.ACTIVE_SESSIONS_KEY)

            # Delete session cache entries
            for session_id in active_sessions:
                key = f"{self.SESSION_KEY_PREFIX}{session_id}"
                self.redis_client.delete(key)

            # Delete active sessions set
            self.redis_client.delete(self.ACTIVE_SESSIONS_KEY)

            logger.info(f"Cleared cache for {len(active_sessions)} sessions")
            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {e!s}")
            return False

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics

        Returns:
            dict: Cache statistics
        """
        if not self.redis_client:
            return {"status": "Redis not available"}

        try:
            active_sessions = self.redis_client.smembers(self.ACTIVE_SESSIONS_KEY)
            info = self.redis_client.info()

            return {
                "status": "connected",
                "active_sessions_count": len(active_sessions),
                "redis_memory_used": info.get("used_memory_human", "unknown"),
                "redis_connected_clients": info.get("connected_clients", "unknown"),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e!s}")
            return {"status": "error", "error": str(e)}
