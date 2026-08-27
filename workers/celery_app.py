"""Celery Application Setup.
Initialises Celery with the Redis broker, sensible reliability defaults,
and a `session_failed` signal that lets us mark the DB session as
FAILED only after Celery has exhausted its retries.
"""

from celery import Celery, shared_task, signals
from kombu import Queue
from opentelemetry.instrumentation.celery import CeleryInstrumentor

from config import REDIS_URL
from metrics.prometheus_metrics import TASKS_PERMANENTLY_FAILED


@shared_task
def reevaluate_stuck_sessions(threshold_hours=24):
    print("Running re-evaluation task...")
    return "Processed stuck sessions successfully."


# 1. Initialize celery_app with task inclusion
celery_app = Celery(
    "interview_tasks", broker=REDIS_URL, backend=REDIS_URL, include=["workers.tasks"]
)
celery_app = Celery("interview_tasks", broker=REDIS_URL, backend=REDIS_URL)
EVALUATION_MAX_RETRIES = 3
EVALUATION_RETRY_BACKOFF_BASE = 2
EVALUATION_RETRY_BACKOFF_MAX = 60
CeleryInstrumentor().instrument()

# 2. Set beat schedule
celery_app.conf.beat_schedule = {
    **getattr(celery_app.conf, "beat_schedule", {}),
    "periodic-re-evaluate-stuck-sessions": {
        "task": "workers.tasks.re_evaluate_stuck_sessions",
        "schedule": 1800.0,
        "kwargs": {"threshold_hours": 2},
    },
}
celery_app = Celery("interview_tasks", broker=REDIS_URL, backend=REDIS_URL)
CeleryInstrumentor().instrument()

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
    # All interview tasks dispatch to the "fast" queue by default (the worker
    # consumes only "fast"/"slow"); without this the tasks land on the default
    # "celery" queue, which no worker reads, and sessions stay QUEUED forever.
    task_default_queue="fast",
    task_queues=(
        Queue("fast"),
        Queue("slow"),
    ),
    # No periodic retry scanner is configured.
    # Interview tasks already use Celery's built-in retry/backoff mechanism
    # via self.retry(). The previous scan_and_dispatch_retries Beat entry
    # referenced an unregistered task and caused errors every 60 seconds.
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

        task.delay("abc-123")               # positional  → args[0]
        task.delay(session_id="abc-123")    # keyword     → kwargs["session_id"]
        task.apply_async(args=["abc-123"])  # positional  → args[0]
        task.apply_async(kwargs={"session_id": "abc-123"})  # keyword

    Checking only ``args[0]`` silently misses the keyword form and returns
    ``None``, causing the failure handler to skip updating the session status.
    """
    if args:
        return args[0]
    return kwargs.get("session_id")


@signals.task_failure.connect
def _on_task_failure(
    sender, task_id, exception, args, kwargs, traceback, einfo, **_extra
):
    print(f"HANDLER EXECUTED: {task_id}")
    """When a session-aware task fails permanently (retries exhausted), mark
    the session as FAILED so the dashboard reflects reality.

    The handler is scoped to :data:`_SESSION_TASK_NAMES` so that unrelated
    periodic tasks (e.g. ``scan_and_dispatch_retries``) do not trigger a
    spurious DB write.

    ``session_id`` is resolved from *either* positional or keyword arguments
    via :func:`_extract_session_id` so the handler is safe regardless of how
    the task was dispatched.

    Imported lazily so importing this module doesn't pull in the DB stack
    before the worker process is ready.
    """
    task_name: str = getattr(sender, "name", "") or ""
    if task_name not in _SESSION_TASK_NAMES:
        return

    try:
        from orchestrator.session_manager import SessionManager

        session_id = _extract_session_id(args, kwargs)
        if not session_id:
            return
        TASKS_PERMANENTLY_FAILED.inc()
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
