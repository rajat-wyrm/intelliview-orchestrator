"""Celery Application Setup.

Initialises Celery with the Redis broker, sensible reliability defaults,
and a `session_failed` signal that lets us mark the DB session as
FAILED only after Celery has exhausted its retries (rather than on
every transient exception).
"""

from celery import Celery, signals
from kombu import Queue

from config import REDIS_URL

celery_app = Celery("interview_tasks", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    task_acks_late=True,  # re-deliver if worker dies mid-task
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # fair distribution across workers
    broker_connection_retry_on_startup=True,
    # Periodic beat schedule — scan for due retries every 60 seconds
    task_queues=(
    Queue("fast"),
    Queue("slow"),
    ),

    task_routes={
    "workers.tasks.scan_and_dispatch_retries": {"queue": "fast"},
    },
    beat_schedule={
        "scan-due-retries": {
            "task": "workers.tasks.scan_and_dispatch_retries",
            "schedule": 60.0,
        },
    },
)

# Auto-discover tasks from workers module
celery_app.autodiscover_tasks(["workers"])


@signals.task_failure.connect
def _on_task_failure(task_id, exception, args, kwargs, traceback, einfo, **_extra):
    """When a task fails permanently (retries exhausted), mark the
    session as FAILED so the dashboard reflects reality.

    `args[0]` is the session_id passed to `process_interview_session`.
    Imported lazily so importing this module doesn't pull in the DB stack
    before the worker process is ready.
    """
    try:
        from orchestrator.session_manager import SessionManager

        session_id = args[0] if args else None
        if not session_id:
            return
        SessionManager().mark_session_failed(session_id, f"Celery task exhausted retries: {exception!s}")
    except Exception as exc:
        # Don't let a signal handler crash the worker.
        import logging

        logging.getLogger(__name__).warning("task_failure handler failed: %s", exc)


if __name__ == "__main__":
    celery_app.start()
