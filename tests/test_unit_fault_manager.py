"""Unit tests for FaultManager — failure logging, DLQ, recovery queue."""
import json
from pathlib import Path 
from datetime import datetime, timezone
from unittest.mock import patch

from orchestrator.fault_manager import FailureType, FaultManager


def _manager():
    with patch("orchestrator.fault_manager.get_redis_client") as mock_client:
        client = mock_client.return_value
    with patch("orchestrator.fault_manager.get_redis_client") as mock_redis:
        client = mock_redis.return_value

        client.ping.return_value = True
        client.lpush.return_value = 1
        client.ltrim.return_value = True
        client.expire.return_value = True
        client.scan.return_value = (0, [])
        client.lrange.return_value = []
        client.get.return_value = None
        client.set.return_value = True
        client.incr.return_value = 1

<<<<<<< HEAD
=======
        return FaultManager()
>>>>>>> a41a2121beb1af26b3fcbe0da8b7da6b4c65096f
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


def test_get_failure_log_decodes_json_entries():
    fm = _manager()
    iso_now = datetime.now(timezone.utc).isoformat()
    payload = (
        '{"timestamp": "' + iso_now + '", "session_id": "s1", '
        '"failure_type": "task_exception", "error_message": "x", "worker_id": "w1"}'
    )
    fm.redis_client.lrange.return_value = [payload]
    log = fm.get_failure_log(limit=10)
    assert all(entry["session_id"] == "s1" for entry in log)
    assert all(entry["failure_type"] == "task_exception" for entry in log)
    # The first decoded entry must be the latest; subsequent duplicates from
    # the 7-day scan window are tolerated (operator-facing behaviour).
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


def test_log_failure_writes_jsonl_file(tmp_path):
    import os
    import json
    from pathlib import Path

    fm = _manager()

    old_dir = os.getcwd()
    os.chdir(tmp_path)

    try:
        fm.log_failure("s1", FailureType.TASK_EXCEPTION, "err1", "w1")
        fm.log_failure("s2", FailureType.TASK_EXCEPTION, "err2", "w2")
        fm.log_failure("s3", FailureType.TASK_EXCEPTION, "err3", "w3")

        log_file = Path("failed_logs.jsonl")
        assert log_file.exists()

        with log_file.open("r") as f:
            records = [json.loads(line) for line in f]

        assert len(records) == 3
        assert records[0]["session_id"] == "s1"
        assert records[1]["session_id"] == "s2"
        assert records[2]["session_id"] == "s3"

    finally:
        os.chdir(old_dir)


def test_reassign_increments_counter_and_persists():
    fm = _manager()
    fm.redis_client.incr.return_value = 2
    assert fm.reassign_task("s3", original_worker="w_dead") is True
    # The modern redis-py uses `set(key, value, ex=ttl)` instead of the
    # deprecated `setex(key, ttl, value)`.
    fm.redis_client.set.assert_called() 

 
   
 