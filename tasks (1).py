"""Celery tasks that drive the interview processing pipeline.

Here's how a session moves through the system:
  QUEUED -> VIDEO_PROCESSING -> AUDIO_PROCESSING -> EVALUATING -> COMPLETED

Every stage writes its progress to Postgres and Redis as it goes, so we
always know where a session is if something goes wrong. The last stage
puts together the risk report and closes out the session.

If a task blows up, we don't just give up and mark it FAILED right away.
`self.retry(...)` kicks in and Celery backs off, waiting a bit longer each
time before trying again. We only flip the session to FAILED once Celery
has actually run out of retries (that part lives in the
`celery_app.task_failure` signal handler, not here).
"""

from __future__ import annotations

import json
import logging
import socket
from datetime import datetime, timezone

from celery import group
from sqlalchemy import select

from database.db import SessionLocal
from database.models import InterviewSession
from orchestrator.redis_client import get_redis_client
from orchestrator.session_manager import SessionManager
from orchestrator.state_sync import StateSynchronizer
from workers.celery_app import celery_app
from workers.evaluation_pipeline import evaluate_answers
from workers.risk_engine import RiskScoringEngine

logger = logging.getLogger(__name__)

session_manager = SessionManager()
state_sync = StateSynchronizer()


# ---------------------------------------------------------------------------
# The two stages that run side by side: video and audio
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    max_retries=3,
    # If video processing fails, don't hammer it again right away -
    # back off and give it some breathing room first.
    retry_backoff=True,       # roughly doubles the wait each retry (1s, 2s, 4s...)
    retry_backoff_max=120,    # but cap it at 2 minutes so it doesn't drag on forever
    retry_jitter=True,        # shake up the timing a bit so retries don't all land together
    name="workers.tasks._run_video",
)
def _run_video(self, session_id: str) -> dict:
    """Runs the video analysis for a session."""
    from workers.video_pipeline import run_video_analysis

    return run_video_analysis(session_id)


@celery_app.task(
    bind=True,
    max_retries=3,
    # Same backoff behavior as the video task above.
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    name="workers.tasks._run_audio",
)
def _run_audio(self, session_id: str) -> dict:
    """Runs the audio analysis for a session."""
    from workers.audio_pipeline import run_audio_analysis

    return run_audio_analysis(session_id)


# ---------------------------------------------------------------------------
# Once video and audio are both done, this picks up the rest of the work
# ---------------------------------------------------------------------------


@celery_app.task(name="workers.tasks._after_parallel")
def _after_parallel(session_id: str, video_result: dict, audio_result: dict):
    """Once video and audio results are both in, run the evaluation and
    build the risk report."""
    try:
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
# This is where everything kicks off for a session
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    max_retries=3,
    # Same backoff setup as the video/audio tasks - fail, wait, try again,
    # wait a bit longer next time.
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    name="workers.tasks.process_interview_session",
)
def process_interview_session(self, session_id):
    """Kicks off video, audio, evaluation, and risk scoring for one
    interview session.

    Video and audio run at the same time (Celery group). Once both are
    done, evaluation and risk scoring run one after the other.
    """
    worker_hostname = socket.gethostname()

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

        # Kick off video and audio together instead of one after the other
        session_manager.update_session_status(
            session_id, session_manager.VIDEO_PROCESSING, {"stage": "parallel_video_audio"}
        )

        parallel_group = group(
            _run_video.s(session_id),
            _run_audio.s(session_id),
        )
        result = parallel_group.apply_async()

        # Block here until both finish
        video_result, audio_result = result.get(timeout=600)
        logger.info("Parallel video+audio completed for session %s", session_id)

        # Now hand off to evaluation + risk scoring
        _after_parallel.delay(session_id, video_result, audio_result)

        return {
            "session_id": session_id,
            "status": "processing_parallel",
            "video_result": video_result,
            "audio_result": audio_result,
            "processed_by": worker_hostname,
        }

    except Exception as exc:
        # We used to calculate the wait time ourselves here. Not anymore -
        # retry_backoff=True on the decorator already handles that for us,
        # so this just needs to trigger the retry.
        logger.warning(
            "Task for session %s failed (attempt %d/3), Celery will retry with backoff: %s",
            session_id,
            self.request.retries + 1,
            exc,
            exc_info=True,
        )
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Runs on a schedule (Celery Beat) to sweep up anything due for a retry
# ---------------------------------------------------------------------------


@celery_app.task(name="workers.tasks.scan_and_dispatch_retries")
def scan_and_dispatch_retries():
    """Checks Redis for sessions that are due to be retried and sends them
    back through the normal scheduling path. Celery Beat runs this every
    60 seconds.
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
                        continue  # too early, skip it for now

                    session_id = data.get("session_id")
                    if not session_id:
                        continue

                    # Send it back through the scheduler like any other job
                    from orchestrator.scheduler import Scheduler, TaskPriority

                    scheduler = Scheduler()
                    scheduler.schedule_task(session_id, priority=TaskPriority.MEDIUM)
                    dispatched += 1

                    # Done with this key, remove it
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
