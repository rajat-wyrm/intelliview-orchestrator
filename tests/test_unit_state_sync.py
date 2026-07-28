"""Unit tests for Redis session state serialization."""

import base64
import binascii
import json
from unittest.mock import MagicMock, patch

import pytest

from monitoring.metrics_collector import MetricsCollector
from orchestrator import session_payload
from orchestrator.fault_manager import FaultManager
from orchestrator.session_payload import (
    SESSION_COMPRESSED_PREFIX,
    SESSION_COMPRESSION_THRESHOLD_BYTES,
    deserialize_session_payload,
    serialize_session_payload,
)
from orchestrator.state_sync import StateSynchronizer


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.sets = {}

    def set(self, key, value, ex=None):
        self.values[key] = (value, ex)
        return True

    def get(self, key):
        stored = self.values.get(key)
        return stored[0] if stored else None

    def scan(self, cursor, match=None, count=100):
        del count
        if cursor != 0:
            return 0, []

        keys = list(self.values)
        if match and match.endswith("*"):
            keys = [key for key in keys if key.startswith(match[:-1])]
        elif match:
            keys = [key for key in keys if key == match]
        return 0, keys

    def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(value)
        return 1

    def delete(self, key):
        self.values.pop(key, None)
        return 1

    def srem(self, key, value):
        if key in self.sets:
            self.sets[key].discard(value)
        return 1

    def smembers(self, key):
        return self.sets.get(key, set())

    def info(self):
        return {
            "used_memory_human": "1MB",
            "connected_clients": 1,
        }


def test_small_session_payload_stays_plain_json():
    session_data = {"session_id": "s1", "status": "QUEUED"}

    payload = serialize_session_payload(session_data)

    assert payload == json.dumps(session_data)
    assert not payload.startswith(SESSION_COMPRESSED_PREFIX)
    assert deserialize_session_payload(payload) == session_data


def test_payload_at_compression_threshold_stays_plain_json(monkeypatch):
    session_data = {"session_id": "s1", "metadata": "x" * 128}
    serialized_size = len(json.dumps(session_data).encode("utf-8"))
    monkeypatch.setattr(session_payload, "SESSION_COMPRESSION_THRESHOLD_BYTES", serialized_size)

    payload = serialize_session_payload(session_data)

    assert payload == json.dumps(session_data)
    assert not payload.startswith(SESSION_COMPRESSED_PREFIX)


def test_large_session_payload_is_compressed_and_round_trips():
    session_data = {
        "session_id": "s1",
        "status": "PROCESSING",
        "answers_provided": [{"answer_text": "x" * SESSION_COMPRESSION_THRESHOLD_BYTES}],
    }

    payload = serialize_session_payload(session_data)

    assert payload.startswith(SESSION_COMPRESSED_PREFIX)
    assert deserialize_session_payload(payload) == session_data


def test_legacy_plain_json_bytes_still_deserialize():
    session_data = {"session_id": "legacy", "status": "CREATED"}
    payload = json.dumps(session_data).encode("utf-8")

    assert deserialize_session_payload(payload) == session_data


def test_state_synchronizer_reads_legacy_plain_json_cache_entries():
    redis = FakeRedis()
    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis
    session_data = {"session_id": "legacy", "status": "QUEUED"}

    redis.set("session:legacy", json.dumps(session_data), ex=sync.SESSION_TTL)

    assert sync.get_session_state("legacy") == session_data


def test_state_synchronizer_uses_compressed_payloads_for_large_sessions():
    redis = FakeRedis()
    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis

    session_data = {
        "session_id": "s2",
        "status": "PROCESSING",
        "metadata": {"blob": "x" * SESSION_COMPRESSION_THRESHOLD_BYTES},
    }

    assert sync.set_session_state("s2", session_data) is True

    stored, ttl = redis.values["session:s2"]
    assert ttl == sync.SESSION_TTL
    assert stored.startswith(SESSION_COMPRESSED_PREFIX)
    assert sync.get_session_state("s2") == session_data
    assert "s2" in redis.sets["active_sessions"]


@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        (f"{SESSION_COMPRESSED_PREFIX}not-valid-base64", binascii.Error),
        (f"{SESSION_COMPRESSED_PREFIX}{base64.b64encode(b'not gzip data').decode('ascii')}", OSError),
    ],
)
def test_corrupted_compressed_payload_raises_from_deserializer(payload, expected_error):
    with pytest.raises(expected_error):
        deserialize_session_payload(payload)


@pytest.mark.parametrize(
    "payload",
    [
        f"{SESSION_COMPRESSED_PREFIX}not-valid-base64",
        f"{SESSION_COMPRESSED_PREFIX}{base64.b64encode(b'not gzip data').decode('ascii')}",
    ],
)
def test_state_synchronizer_returns_none_for_corrupted_compressed_cache_entry(payload):
    redis = FakeRedis()
    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis
    redis.set("session:bad", payload, ex=sync.SESSION_TTL)

    assert sync.get_session_state("bad") is None


def test_metrics_collector_reads_compressed_session_scans():
    redis = FakeRedis()
    redis.set(
        "session:s3",
        serialize_session_payload(
            {
                "session_id": "s3",
                "status": "PROCESSING",
                "metadata": {"blob": "x" * SESSION_COMPRESSION_THRESHOLD_BYTES},
            }
        ),
    )
    collector = MetricsCollector.__new__(MetricsCollector)
    collector.redis_client = redis

    metrics = collector._get_session_metrics()

    assert metrics["active"] == 1
    assert metrics["total"] == 1


def test_metrics_collector_skips_corrupted_compressed_session_scans():
    redis = FakeRedis()
    redis.set("session:bad", f"{SESSION_COMPRESSED_PREFIX}not-valid-base64")
    redis.set(
        "session:good",
        serialize_session_payload(
            {
                "session_id": "good",
                "status": "FAILED",
                "metadata": {"blob": "x" * SESSION_COMPRESSION_THRESHOLD_BYTES},
            }
        ),
    )
    collector = MetricsCollector.__new__(MetricsCollector)
    collector.redis_client = redis

    metrics = collector._get_session_metrics()

    assert metrics["failed"] == 1
    assert metrics["total"] == 1


def test_fault_manager_reads_compressed_session_scans():
    redis = FakeRedis()
    redis.set(
        "session:s4",
        serialize_session_payload(
            {
                "session_id": "s4",
                "status": "PROCESSING",
                "assigned_worker": "worker-1",
                "metadata": {"blob": "x" * SESSION_COMPRESSION_THRESHOLD_BYTES},
            }
        ),
    )
    fault_manager = FaultManager.__new__(FaultManager)
    fault_manager.redis_client = redis

    assert fault_manager._get_worker_tasks("worker-1") == ["s4"]


def test_fault_manager_skips_corrupted_compressed_session_scans():
    redis = FakeRedis()
    redis.set("session:bad", f"{SESSION_COMPRESSED_PREFIX}not-valid-base64")
    redis.set(
        "session:good",
        serialize_session_payload(
            {
                "session_id": "good",
                "status": "PROCESSING",
                "assigned_worker": "worker-1",
                "metadata": {"blob": "x" * SESSION_COMPRESSION_THRESHOLD_BYTES},
            }
        ),
    )
    fault_manager = FaultManager.__new__(FaultManager)
    fault_manager.redis_client = redis

    assert fault_manager._get_worker_tasks("worker-1") == ["good"]


def test_delete_session_state_removes_cached_session():
    redis = FakeRedis()
    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis

    session_data = {"session_id": "s1", "status": "QUEUED"}

    sync.set_session_state("s1", session_data)

    assert "session:s1" in redis.values
    assert "s1" in redis.sets["active_sessions"]

    assert sync.delete_session_state("s1") is True

    assert "session:s1" not in redis.values
    assert "s1" not in redis.sets["active_sessions"]


def test_get_active_sessions_returns_all_active_session_ids():
    redis = FakeRedis()
    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis

    sync.set_session_state("s1", {"session_id": "s1"})
    sync.set_session_state("s2", {"session_id": "s2"})

    active_sessions = sync.get_active_sessions()

    assert set(active_sessions) == {"s1", "s2"}


def test_clear_cache_removes_all_cached_sessions():
    redis = FakeRedis()
    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis

    sync.set_session_state("s1", {"session_id": "s1"})
    sync.set_session_state("s2", {"session_id": "s2"})

    assert "session:s1" in redis.values
    assert "session:s2" in redis.values

    assert sync.clear_cache() is True

    assert "session:s1" not in redis.values
    assert "session:s2" not in redis.values
    assert "active_sessions" not in redis.values


def test_get_cache_stats_returns_expected_information():
    redis = FakeRedis()
    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis

    sync.set_session_state("s1", {"session_id": "s1"})
    sync.set_session_state("s2", {"session_id": "s2"})

    stats = sync.get_cache_stats()

    assert stats["status"] == "connected"
    assert stats["active_sessions_count"] == 2
    assert stats["redis_memory_used"] == "1MB"
    assert stats["redis_connected_clients"] == 1


def test_sync_state_to_db_updates_database():
    interview = MagicMock()

    db_session = MagicMock()
    db_session.execute.return_value.scalar_one_or_none.return_value = interview

    sync = StateSynchronizer.__new__(StateSynchronizer)

    session_data = {
        "status": "COMPLETED",
        "risk_score": 7.5,
        "video_analysis": {"score": 90},
        "audio_analysis": {"score": 85},
        "evaluation_analysis": {"overall": 88},
    }

    with patch("database.db.SessionLocal", return_value=db_session):
        assert sync.sync_state_to_db("session-1", session_data) is True

    assert interview.status == "COMPLETED"
    assert interview.risk_score == 7.5
    assert interview.video_analysis == {"score": 90}

    assert interview.audio_analysis == {"score": 85}
    assert interview.evaluation_analysis == {"overall": 88}

    db_session.commit.assert_called_once()
    db_session.close.assert_called_once()


def test_delete_session_state_handles_redis_exception():
    redis = MagicMock()
    redis.delete.side_effect = Exception("Redis error")

    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis

    assert sync.delete_session_state("s1") is False


def test_get_active_sessions_handles_redis_exception():
    redis = MagicMock()
    redis.smembers.side_effect = Exception("Redis error")

    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis

    assert sync.get_active_sessions() == []


def test_get_cache_stats_handles_redis_exception():
    redis = MagicMock()
    redis.smembers.side_effect = Exception("Redis error")

    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis

    stats = sync.get_cache_stats()

    assert stats["status"] == "error"


def test_get_session_state_returns_none_when_redis_fails():
    sync = StateSynchronizer.__new__(StateSynchronizer)

    redis = MagicMock()
    redis.get.side_effect = Exception("Redis error")

    sync.redis_client = redis

    assert sync.get_session_state("s1") is None


def test_set_session_state_returns_false_when_redis_unavailable():
    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = None

    assert sync.set_session_state("s1", {"status": "QUEUED"}) is False


def test_set_session_state_handles_redis_exception():
    redis = MagicMock()
    redis.set.side_effect = Exception("Redis error")

    sync = StateSynchronizer.__new__(StateSynchronizer)
    sync.redis_client = redis

    assert sync.set_session_state("s1", {"status": "QUEUED"}) is False


def test_sync_state_to_db_handles_database_exception():
    db_session = MagicMock()
    db_session.execute.side_effect = Exception("DB error")

    sync = StateSynchronizer.__new__(StateSynchronizer)

    with patch("database.db.SessionLocal", return_value=db_session):
        assert sync.sync_state_to_db("session-1", {"status": "COMPLETED"}) is False

    db_session.rollback.assert_called_once()
    db_session.close.assert_called_once()
