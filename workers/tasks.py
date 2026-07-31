"""Celery Tasks for Interview Processing.

Pipeline:
  1. QUEUED  -> VIDEO_PROCESSING -> AUDIO_PROCESSING -> EVALUATING
  2. Each stage persists to Postgres and the Redis cache.
  3. Final stage writes the risk report and marks the session COMPLETED.
  4. On exception: `self.retry(...)` triggers exponential backoff via
     Celery. The session is NOT marked FAILED here — only after Celery
     has exhausted retries (see `celery_app.task_failure` signal).
"""

from __future__ import annotations

import json
import logging
import socket
from datetime import datetime, timezone

from celery import chord, group
from sqlalchemy import select

from database.db import SessionLocal
from database.models import InterviewSession
from metrics.prometheus_metrics import (
    CELERY_ACTIVE_TASKS,
    CELERY_TASK_RUNTIME,
    CELERY_TASKS_PROCESSED_TOTAL,  # Updated custom counter
    FAILURE_COUNT,
    PIPELINE_LATENCY,
    POSTGRES_HEALTH,
    QUEUE_DEPTH,
    REDIS_HEALTH,
    RETRY_COUNT,
    RISK_SCORE,
    WORKERS_HEALTHY,
)
from orchestrator.redis_client import get_redis_client
from orchestrator.session_manager import SessionManager
from orchestrator.state_sync import StateSynchronizer
from workers.celery_app import celery_app
from workers.evaluation_pipeline import evaluate_answers
from workers.risk_engine import RiskScoringEngine

logger = logging.getLogger(__name__)

session_manager = SessionManager()
state_sync = StateSynchronizer()

# Redelivered tasks (task_acks_late + task_reject_on_worker_lost) re-run
# from the top with the same session_id while the DB row may still be
# active. task_time_limit tells us when a stuck attempt is provably dead.
REDELIVERY_STALE_AFTER_SECONDS = celery_app.conf.task_time_limit + 60

ACTIVE_PROCESSING_STATUSES = {
    session_manager.PROCESSING,
    session_manager.VIDEO_PROCESSING,
    getattr(session_manager, "AUDIO_PROCESSING", "AUDIO_PROCESSING"),
    session_manager.EVALUATING,
}


# ---------------------------------------------------------------------------
# Helper to set background infrastructure health states
# ---------------------------------------------------------------------------


def _update_infra_health(healthy: bool = True):
    """Sets system infrastructure gauges to reflect live operations."""
    state = 1.0 if healthy else 0.0
    WORKERS_HEALTHY.set(state)
    REDIS_HEALTH.set(state)
    POSTGRES_HEALTH.set(state)


# ---------------------------------------------------------------------------
# Individual stage tasks
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, name="workers.tasks._run_video")
def _run_video(self, session_id: str) -> dict:
    """Video analysis stage."""
    from workers.video_pipeline import run_video_analysis

    return run_video_analysis(session_id)


@celery_app.task(bind=True, max_retries=3, name="workers.tasks._run_audio")
def _run_audio(self, session_id: str) -> dict:
    """Audio analysis stage."""
    from workers.audio_pipeline import run_audio_analysis

    return run_audio_analysis(session_id)


# ---------------------------------------------------------------------------
# Callback after parallel video + audio complete
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, name="workers.tasks._after_parallel")
def _after_parallel(self, results: list, session_id: str):
    """Runs after video + audio group completes; then evaluation + risk.

    Invoked by the chord once both ``_run_video`` and ``_run_audio``
    succeed.  ``results`` is a two-element list from the group --
    ``[video_result, audio_result]``.
    """
    try:
        video_result, audio_result = results  # unpack chord group results
        logger.info("Parallel video+audio done for %s - running evaluation", session_id)

        session_manager.update_session_status(session_id, session_manager.EVALUATING, {"stage": "evaluation"})
        evaluation_result = evaluate_answers(session_id)
        logger.info("Answer evaluation completed for session %s", session_id)

        risk_report = RiskScoringEngine.generate_risk_report(
            session_id, video_result, audio_result, evaluation_result
        )
        final_risk_score = risk_report["final_risk_score"]
        risk_classification = risk_report["risk_classification"]
        logger.info("Risk report: %s (score: %s)", risk_classification, final_risk_score)

        now = datetime.now(timezone.utc)
        db_session = SessionLocal()
        try:
            interview = db_session.execute(
                select(InterviewSession).where(InterviewSession.session_id == session_id)
            ).scalar_one_or_none()
            if interview:
                interview.risk_score = final_risk_score
                interview.video_analysis = video_result
                interview.audio_analysis = audio_result
                interview.evaluation_analysis = evaluation_result
                interview.end_time = now
                interview.updated_at = now
                db_session.commit()
        finally:
            db_session.close()

        session_manager.mark_session_completed(session_id, final_risk_score)
        state_sync.delete_session_state(session_id)

        logger.info("Successfully completed processing for session %s", session_id)
    except Exception as exc:
        logger.error("Post-parallel stage failed for %s: %s", session_id, exc, exc_info=True)
        session_manager.mark_session_failed(session_id, f"Post-parallel stage failed: {exc}")


# ---------------------------------------------------------------------------
# Main entry-point task
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, name="workers.tasks.process_interview_session")
def process_interview_session(self, session_id: str, priority: str = "medium"):
    logger.info("Session = %s | Priority = %s", session_id, priority)
    
    # Determine priority queue for downstream child tasks
    priority_clean = str(priority).lower() if priority else "medium"
    if priority_clean not in ("high", "medium", "low"):
        priority_clean = "medium"
    target_queue = f"{priority_clean}_priority"

    task_name = self.name
    start_time = time.perf_counter()

    # Track currently active task tracking gauge
    CELERY_ACTIVE_TASKS.labels(task_name=task_name).inc()

    # Assert worker and backend services are active
    _update_infra_health(True)

    try:
        logger.info("Worker %s starting interview session: %s", worker_hostname, session_id)

        db_session = SessionLocal()
        try:
            interview = db_session.execute(
                select(InterviewSession).where(InterviewSession.session_id == session_id)
            ).scalar_one_or_none()
            if interview is None:
                logger.error("Session %s not found in DB", session_id)
                return {"session_id": session_id, "status": "missing"}
            if interview.status == "FAILED":
                interview.status = "QUEUED"
                db_session.commit()
        finally:
            db_session.close()

        session_manager.update_session_status(
            session_id, session_manager.PROCESSING, {"assigned_node": worker_hostname}
        )

        db_session = SessionLocal()
        try:
            interview = db_session.execute(
                select(InterviewSession).where(InterviewSession.session_id == session_id)
            ).scalar_one_or_none()
            if interview:
                interview.assigned_node = worker_hostname
                interview.start_time = datetime.now(timezone.utc)
                db_session.commit()
        finally:
            db_session.close()

        # Parallel: video + audio via Celery group
        session_manager.update_session_status(
            session_id, session_manager.VIDEO_PROCESSING, {"stage": "parallel_video_audio"}
        )

        # Use chord to dispatch video + audio in parallel and chain into
        # _after_parallel once both complete — avoids blocking the solo
        # worker pool (group + result.get() would deadlock).
        # Target queue is passed so child tasks match the parent session priority.
        parallel_header = group(
            _run_video.s(session_id).set(queue=target_queue),
            _run_audio.s(session_id).set(queue=target_queue),
        )
        chord(parallel_header)(_after_parallel.s(session_id).set(queue=target_queue))

        logger.info("Dispatched parallel video+audio for session %s on queue %s", session_id, target_queue)

        return {
            "session_id": session_id,
            "status": "processing_parallel",
            "processed_by": worker_hostname,
            "priority": priority_clean,
        }

    except Exception as exc:
        retry_delay = 2 ** (self.request.retries + 1)
        logger.warning(
            "Task for session %s failed (attempt %d/3), retrying in %ds: %s",
            session_id,
            self.request.retries + 1,
            retry_delay,
            exc,
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=retry_delay)


# ---------------------------------------------------------------------------
# Celery Beat: periodic retry scanner
# ---------------------------------------------------------------------------


@celery_app.task(name="workers.tasks.scan_and_dispatch_retries")
def scan_and_dispatch_retries():
    """Scan Redis for retry entries whose ``retry_after`` timestamp has
    passed and re-dispatch the corresponding session through the normal
    scheduling path.  Runs every 60 s via Celery Beat.
    """
    redis_client = get_redis_client()

    retry_scheduled_prefix = "retry_scheduled:"

    try:
        cursor = 0
        dispatched = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=f"{retry_scheduled_prefix}*", count=50)
            for key in keys:
                try:
                    raw = redis_client.get(key)
                    if not raw:
                        continue
                    data = json.loads(raw)
                    retry_after_str = data.get("retry_after")
                    if not retry_after_str:
                        continue
                    retry_after = datetime.fromisoformat(retry_after_str)
                    if retry_after.tzinfo is None:
                        retry_after = retry_after.replace(tzinfo=timezone.utc)

                    if datetime.now(timezone.utc) < retry_after:
                        continue  # not due yet

                    session_id = data.get("session_id")
                    if not session_id:
                        continue

                    # Dispatch via the normal scheduling path
                    from orchestrator.scheduler import Scheduler, TaskPriority

                    scheduler = Scheduler()
                    scheduler.schedule_task(session_id, priority=TaskPriority.MEDIUM)
                    dispatched += 1

                    # Clean up the scheduled key
                    redis_client.delete(key)
                    logger.info("Dispatched retry for session %s", session_id)

                except Exception as exc:
                    logger.debug("Error processing retry key %s: %s", key, exc)
                    continue

            if cursor == 0:
                break

        if dispatched:
            logger.info("Scan-and-dispatch complete: %d retries dispatched", dispatched)

    except Exception as exc:
        logger.error("scan_and_dispatch_retries failed: %s", exc)