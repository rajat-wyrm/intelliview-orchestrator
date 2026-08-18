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

import logging
import socket
import time
from datetime import datetime, timezone

from celery import chord, group
from sqlalchemy import select

from database.db import SessionLocal
from database.models import InterviewSession
from monitoring.prometheus_metrics import (
    FAILURE_COUNT,
    PIPELINE_LATENCY,
    POSTGRES_HEALTH,
    REDIS_HEALTH,
    RISK_SCORE,
    WORKERS_HEALTHY,
)
from orchestrator.session_manager import SessionManager
from orchestrator.state_sync import StateSynchronizer
from orchestrator.worker_registry import WorkerRegistry
from workers.celery_app import celery_app
from workers.evaluation_pipeline import evaluate_answers
from workers.risk_engine import RiskScoringEngine

logger = logging.getLogger(__name__)

session_manager = SessionManager()
state_sync = StateSynchronizer()


# ---------------------------------------------------------------------------
# Helper methods
# ---------------------------------------------------------------------------


def _get_session_state(session_id: str) -> dict:
    """Get session state from the state synchronizer."""
    state = state_sync.get_session_state(session_id)
    return state or {}


def _update_session_state(session_id: str, **kwargs):
    """Update session state in the state synchronizer."""
    state = _get_session_state(session_id)
    state.update(kwargs)
    state_sync.set_session_state(session_id, state)


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
    from workers.video_pipeline import run_video_analysis

    logger.info("Starting video analysis stage for session %s", session_id)
    start = time.perf_counter()

    _update_infra_health(True)

    result = run_video_analysis(session_id)

    latency = time.perf_counter() - start
    PIPELINE_LATENCY.labels(stage="video").observe(latency)

    _update_session_state(
        session_id,
        video_completed=True,
        video_result=result,
    )

    logger.info("Video analysis stage completed in %.2fs", latency)

    return result


@celery_app.task(bind=True, max_retries=3, name="workers.tasks._run_audio")
def _run_audio(self, session_id: str) -> dict:
    from workers.audio_pipeline import run_audio_analysis

    logger.info("Starting audio analysis stage for session %s", session_id)
    start = time.perf_counter()

    _update_infra_health(True)

    result = run_audio_analysis(session_id)

    latency = time.perf_counter() - start
    PIPELINE_LATENCY.labels(stage="audio").observe(latency)

    _update_session_state(
        session_id,
        audio_completed=True,
        audio_result=result,
    )

    logger.info("Audio analysis stage completed in %.2fs", latency)

    return result


# ---------------------------------------------------------------------------
# Callback after parallel video + audio complete
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, name="workers.tasks._after_parallel")
def _after_parallel(self, results: list, session_id: str):
    """Runs after video + audio group completes; then evaluation + risk.

    Chord callback: first argument is the list of results from the parallel
    group [video_result, audio_result], followed by the session_id from .s().
    """
    video_result, audio_result = results[0], results[1]
    try:
        logger.info("Parallel video+audio done for %s - running evaluation", session_id)
        session_manager.update_session_status(
            session_id, session_manager.EVALUATING, {"stage": "evaluation"}
        )

        start = time.perf_counter()
        evaluation_result = evaluate_answers(session_id)

        latency = time.perf_counter() - start
        PIPELINE_LATENCY.labels(stage="evaluation").observe(latency)
        logger.info(
            "Answer evaluation completed for session %s in %.2fs", session_id, latency
        )

        risk_report = RiskScoringEngine.generate_risk_report(
            session_id, video_result, audio_result, evaluation_result
        )
        final_risk_score = risk_report["final_risk_score"]
        RISK_SCORE.observe(final_risk_score)

        risk_classification = risk_report["risk_classification"]
        logger.info(
            "Risk report: %s (score: %s)", risk_classification, final_risk_score
        )

        now = datetime.now(timezone.utc)
        db_session = SessionLocal()
        try:
            interview = db_session.execute(
                select(InterviewSession).where(
                    InterviewSession.session_id == session_id
                )
            ).scalar_one_or_none()
            if interview:
                interview.risk_score = final_risk_score
                interview.video_analysis = video_result
                interview.audio_analysis = audio_result
                interview.evaluation_analysis = evaluation_result
                interview.end_time = now
                interview.updated_at = now
                db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

        session_manager.mark_session_completed(session_id, final_risk_score)
        state_sync.delete_session_state(session_id)
        logger.info("Successfully completed processing for session %s", session_id)

    except Exception as exc:
        logger.error(
            "Post-parallel stage failed for %s: %s", session_id, exc, exc_info=True
        )
        FAILURE_COUNT.labels(failure_type="post_parallel_error").inc()
        session_manager.mark_session_failed(
            session_id, f"Post-parallel stage failed: {exc}"
        )


# ---------------------------------------------------------------------------
# Main entry-point task
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True, max_retries=3, name="workers.tasks.process_interview_session"
)
def process_interview_session(self, session_id):
    """
    Video and audio run in parallel via a Celery group; the evaluation
    and risk scoring stages run sequentially after both complete.
    """
    task_name = self.name
    start_time = time.perf_counter()

    worker_hostname = socket.gethostname()
    registry = WorkerRegistry()

    try:
        worker_hostname = socket.gethostname()
        logger.info(
            "Worker %s starting interview session: %s", worker_hostname, session_id
        )

        db_session = SessionLocal()
        try:
            interview = db_session.execute(
                select(InterviewSession).where(
                    InterviewSession.session_id == session_id
                )
            ).scalar_one_or_none()

            if interview is None:
                logger.error("Session %s not found in DB", session_id)
                return {
                    "session_id": session_id,
                    "status": "missing",
                }

            if interview.status == "FAILED":
                interview.status = "QUEUED"
                db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

        # Redelivery guard: if the session is already in VIDEO_PROCESSING
        # and started recently, this is a duplicate delivery from a lost
        # worker - skip it.
        if interview and interview.status == session_manager.VIDEO_PROCESSING:
            if interview.start_time:
                start_time = interview.start_time
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - start_time).total_seconds() < 1800:
                    logger.info(
                        "Skipping duplicate delivery for session %s (already processing)",
                        session_id,
                    )
                    return {
                        "session_id": session_id,
                        "status": "skipped_duplicate_delivery",
                    }

        session_manager.update_session_status(
            session_id,
            session_manager.PROCESSING,
            {"assigned_node": worker_hostname},
        )

        db_session = SessionLocal()
        try:
            interview = db_session.execute(
                select(InterviewSession).where(
                    InterviewSession.session_id == session_id
                )
            ).scalar_one_or_none()

            if interview:
                interview.assigned_node = worker_hostname
                interview.start_time = datetime.now(timezone.utc)
                db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

        # Parallel execution via chord: group runs video+audio, then callback runs _after_parallel
        session_manager.update_session_status(
            session_id,
            session_manager.VIDEO_PROCESSING,
            {"stage": "parallel_video_audio"},
        )

        parallel_group = group(
            _run_video.s(session_id),
            _run_audio.s(session_id),
        )

        # Chord: runs parallel_group, then _after_parallel with results.
        # chord(self)(callback) applies the chord and returns an AsyncResult.
        chord(parallel_group)(_after_parallel.s(session_id))

        # Record successful task initiation
        registry.record_success(worker_hostname)

        return {
            "session_id": session_id,
            "status": "processing_parallel",
            "processed_by": worker_hostname,
        }

    except Exception as exc:
        # Record worker failure
        registry.record_failure(worker_hostname)

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
