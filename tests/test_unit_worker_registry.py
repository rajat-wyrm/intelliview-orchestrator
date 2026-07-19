"""Unit tests for WorkerRegistry — register, heartbeat, capacity, deregister."""

from unittest.mock import MagicMock, patch

from orchestrator.worker_registry import WorkerRegistry


def _new_registry():
    client = MagicMock()

    client.ping.return_value = True
    client.hset.return_value = True
    client.sadd.return_value = True
    client.expire.return_value = True
    client.set.return_value = True
    client.delete.return_value = 1
    client.srem.return_value = 1
    client.hincrby.return_value = 1
    client.smembers.return_value = set()
    client.hgetall.return_value = {}
    client.scan_iter.return_value = iter([])

    with patch("orchestrator.worker_registry.CacheManager", return_value=client):
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
