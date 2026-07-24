"""Unit tests for WorkerRegistry — register, heartbeat, capacity, deregister."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from orchestrator.worker_registry import WorkerRegistry


def _new_registry():
    with patch("orchestrator.worker_registry.get_redis_client") as mock_get_redis:
        mock_redis = MagicMock()

        mock_redis.hset.return_value = True
        mock_redis.sadd.return_value = True
        mock_redis.expire.return_value = True
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.srem.return_value = 1
        mock_redis.hincrby.return_value = 1
        mock_redis.smembers.return_value = set()
        mock_redis.hgetall.return_value = {}

        mock_get_redis.return_value = mock_redis

        return WorkerRegistry()


def test_register_worker_records_capacity():
    reg = _new_registry()
    assert reg.register_worker("w1", capacity=4) is True
    w = reg.get_worker("w1")
    assert w is not None
    assert w["capacity"] == 4
    assert w["active_tasks"] == 0
    assert w["status"] == "healthy"


def test_heartbeat_updates_active_tasks_and_marks_healthy():
    reg = _new_registry()
    reg.register_worker("w2", capacity=8)
    assert reg.heartbeat("w2", active_tasks=3) is True
    assert reg.get_worker("w2")["active_tasks"] == 3


def test_heartbeat_unknown_worker_returns_false():
    reg = _new_registry()
    assert reg.heartbeat("ghost", active_tasks=1) is False


def test_increment_decrement_active_tasks_clamps_to_zero():
    reg = _new_registry()
    reg.register_worker("w3", capacity=2)
    reg.increment_active_tasks("w3")
    reg.increment_active_tasks("w3")
    assert reg.get_worker("w3")["active_tasks"] == 2
    reg.decrement_active_tasks("w3")
    reg.decrement_active_tasks("w3")
    reg.decrement_active_tasks("w3")  # clamp
    assert reg.get_worker("w3")["active_tasks"] == 0


def test_get_available_workers_excludes_full_and_unhealthy():
    reg = _new_registry()
    reg.register_worker("healthy_free", capacity=2)
    reg.register_worker("healthy_full", capacity=2)
    reg.increment_active_tasks("healthy_full")
    reg.increment_active_tasks("healthy_full")
    reg.register_worker("degraded", capacity=2)
    reg.update_worker_status("degraded", "degraded")

    available = reg.get_available_workers()
    ids = {w["worker_id"] for w in available}
    assert "healthy_free" in ids
    assert "healthy_full" not in ids
    assert "degraded" not in ids


def test_worker_statistics_computes_utilization():
    reg = _new_registry()
    reg.register_worker("a", capacity=4)
    reg.register_worker("b", capacity=4)
    reg.increment_active_tasks("a")
    reg.increment_active_tasks("b")
    stats = reg.get_worker_statistics()
    assert stats["total_workers"] == 2
    assert stats["total_capacity"] == 8
    assert stats["total_active_tasks"] == 2
    assert stats["capacity_utilization"] == 25.0

def test_detect_unhealthy_worker_marks_status():
    reg = _new_registry()

    reg.register_worker("worker1", capacity=2)

    # Simulate worker stopping by making heartbeat older than timeout
    reg.get_worker("worker1")["last_heartbeat"] = (
        datetime.now(timezone.utc) - timedelta(seconds=120)
    ).isoformat()

    unhealthy = reg.detect_unhealthy_workers()

    assert "worker1" in unhealthy
    assert reg.get_worker("worker1")["status"] == "unhealthy"

def test_detect_unhealthy_worker_keeps_recent_worker_healthy():
    reg = _new_registry()

    reg.register_worker("worker2", capacity=2)

    unhealthy = reg.detect_unhealthy_workers()

    assert unhealthy == []
    assert reg.get_worker("worker2")["status"] == "healthy"

def test_detect_unhealthy_workers_only_marks_expired_workers():
    reg = _new_registry()

    reg.register_worker("healthy_worker", capacity=2)
    reg.register_worker("stale_worker", capacity=2)

    reg.get_worker("stale_worker")["last_heartbeat"] = (
        datetime.now(timezone.utc) - timedelta(seconds=120)
    ).isoformat()

    unhealthy = reg.detect_unhealthy_workers()

    assert unhealthy == ["stale_worker"]
    assert reg.get_worker("healthy_worker")["status"] == "healthy"
    assert reg.get_worker("stale_worker")["status"] == "unhealthy"

def test_deregister_worker_removes_entry():
    reg = _new_registry()
    reg.register_worker("w4", capacity=2)
    assert reg.deregister_worker("w4") is True
    assert reg.get_worker("w4") is None


def test_pubsub_sync_message_updates_local_workers():
    reg = _new_registry()
    fake_message = {"type": "message", "data": '{"worker_id": "test_sync_worker", "action": "sync"}'}
    with patch.object(
        reg.redis_client, "hgetall", return_value={"status": "healthy", "active_tasks": "2", "capacity": "4"}
    ):
        reg._handle_pubsub_message(fake_message)
    assert "test_sync_worker" in reg.local_workers
    assert reg.local_workers["test_sync_worker"]["active_tasks"] == 2


def test_pubsub_deregister_message_removes_worker():
    reg = _new_registry()
    reg.local_workers["dead_worker"] = {"worker_id": "dead_worker", "status": "healthy"}
    fake_message = {"type": "message", "data": '{"worker_id": "dead_worker", "action": "deregister"}'}
    reg._handle_pubsub_message(fake_message)
    assert "dead_worker" not in reg.local_workers


def test_pubsub_malformed_message_handled_safely():
    reg = _new_registry()
    fake_message = {
        "type": "message",
        "data": "invalid-json-payload-string",
    }
    reg._handle_pubsub_message(fake_message)
    assert reg.local_workers == {}
