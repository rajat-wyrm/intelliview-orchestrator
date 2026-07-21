"""
Retry Manager Module

Handles automatic retry logic with controlled backoff and attempt limiting.

Responsibilities:
- Schedule task retries with exponential backoff
- Track retry attempt counts per task
- Prevent infinite retry loops
- Manage retry metadata and state
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from orchestrator.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy options"""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    IMMEDIATE = "immediate"


class RetryManager:
    """
    Manages automatic retry logic for failed tasks with backoff strategies.

    Handles:
    - Tracking retry attempts per session
    - Calculating retry delays using exponential backoff
    - Limiting maximum retries to prevent infinite loops
    - Scheduling retry execution
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: int = 2,
        max_delay: int = 3600,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    ):
        """
        Initialize RetryManager

        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for backoff calculation (default: 2)
            max_delay: Maximum delay between retries in seconds (default: 3600 = 1 hour)
            strategy: Retry strategy to use (default: EXPONENTIAL_BACKOFF)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.redis_client = CacheManager()
        self.retry_key_prefix = "retry:"
        self.retry_count_key = "retry_count:"
        self.retry_scheduled_key = "retry_scheduled:"

        logger.info(
            f"RetryManager initialized: max_retries={max_retries}, "
            f"strategy={strategy.value}, base_delay={base_delay}s"
        )

    def can_retry(self, session_id: str) -> bool:
        """
        Check if a session can be retried (hasn't exceeded max attempts)

        Args:
            session_id: ID of session to check

        Returns:
            True if session can be retried, False if max attempts exceeded
        """
        try:
            retry_count = self.get_retry_count(session_id)
            can_retry = retry_count < self.max_retries

            if can_retry:
                logger.debug(f"Session {session_id} can retry ({retry_count}/{self.max_retries})")
            else:
                logger.warning(
                    f"Session {session_id} max retries exceeded ({retry_count}/{self.max_retries})"
                )

            return can_retry

        except Exception as e:
            logger.error(f"Error checking if can retry: {e!s}")
            return False

    def schedule_retry(self, session_id: str, delay_seconds: int | None = None) -> bool:
        """
        Schedule a retry for a failed task

        Calculates appropriate delay based on retry attempt count and strategy,
        then schedules the task for retry after that delay.

        Args:
            session_id: ID of session to retry
            delay_seconds: Optional override for delay (uses calculated if None)

        Returns:
            True if retry was scheduled, False otherwise
        """
        try:
            # Check if can retry
            if not self.can_retry(session_id):
                logger.warning(f"Cannot retry session {session_id}: max retries exceeded")
                return False

            # Get current retry count and increment
            retry_count = self.increment_retry(session_id)

            # Calculate delay if not provided
            if delay_seconds is None:
                delay_seconds = self._calculate_delay(retry_count)
            else:
                delay_seconds = min(delay_seconds, self.max_delay)

            logger.info(f"Scheduling retry for {session_id}: attempt {retry_count}, delay {delay_seconds}s")

            # Create retry record
            retry_data = {
                "session_id": session_id,
                "retry_count": retry_count,
                "scheduled_at": datetime.now(timezone.utc).isoformat(),
                "retry_after": (datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)).isoformat(),
                "delay_seconds": delay_seconds,
                "strategy": self.strategy.value,
            }

            if self.redis_client:
                # Store retry metadata
                retry_key = f"{self.retry_key_prefix}{session_id}"
                self.redis_client.set(
                    retry_key,
                    json.dumps(retry_data),
                    ex=delay_seconds + 600,
                )

                # Add to scheduled retry set (expire based on retry time)
                scheduled_key = f"{self.retry_scheduled_key}{session_id}"
                self.redis_client.set(
                    scheduled_key,
                    json.dumps(retry_data),
                    ex=delay_seconds,
                )

                logger.debug(f"Retry scheduled for {session_id} in {delay_seconds}s")

            return True

        except Exception as e:
            logger.error(f"Error scheduling retry for {session_id}: {e!s}")
            return False

    def _calculate_delay(self, retry_count: int) -> int:
        """
        Calculate delay for next retry based on strategy and attempt count

        Args:
            retry_count: Current retry attempt number (1-based)

        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            # Exponential: 2^retry_count seconds
            delay = self.base_delay**retry_count
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            # Linear: base_delay * retry_count seconds
            delay = self.base_delay * retry_count
        else:  # IMMEDIATE
            delay = 0

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        logger.debug(f"Calculated delay for retry {retry_count}: {delay}s using {self.strategy.value}")

        return delay

    def get_retry_count(self, session_id: str) -> int:
        """
        Get current retry attempt count for a session

        Args:
            session_id: ID of session

        Returns:
            Number of retry attempts (0 if no retries scheduled)
        """
        try:
            if not self.redis_client:
                return 0

            count_key = f"{self.retry_count_key}{session_id}"
            count = self.redis_client.get(count_key)

            return int(count) if count else 0

        except Exception as e:
            logger.warning(f"Error getting retry count: {e!s}")
            return 0

    def increment_retry(self, session_id: str) -> int:
        """
        Increment retry attempt count for a session

        Args:
            session_id: ID of session

        Returns:
            New retry count after increment
        """
        try:
            if not self.redis_client:
                return 1

            count_key = f"{self.retry_count_key}{session_id}"
            count = self.redis_client.incr(count_key)

            # Set TTL to 7 days
            self.redis_client.expire(count_key, 604800)

            logger.debug(f"Incremented retry count for {session_id} to {count}")

            return count

        except Exception as e:
            logger.error(f"Error incrementing retry count: {e!s}")
            return 1

    def get_retry_info(self, session_id: str) -> dict[str, Any]:
        """
        Get detailed retry information for a session

        Args:
            session_id: ID of session

        Returns:
            Dict with retry metadata and scheduling info
        """
        try:
            retry_count = self.get_retry_count(session_id)
            can_retry = self.can_retry(session_id)

            retry_data = None
            if self.redis_client:
                retry_key = f"{self.retry_key_prefix}{session_id}"
                retry_json = self.redis_client.get(retry_key)
                if retry_json:
                    retry_data = json.loads(retry_json)

            info = {
                "session_id": session_id,
                "current_retry_count": retry_count,
                "max_retries": self.max_retries,
                "can_retry": can_retry,
                "retry_strategy": self.strategy.value,
                "next_delay": self._calculate_delay(retry_count + 1) if can_retry else None,
            }

            if retry_data:
                info["scheduled_retry"] = retry_data

            return info

        except Exception as e:
            logger.error(f"Error getting retry info: {e!s}")
            return {}

    def get_scheduled_retries(self, limit: int = 100) -> list:
        """
        Get list of tasks scheduled for retry

        Args:
            limit: Maximum number to return

        Returns:
            List of retry scheduled entries
        """
        try:
            if not self.redis_client:
                return []

            retries = []
            cursor = 0
            count = 0

            while count < limit:
                cursor, keys = self.redis_client.scan(cursor, match=f"{self.retry_scheduled_key}*", count=100)

                for key in keys:
                    if count >= limit:
                        break

                    try:
                        data = self.redis_client.get(key)
                        if data:
                            retries.append(json.loads(data))
                            count += 1
                    except Exception:
                        continue

                if cursor == 0:
                    break

            return retries

        except Exception as e:
            logger.error(f"Error getting scheduled retries: {e!s}")
            return []

    def get_retry_statistics(self) -> dict[str, Any]:
        """
        Get aggregate retry statistics for the system

        Returns:
            Dict with retry metrics
        """
        try:
            scheduled = self.get_scheduled_retries(500)

            return {
                "total_scheduled_retries": len(scheduled),
                "scheduled_retries": scheduled[:10],
                "retry_strategy": self.strategy.value,
                "max_retries": self.max_retries,
                "base_delay": self.base_delay,
                "max_delay": self.max_delay,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting retry statistics: {e!s}")
            return {}
