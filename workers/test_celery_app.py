"""Unit tests for the ``_on_task_failure`` signal handler in celery_app.

Focus areas
-----------
* ``session_id`` passed as a *positional* argument (original behaviour).
* ``session_id`` passed as a *keyword* argument (the bug this PR fixes).
* Tasks that are **not** session-aware (e.g. ``scan_and_dispatch_retries``)
  must be ignored — no DB write should occur.
* Tasks with neither positional nor keyword ``session_id`` are skipped
  gracefully without raising.

These tests never touch Redis, Postgres, or a real Celery broker.  Every
external dependency is stubbed at the ``sys.modules`` level so the test
suite runs completely offline.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out the heavy dependencies that celery_app.py drags in at import time.
# These must be in sys.modules BEFORE we import anything from this project.
# ---------------------------------------------------------------------------

def _install_stubs():
    """Insert lightweight fakes so `from config import REDIS_URL` etc. work."""
    # config stub
    config_mod = types.ModuleType("config")
    config_mod.REDIS_URL = "redis://localhost:6379/0"
    sys.modules.setdefault("config", config_mod)

    # orchestrator package + session_manager stub (real import happens lazily
    # inside _on_task_failure — we patch it per-test, but the package must
    # exist in sys.modules so the import machinery doesn't error at stub time)
    orch_pkg = types.ModuleType("orchestrator")
    sys.modules.setdefault("orchestrator", orch_pkg)

    sm_mod = types.ModuleType("orchestrator.session_manager")
    sm_mod.SessionManager = MagicMock()
    sys.modules.setdefault("orchestrator.session_manager", sm_mod)


_install_stubs()

# Now we can safely import the module under test.
from workers.celery_app import _SESSION_TASK_NAMES, _extract_session_id, _on_task_failure  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAIN_TASK = "workers.tasks.process_interview_session"
_VIDEO_TASK = "workers.tasks._run_video"
_AUDIO_TASK = "workers.tasks._run_audio"
_AFTER_TASK = "workers.tasks._after_parallel"
_BEAT_TASK = "workers.tasks.scan_and_dispatch_retries"

SESSION_ID = "test-session-abc-123"


def _make_sender(task_name: str) -> SimpleNamespace:
    """Return a minimal Celery task-sender stub."""
    return SimpleNamespace(name=task_name)


def _invoke_handler(sender, args: tuple = (), kwargs: dict | None = None):
    """Call the real signal handler with controlled arguments."""
    _on_task_failure(
        sender=sender,
        task_id="fake-task-id",
        exception=RuntimeError("something broke"),
        args=args,
        kwargs=kwargs or {},
        traceback=None,
        einfo=None,
    )


# ---------------------------------------------------------------------------
# _extract_session_id — pure unit tests, no mocking needed
# ---------------------------------------------------------------------------


class TestExtractSessionId:
    def test_positional_arg_returned(self):
        assert _extract_session_id((SESSION_ID,), {}) == SESSION_ID

    def test_keyword_arg_returned_when_no_positional(self):
        assert _extract_session_id((), {"session_id": SESSION_ID}) == SESSION_ID

    def test_positional_takes_precedence_over_keyword(self):
        # Both provided — positional wins (mirrors Python calling convention).
        assert _extract_session_id((SESSION_ID,), {"session_id": "other"}) == SESSION_ID

    def test_returns_none_when_both_absent(self):
        assert _extract_session_id((), {}) is None

    def test_returns_none_when_only_unrelated_kwargs(self):
        assert _extract_session_id((), {"other_param": "val"}) is None


# ---------------------------------------------------------------------------
# _SESSION_TASK_NAMES — contents check
# ---------------------------------------------------------------------------


class TestSessionTaskNames:
    def test_main_task_in_set(self):
        assert _MAIN_TASK in _SESSION_TASK_NAMES

    def test_video_task_in_set(self):
        assert _VIDEO_TASK in _SESSION_TASK_NAMES

    def test_audio_task_in_set(self):
        assert _AUDIO_TASK in _SESSION_TASK_NAMES

    def test_after_parallel_in_set(self):
        assert _AFTER_TASK in _SESSION_TASK_NAMES

    def test_beat_task_not_in_set(self):
        assert _BEAT_TASK not in _SESSION_TASK_NAMES


# ---------------------------------------------------------------------------
# _on_task_failure — task scoping
# ---------------------------------------------------------------------------


class TestOnTaskFailureScoping:
    """Handler should only act on tasks listed in _SESSION_TASK_NAMES."""

    def _fresh_sm(self):
        mock_instance = MagicMock()
        mock_class = MagicMock(return_value=mock_instance)
        return mock_class, mock_instance

    def test_beat_task_is_ignored(self):
        mock_class, mock_instance = self._fresh_sm()
        with patch.dict(sys.modules, {"orchestrator.session_manager": types.SimpleNamespace(SessionManager=mock_class)}):
            sender = _make_sender(_BEAT_TASK)
            _invoke_handler(sender, args=(), kwargs={})
        mock_instance.mark_session_failed.assert_not_called()

    def test_unknown_task_is_ignored(self):
        mock_class, mock_instance = self._fresh_sm()
        with patch.dict(sys.modules, {"orchestrator.session_manager": types.SimpleNamespace(SessionManager=mock_class)}):
            sender = _make_sender("workers.tasks.some_future_task")
            _invoke_handler(sender, args=(), kwargs={})
        mock_instance.mark_session_failed.assert_not_called()

    def test_main_task_is_handled(self):
        mock_class, mock_instance = self._fresh_sm()
        with patch.dict(sys.modules, {"orchestrator.session_manager": types.SimpleNamespace(SessionManager=mock_class)}):
            _invoke_handler(_make_sender(_MAIN_TASK), args=(SESSION_ID,))
        mock_instance.mark_session_failed.assert_called_once()

    def test_video_task_is_handled(self):
        mock_class, mock_instance = self._fresh_sm()
        with patch.dict(sys.modules, {"orchestrator.session_manager": types.SimpleNamespace(SessionManager=mock_class)}):
            _invoke_handler(_make_sender(_VIDEO_TASK), args=(SESSION_ID,))
        mock_instance.mark_session_failed.assert_called_once()

    def test_audio_task_is_handled(self):
        mock_class, mock_instance = self._fresh_sm()
        with patch.dict(sys.modules, {"orchestrator.session_manager": types.SimpleNamespace(SessionManager=mock_class)}):
            _invoke_handler(_make_sender(_AUDIO_TASK), args=(SESSION_ID,))
        mock_instance.mark_session_failed.assert_called_once()

    def test_after_parallel_task_is_handled(self):
        mock_class, mock_instance = self._fresh_sm()
        with patch.dict(sys.modules, {"orchestrator.session_manager": types.SimpleNamespace(SessionManager=mock_class)}):
            # _after_parallel(session_id, video_result, audio_result)
            _invoke_handler(_make_sender(_AFTER_TASK), args=(SESSION_ID, {}, {}))
        mock_instance.mark_session_failed.assert_called_once()


# ---------------------------------------------------------------------------
# _on_task_failure — session_id resolution (the core bug fix)
# ---------------------------------------------------------------------------


class TestOnTaskFailureSessionIdResolution:
    """Handler must find session_id whether it arrives positionally or as a kwarg."""

    def _sm_patch(self):
        mock_instance = MagicMock()
        mock_class = MagicMock(return_value=mock_instance)
        stub = types.SimpleNamespace(SessionManager=mock_class)
        return stub, mock_instance

    def test_session_id_via_positional_arg(self):
        """Original call pattern: task.delay('abc-123') — args[0] is session_id."""
        stub, mock_instance = self._sm_patch()
        with patch.dict(sys.modules, {"orchestrator.session_manager": stub}):
            _invoke_handler(_make_sender(_MAIN_TASK), args=(SESSION_ID,), kwargs={})

        mock_instance.mark_session_failed.assert_called_once()
        actual_sid, actual_msg = mock_instance.mark_session_failed.call_args[0]
        assert actual_sid == SESSION_ID
        assert "exhausted retries" in actual_msg

    def test_session_id_via_keyword_arg(self):
        """Keyword call: task.delay(session_id='abc-123') — was silently lost before this fix."""
        stub, mock_instance = self._sm_patch()
        with patch.dict(sys.modules, {"orchestrator.session_manager": stub}):
            # Crucially: args is EMPTY, session_id lives in kwargs only.
            _invoke_handler(_make_sender(_MAIN_TASK), args=(), kwargs={"session_id": SESSION_ID})

        mock_instance.mark_session_failed.assert_called_once()
        actual_sid, actual_msg = mock_instance.mark_session_failed.call_args[0]
        assert actual_sid == SESSION_ID, (
            "session_id passed as a keyword argument was not picked up — "
            "the args[0] bug is still present"
        )
        assert "exhausted retries" in actual_msg

    def test_apply_async_with_kwargs_dict(self):
        """task.apply_async(kwargs={'session_id': ...}) — equivalent to keyword call."""
        stub, mock_instance = self._sm_patch()
        with patch.dict(sys.modules, {"orchestrator.session_manager": stub}):
            _invoke_handler(_make_sender(_VIDEO_TASK), args=(), kwargs={"session_id": SESSION_ID})

        mock_instance.mark_session_failed.assert_called_once()
        actual_sid = mock_instance.mark_session_failed.call_args[0][0]
        assert actual_sid == SESSION_ID

    def test_no_session_id_skips_db_call(self):
        """If session_id cannot be found in args or kwargs, skip silently."""
        stub, mock_instance = self._sm_patch()
        with patch.dict(sys.modules, {"orchestrator.session_manager": stub}):
            _invoke_handler(_make_sender(_MAIN_TASK), args=(), kwargs={"other_param": "value"})

        mock_instance.mark_session_failed.assert_not_called()

    def test_error_message_contains_exception_text(self):
        """The reason string forwarded to the DB should quote the exception."""
        stub, mock_instance = self._sm_patch()
        with patch.dict(sys.modules, {"orchestrator.session_manager": stub}):
            _on_task_failure(
                sender=_make_sender(_MAIN_TASK),
                task_id="tid",
                exception=RuntimeError("disk full"),
                args=(),
                kwargs={"session_id": SESSION_ID},
                traceback=None,
                einfo=None,
            )

        _, reason = mock_instance.mark_session_failed.call_args[0]
        assert "disk full" in reason

    def test_handler_survives_session_manager_exception(self):
        """A crash inside SessionManager must not propagate out of the handler."""
        mock_instance = MagicMock()
        mock_instance.mark_session_failed.side_effect = Exception("DB unavailable")
        mock_class = MagicMock(return_value=mock_instance)
        stub = types.SimpleNamespace(SessionManager=mock_class)

        with patch.dict(sys.modules, {"orchestrator.session_manager": stub}):
            # Should not raise — handler logs and swallows internal errors.
            _invoke_handler(_make_sender(_MAIN_TASK), args=(SESSION_ID,))
