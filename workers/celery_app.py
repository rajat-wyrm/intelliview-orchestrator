"""Celery Application Setup.

Initialises Celery with the Redis broker, sensible reliability defaults,
and a `session_failed` signal that lets us mark the DB session as
FAILED only after Celery has exhausted its retries.
"""

from celery import Celery, signals
from kombu import Queue
from opentelemetry.instrumentation.celery import CeleryInstrumentor

from config import REDIS_URL

celery_app = Celery("interview_tasks", broker=REDIS_URL, backend=REDIS_URL)
CeleryInstrumentor().instrument()

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
    # Long-running interview tasks should reserve only one task at a time
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # Priority queues setup for Issue 4
    task_default_queue="medium_priority",
    task_queues=(
        Queue("high_priority"),
        Queue("medium_priority"),
        Queue("low_priority"),
    ),
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


_SESSION_TASK_NAMES: frozenset[str] = frozenset(
    {
        "workers.tasks.process_interview_session",
        "workers.tasks._run_video",
        "workers.tasks._run_audio",
        "workers.tasks._after_parallel",
    }
)
"""Tasks that carry a ``session_id`` and whose permanent failure should be
propagated to the session record.  Tasks outside this set (e.g.
``scan_and_dispatch_retries``) do not own a session and are skipped."""


def _extract_session_id(args: tuple, kwargs: dict) -> str | None:
    """Return ``session_id`` from either positional or keyword arguments.

    Callers may invoke a task in any of the following equivalent ways::

        task.delay("abc-123")                # positional  → args[0]
        task.delay(session_id="abc-123")    # keyword      → kwargs["session_id"]
        task.apply_async(args=["abc-123"])  # positional  → args[0]
        task.apply_async(kwargs={"session_id": "abc-123"})  # keyword

    Checking only ``args[0]`` silently misses the keyword form and returns
    ``None``, causing the failure handler to skip updating the session status.
    """
    if args:
        return args[0]
    return kwargs.get("session_id")


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
        SessionManager().mark_session_failed(
            session_id,
            f"Celery task exhausted retries: {exception!s}",
        )

        # TODO: enable notification task when implemented
        # send_mock_email_alert.delay(session_id)
    except Exception as exc:
        # Don't let a signal handler crash the worker.
        import logging

        logging.getLogger(__name__).warning("task_failure handler failed: %s", exc)


@celery_app.task(name="workers.tasks.send_mock_email_alert")
def send_mock_email_alert(session_id: str) -> None:
    """Mock email alert task — logs the notification.

    In production this would call SendGrid / SES / etc.
    """
    import logging

    logging.getLogger(__name__).info("Mock email alert sent for session %s", session_id)


if __name__ == "__main__":
    celery_app.start()