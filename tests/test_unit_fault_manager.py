"""Unit tests for FaultManager — failure logging, DLQ, recovery queue."""

from datetime import datetime, timezone


from orchestrator.fault_manager import FailureType, FaultManager


from unittest.mock import MagicMock, patch


def _manager():
    with patch("orchestrator.fault_manager.get_redis_client") as mock_get_redis:
        client = MagicMock()

        client.lpush.return_value = 1
        client.ltrim.return_value = True
        client.expire.return_value = True
        client.scan.return_value = (0, [])
        client.lrange.return_value = []
        client.get.return_value = None
        client.set.return_value = True
        client.incr.return_value = 1

        mock_get_redis.return_value = client

        return FaultManager()

def test_log_failure_appends_to_log_key():
    fm = _manager()
    assert fm.log_failure("s1", FailureType.TASK_EXCEPTION, "boom", "w1") is True
    call = fm.redis_client.lpush.call_args
    assert call.args[0].startswith("failure_log:")
    payload = call.args[1]
    assert "boom" in payload
    assert "w1" in payload


def test_move_to_dlq_uses_dead_letter_queue_key():
    fm = _manager()
    assert fm.move_to_dead_letter_queue("s9", "max retries") is True
    fm.redis_client.lpush.assert_called_once()
    assert fm.redis_client.lpush.call_args.args[0] == "dead_letter_queue"
    fm.redis_client.expire.assert_called_once_with(
        "dead_letter_queue",
        604800,
    )


def test_get_failure_log_decodes_json_entries():
    fm = _manager()
    fm.redis_client.lrange.return_value = [
        '{"session_id": "s1", "failure_type": "task_exception", "worker_id": "w1"}'
    ]
    log = fm.get_failure_log(limit=10)
    assert all(entry["session_id"] == "s1" for entry in log)
    assert all(entry["failure_type"] == "task_exception" for entry in log)
    assert log[0]["worker_id"] == "w1"  
    
def test_handle_worker_failure_reassigns_tasks_and_logs():
    fm = _manager()
    with (
        patch.object(fm, "_get_worker_tasks", return_value=["s1", "s2"]),
        patch.object(fm, "reassign_task", return_value=True) as reassign,
        patch.object(fm, "log_failure", return_value=True) as log,
    ):
        assert fm.handle_worker_failure("w_dead", "crash") is True
    assert reassign.call_count == 2
    log.assert_called_once()


def test_reassign_increments_counter_and_persists():
    fm = _manager()
    fm.redis_client.incr.return_value = 2
    assert fm.reassign_task("s3", original_worker="w_dead") is True
    # The modern redis-py uses `set(key, value, ex=ttl)` instead of the
    # deprecated `setex(key, ttl, value)`.
    fm.redis_client.set.assert_called()
    
import json


def test_get_worker_tasks_uses_assigned_node():
    fm = _manager()

    session = {
        "session_id": "session-123",
        "assigned_node": "worker-1",
    }

    fm.redis_client.scan.return_value = (0, ["session:123"])
    fm.redis_client.get.return_value = json.dumps(session)

    tasks = fm._get_worker_tasks("worker-1")

    assert tasks == ["session-123"]   
    
import json


def test_get_worker_tasks_uses_assigned_node():
    fm = _manager()

    session = {
        "session_id": "session-123",
        "assigned_node": "worker-1",
    }

    fm.redis_client.scan.return_value = (0, ["session:123"])
    fm.redis_client.get.return_value = json.dumps(session)

    tasks = fm._get_worker_tasks("worker-1")

    assert tasks == ["session-123"]     
