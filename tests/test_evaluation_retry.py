from unittest.mock import patch

from celery.exceptions import Retry

from workers.celery_app import (
    EVALUATION_MAX_RETRIES,
    EVALUATION_RETRY_BACKOFF_BASE,
    EVALUATION_RETRY_BACKOFF_MAX,
)
from workers.tasks import _after_parallel


def test_evaluation_retry_configuration():
    assert _after_parallel.max_retries == 3
    assert EVALUATION_MAX_RETRIES == 3
    assert EVALUATION_RETRY_BACKOFF_BASE == 2
    assert EVALUATION_RETRY_BACKOFF_MAX == 60


def _run_evaluation_failure(retries):
    evaluation_error = RuntimeError("temporary evaluation failure")

    with (
        patch(
            "workers.tasks.evaluate_answers",
            side_effect=evaluation_error,
        ),
        patch("workers.tasks.session_manager") as session_manager,
        patch.object(
            _after_parallel,
            "retry",
            side_effect=Retry("retry scheduled"),
        ) as retry_mock,
    ):

        _after_parallel.push_request(retries=retries)

        try:
            _after_parallel.run(
                [{"video": "ok"}, {"audio": "ok"}],
                "session-123",
            )
        except Retry:
            pass

    return retry_mock, session_manager, evaluation_error


def test_evaluation_failure_retries_with_exponential_backoff():
    retry_mock, session_manager, evaluation_error = _run_evaluation_failure(0)

    retry_mock.assert_called_once_with(
        exc=evaluation_error,
        countdown=2,
    )

    session_manager.mark_session_failed.assert_not_called()


def test_evaluation_retry_uses_next_backoff_delay():
    retry_mock, _, evaluation_error = _run_evaluation_failure(1)

    retry_mock.assert_called_once_with(
        exc=evaluation_error,
        countdown=4,
    )


def test_evaluation_backoff_is_capped():
    retry_mock, _, evaluation_error = _run_evaluation_failure(10)

    retry_mock.assert_called_once_with(
        exc=evaluation_error,
        countdown=EVALUATION_RETRY_BACKOFF_MAX,
    )
