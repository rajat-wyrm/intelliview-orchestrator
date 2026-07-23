"""Celery Application Setup.

Initialises Celery with the Redis broker, sensible reliability defaults,
and a `session_failed` signal that lets us mark the DB session as
FAILED only after Celery has exhausted its retries (rather than on
every transient exception).
"""
"""
# TODO:
 Separate worker deployment is pending.
 These queues prepare task routing for future deployment where:
 - interview queue will be processed by workers with
   worker_prefetch_multiplier=1 for long-running tasks.
 - maintenance queue will be processed by dedicated workers with a
   higher worker_prefetch_multiplier for short-running tasks.

from celery import Celery, signals
from kombu import Queue

"""
from celery import Celery, signals
from kombu import Queue
from config import REDIS_URL
from workers.metrics_server import start_worker_metrics





celery_app = Celery("interview_tasks", broker=REDIS_URL, backend=REDIS_URL)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    task_acks_late=True,  # re-deliver if worker dies mid-task
    task_reject_on_worker_lost=True,

    # Long-running interview tasks should reserve only one task at a time
    worker_prefetch_multiplier=1,

    broker_connection_retry_on_startup=True,
   
    # Periodic beat schedule — scan for due retries every 60 seconds
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
        from workers.tasks import send_mock_email_alert 
        session_id = args[0] if args else None
        if not session_id:
            return
        SessionManager().mark_session_failed(session_id, f"Celery task exhausted retries: {exception!s}")
        send_mock_email_alert.delay(session_id)
    except Exception as exc:
        # Don't let a signal handler crash the worker.
        import logging

        logging.getLogger(__name__).warning("task_failure handler failed: %s", exc)


if __name__ == "__main__":
    celery_app.start()