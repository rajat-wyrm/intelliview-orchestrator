"""Unit tests for WorkerRegistry - register, heartbeat, capacity, deregister."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from orchestrator.worker_registry import WorkerRegistry


# def _new_registry():
#     with patch("orchestrator.worker_registry.redis.from_url") as mock_redis:
#         mock_redis.return_value.ping.return_value = True
#         mock_redis.return_value.hset.return_value = True
#         mock_redis.return_value.sadd.return_value = True
#         mock_redis.return_value.expire.return_value = True
#         mock_redis.return_value.setex.return_value = True
#         mock_redis.return_value.delete.return_value = 1
#         mock_redis.return_value.srem.return_value = 1
#         mock_redis.return_value.hincrby.return_value = 1
#         return WorkerRegistry()
def _new_registry():
    with patch("orchestrator.worker_registry.get_redis_client") as mock_get_redis:
        mock_redis = MagicMock()

        mock_redis.ping.return_value = True
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

        reg = WorkerRegistry()

    # Assign mock directly so post-construction calls (register, heartbeat …)
    # also use the fake client, not a real Redis connection.
    reg.redis_client = mock_redis
    return reg


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


# ===========================================================================
# NEW: Weight field tests
# ===========================================================================


def test_register_worker_with_weight():
    """Explicit weight should be stored correctly, separate from capacity."""
    reg = _new_registry()
    assert reg.register_worker("heavy", capacity=4, weight=10) is True
    w = reg.get_worker("heavy")
    assert w is not None
    assert w["capacity"] == 4
    assert w["weight"] == 10


def test_register_worker_default_weight_equals_capacity():
    """When no weight is specified, it should default to the capacity value."""
    reg = _new_registry()
    assert reg.register_worker("default", capacity=8) is True
    w = reg.get_worker("default")
    assert w is not None
    assert w["weight"] == 8  # defaults to capacity
    assert w["capacity"] == 8

