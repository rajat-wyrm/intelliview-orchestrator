"""
Fault Manager Module

Handles system-level failures and coordinates recovery mechanisms.

Responsibilities:
- Detect failed sessions and workers
- Reassign failed tasks to healthy workers
- Log failure reasons and recovery actions
- Coordinate system recovery workflows
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from orchestrator.redis_client import get_redis_client
from orchestrator.retry_manager import RetryManager

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures that can occur"""

    WORKER_CRASH = "worker_crash"
    TASK_TIMEOUT = "task_timeout"
    TASK_EXCEPTION = "task_exception"
    NETWORK_ERROR = "network_error"
    PIPELINE_FAILURE = "pipeline_failure"
    SESSION_TIMEOUT = "session_timeout"


class FaultManager:
    """
    Manages fault detection and recovery operations for the distributed system.

    Handles:
    - Worker failure detection and removal
    - Task reassignment to healthy workers
    - Session recovery coordination
    - Failure logging and analysis
    """

    def __init__(self, debounce_time: int = 60):
        """
        Initialize FaultManager

        Args:
            debounce_time: Seconds to wait before treating alert as new (prevent spam)
        """
        self.debounce_time = debounce_time
        self.redis_client = get_redis_client()
        self.retry_manager = RetryManager()
        self.failure_log_prefix = "failure_log:"
        self.recovery_queue_prefix = "recovery_queue:"
        self.dead_letter_queue = "dead_letter_queue"

        logger.info(f"FaultManager initialized with debounce_time={debounce_time}s")

    def _create_redis_client(self) -> Any:
        """Create the shared Redis client used by the orchestrator."""
        return get_redis_client()

    def detect_failed_sessions(self, timeout_seconds: int = 1800) -> list[str]:
        """
        Detect sessions that have been stuck in PROCESSING state too long

        Args:
            timeout_seconds: Maximum processing time (default: 30 minutes)

        Returns:
            List of session_ids that appear to be failed
        """
        try:
            if not self.redis_client:
                return []

            failed_sessions = []

            # Scan for sessions stuck in PROCESSING
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match="session:*", count=100)

                for key in keys:
                    try:
                        session_data = self.redis_client.get(key)
                        if not session_data:
                            continue

                        session = json.loads(session_data)

                        # Check if session is stuck in PROCESSING
                        if session.get("status") == "PROCESSING":
                            start_time = session.get("start_time")
                            if start_time:
                                start_dt = datetime.fromisoformat(start_time)
                                elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds()

                                if elapsed > timeout_seconds:
                                    failed_sessions.append(session.get("session_id"))
                                    logger.warning(
                                        f"Session {session.get('session_id')} detected as stuck: "
                                        f"{elapsed}s > {timeout_seconds}s"
                                    )
                    except Exception as e:
                        logger.debug(f"Error processing session key {key}: {e!s}")
                        continue

                if cursor == 0:
                    break

            return failed_sessions

        except Exception as e:
            logger.error(f"Error detecting failed sessions: {e!s}")
            return []

    def handle_worker_failure(self, worker_id: str, failure_reason: str = "unknown") -> bool:
        """
        Handle failure of a worker node

        Triggers:
        - Worker removal from registry
        - Task reassignment to other workers
        - Failure logging

        Args:
            worker_id: ID of failed worker
            failure_reason: Description of failure cause

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            logger.critical(f"Worker {worker_id} has failed: {failure_reason}")

            # Log the failure
            self.log_failure(
                session_id=None,
                failure_type=FailureType.WORKER_CRASH,
                error_message=failure_reason,
                worker_id=worker_id,
            )

            # Get tasks assigned to this worker (from session tracker)
            tasks_to_reassign = self._get_worker_tasks(worker_id)

            logger.info(f"Found {len(tasks_to_reassign)} tasks to reassign from failed worker {worker_id}")

            # Reassign each task
            reassigned_count = 0
            for session_id in tasks_to_reassign:
                if self.reassign_task(session_id, original_worker=worker_id):
                    reassigned_count += 1

            logger.info(f"Successfully reassigned {reassigned_count}/{len(tasks_to_reassign)} tasks")

            return True

        except Exception as e:
            logger.error(f"Error handling worker failure: {e!s}")
            return False

    def reassign_task(self, session_id: str, original_worker: str | None = None) -> bool:
        """
        Reassign a failed task to another healthy worker

        Args:
            session_id: ID of session/task to reassign
            original_worker: Worker that previously had the task

        Returns:
            True if task was reassigned, False otherwise
        """
        try:
            logger.info(
                f"Reassigning task {session_id}" + (f" from {original_worker}" if original_worker else "")
            )

            # Add to recovery queue for retry
            recovery_key = f"{self.recovery_queue_prefix}{session_id}"

            recovery_data = {
                "session_id": session_id,
                "reassigned_at": datetime.now(timezone.utc).isoformat(),
                "original_worker": original_worker,
                "reassignment_count": self._increment_reassignment_count(session_id),
            }

            if self.redis_client:
                self.redis_client.set(
                    recovery_key,
                    json.dumps(recovery_data),
                    ex=86400,
                )
                logger.info(f"Task {session_id} added to recovery queue")

            return True

        except Exception as e:
            logger.error(f"Error reassigning task {session_id}: {e!s}")
            return False

    def _get_worker_tasks(self, worker_id: str) -> list[str]:
        """Get list of sessions/tasks assigned to a worker"""
        try:
            if not self.redis_client:
                return []

            tasks = []
            cursor = 0

            while True:
                cursor, keys = self.redis_client.scan(cursor, match="session:*", count=100)

                for key in keys:
                    try:
                        session_data = self.redis_client.get(key)
                        if session_data:
                            session = json.loads(session_data)
                            if session.get("assigned_worker") == worker_id:
                                tasks.append(session.get("session_id"))
                    except Exception:
                        continue

                if cursor == 0:
                    break

            return tasks
        except Exception as e:
            logger.error(f"Error getting worker tasks: {e!s}")
            return []

    def _increment_reassignment_count(self, session_id: str) -> int:
        """Track how many times a task has been reassigned"""
        try:
            if not self.redis_client:
                return 1

            key = f"reassignment_count:{session_id}"
            count = self.redis_client.incr(key)
            self.redis_client.expire(key, 86400)  # 24 hour TTL

            return count
        except Exception as e:
            logger.warning(f"Error incrementing reassignment count: {e!s}")
            return 1

    def log_failure(
        self,
        session_id: str | None,
        failure_type: FailureType,
        error_message: str,
        worker_id: str | None = None,
    ) -> bool:
        """
        Log a failure event for auditing and analysis

        Args:
            session_id: ID of failed session (may be None for worker/system failures)
            failure_type: Type of failure that occurred
            error_message: Detailed error description
            worker_id: ID of worker involved (if applicable)

        Returns:
            True if logged successfully
        """
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "failure_type": failure_type.value,
                "error_message": error_message,
                "worker_id": worker_id,
            }

            if self.redis_client:
                # Add to failure log list (keep last 1000 failures)
                log_key = f"{self.failure_log_prefix}{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
                self.redis_client.lpush(log_key, json.dumps(log_entry))
                self.redis_client.ltrim(log_key, 0, 999)
                self.redis_client.expire(log_key, 604800)  # 7 day TTL

            logger.info(f"Failure logged: {failure_type.value} - {error_message}")
            return True

        except Exception as e:
            logger.error(f"Error logging failure: {e!s}")
            return False

    def move_to_dead_letter_queue(self, session_id: str, reason: str) -> bool:
        """
        Move permanently failed task to dead letter queue for manual inspection

        Args:
            session_id: ID of session that permanently failed
            reason: Reason for moving to DLQ

        Returns:
            True if moved successfully
        """
        try:
            dlq_entry = {
                "session_id": session_id,
                "moved_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "retry_count": self.retry_manager.get_retry_count(session_id),
            }

            if self.redis_client:
                self.redis_client.lpush(self.dead_letter_queue, json.dumps(dlq_entry))
                logger.warning(f"Session {session_id} moved to dead letter queue: {reason}")

            return True

        except Exception as e:
            logger.error(f"Error moving to dead letter queue: {e!s}")
            return False

    def handle_failed_session(self, session_id: str, reason: str,) -> bool:
        """
        Handle a failed session.

        1. Log failure.
        2. Retry if possible.
        3. Otherwise move to DLQ.
        """

        logger.warning(
            "Handling failed session %s",
            session_id,
        )

        self.log_failure(
            session_id=session_id,
            failure_type=FailureType.TASK_EXCEPTION,
            error_message=reason,
        )

        scheduled = self.retry_manager.schedule_retry(session_id)

        if scheduled:
            return True

        logger.error(
            "Retries exhausted for %s",
            session_id,
        )

        moved = self.move_to_dead_letter_queue(session_id, reason)

        if moved:
            logger.warning("Session %s moved to Dead Letter Queue", session_id)
        else:
            logger.error("Failed to move %s to Dead Letter Queue", session_id)

        return False


    def get_recovery_queue(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get sessions queued for recovery/retry

        Args:
            limit: Maximum number to return

        Returns:
            List of recovery queue entries
        """
        try:
            if not self.redis_client:
                return []

            items = []
            cursor = 0
            count = 0

            while count < limit:
                cursor, keys = self.redis_client.scan(
                    cursor, match=f"{self.recovery_queue_prefix}*", count=100
                )

                for key in keys:
                    if count >= limit:
                        break

                    try:
                        data = self.redis_client.get(key)
                        if data:
                            items.append(json.loads(data))
                            count += 1
                    except Exception:
                        continue

                if cursor == 0:
                    break

            return items

        except Exception as e:
            logger.error(f"Error getting recovery queue: {e!s}")
            return []

    def get_failure_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get recent failure log entries

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of failure log entries
        """
        try:
            if not self.redis_client:
                return []

            entries = []

            # Get today's and yesterday's logs
            today = datetime.now(timezone.utc)
            for days_back in range(7):
                log_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
                log_key = f"{self.failure_log_prefix}{log_date}"

                # Get up to limit entries
                log_entries = self.redis_client.lrange(log_key, 0, limit - 1)

                for entry_json in log_entries:
                    try:
                        entries.append(json.loads(entry_json))
                        if len(entries) >= limit:
                            return entries[:limit]
                    except Exception:
                        continue

            return entries[:limit]

        except Exception as e:
            logger.error(f"Error getting failure log: {e!s}")
            return []

    def get_dead_letter_queue(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get entries from the dead letter queue

        Args:
            limit: Maximum number to return

        Returns:
            List of permanently failed sessions
        """
        try:
            if not self.redis_client:
                return []

            items = []
            entries = self.redis_client.lrange(self.dead_letter_queue, 0, limit - 1)

            for entry_json in entries:
                try:
                    items.append(json.loads(entry_json))
                except Exception:
                    continue

            return items

        except Exception as e:
            logger.error(f"Error getting dead letter queue: {e!s}")
            return []

    def get_system_fault_stats(self) -> dict[str, Any]:
        """
        Get aggregate fault statistics for the system

        Returns:
            Dict with fault metrics
        """
        try:
            failure_log = self.get_failure_log(500)
            recovery_queue = self.get_recovery_queue(500)
            dlq = self.get_dead_letter_queue(500)

            # Count by failure type
            failure_types = {}
            for entry in failure_log:
                ft = entry.get("failure_type", "unknown")
                failure_types[ft] = failure_types.get(ft, 0) + 1

            return {
                "total_failures": len(failure_log),
                "failures_by_type": failure_types,
                "recovery_queue_size": len(recovery_queue),
                "dead_letter_queue_size": len(dlq),
                "last_failures": failure_log[:10],
            }

        except Exception as e:
            logger.error(f"Error getting fault stats: {e!s}")
            return {}
