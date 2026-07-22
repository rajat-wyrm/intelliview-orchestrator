"""Unit tests for WorkerRegistry — register, heartbeat, capacity, deregister."""

from unittest.mock import patch

from orchestrator.worker_registry import WorkerRegistry


def _new_registry():
    with patch("orchestrator.worker_registry.get_redis_client") as mock_redis:
        mock_redis.return_value.ping.return_value = True
        mock_redis.return_value.hset.return_value = True
        mock_redis.return_value.sadd.return_value = True
        mock_redis.return_value.expire.return_value = True
        mock_redis.return_value.setex.return_value = True
        mock_redis.return_value.delete.return_value = 1
        mock_redis.return_value.srem.return_value = 1
        mock_redis.return_value.hincrby.return_value = 1
        mock_redis.return_value.smembers.return_value = set()
        mock_redis.return_value.hgetall.return_value = {}
        mock_redis.return_value.scan_iter.return_value = iter([])

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


def test_deregister_worker_removes_entry():
    reg = _new_registry()
    reg.register_worker("w4", capacity=2)
    assert reg.deregister_worker("w4") is True
    assert reg.get_worker("w4") is None
