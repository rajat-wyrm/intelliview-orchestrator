"""Unit tests for StateSynchronizer."""

import json
from unittest.mock import patch

from orchestrator.state_sync import StateSynchronizer


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.sets = {}

    def set(self, key, value, ex=None):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)
        self.sets.pop(key, None)

    def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(value)

    def srem(self, key, value):
        if key in self.sets:
            self.sets[key].discard(value)

    def smembers(self, key):
        return self.sets.get(key, set())

    def info(self):
        return {
            "used_memory_human": "1M",
            "connected_clients": 1,
        }


def test_set_session_state_success():
    fake = FakeRedis()

    with patch("orchestrator.state_sync.get_redis_client", return_value=fake):
        sync = StateSynchronizer()

        data = {
            "status": "running",
            "risk_score": 10,
        }

        result = sync.set_session_state("session1", data)

        assert result is True
        assert json.loads(fake.store["session:session1"]) == data
        assert "session1" in fake.sets["active_sessions"]
    
def test_get_session_state_success():
    fake = FakeRedis()

    with patch("orchestrator.state_sync.get_redis_client", return_value=fake):
        sync = StateSynchronizer()

        data = {
            "status": "running",
            "risk_score": 10,
        }

        sync.set_session_state("session1", data)

        result = sync.get_session_state("session1")

        assert result == data

def test_get_session_state_not_found():
    fake = FakeRedis()

    with patch("orchestrator.state_sync.get_redis_client", return_value=fake):
        sync = StateSynchronizer()

        result = sync.get_session_state("unknown_session")

        assert result is None

def test_delete_session_state():
    fake = FakeRedis()

    with patch("orchestrator.state_sync.get_redis_client", return_value=fake):
        sync = StateSynchronizer()

        data = {
            "status": "running",
        }

        sync.set_session_state("session1", data)

        assert "session:session1" in fake.store
        assert "session1" in fake.sets["active_sessions"]

        result = sync.delete_session_state("session1")

        assert result is True
        assert "session:session1" not in fake.store
        assert "session1" not in fake.sets["active_sessions"]

def test_get_active_sessions():
    fake = FakeRedis()

    with patch("orchestrator.state_sync.get_redis_client", return_value=fake):
        sync = StateSynchronizer()

        sync.set_session_state("session1", {"status": "running"})
        sync.set_session_state("session2", {"status": "completed"})

        sessions = sync.get_active_sessions()

        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions

def test_clear_cache():
    fake = FakeRedis()

    with patch("orchestrator.state_sync.get_redis_client", return_value=fake):
        sync = StateSynchronizer()

        sync.set_session_state("session1", {"status": "running"})
        sync.set_session_state("session2", {"status": "completed"})

        assert len(fake.store) == 2
        assert len(fake.sets["active_sessions"]) == 2

        result = sync.clear_cache()

        assert result is True
        assert fake.store == {}
        assert "active_sessions" not in fake.sets

def test_get_cache_stats():
    fake = FakeRedis()

    with patch("orchestrator.state_sync.get_redis_client", return_value=fake):
        sync = StateSynchronizer()

        sync.set_session_state("session1", {"status": "running"})
        sync.set_session_state("session2", {"status": "completed"})

        stats = sync.get_cache_stats()

        assert stats["status"] == "connected"
        assert stats["active_sessions_count"] == 2
        assert stats["redis_memory_used"] == "1M"
        assert stats["redis_connected_clients"] == 1

def test_sync_state_to_db_returns_false_when_session_not_found():
    fake = FakeRedis()

    class FakeDB:
        def execute(self, *args, **kwargs):
            class Result:
                def scalar_one_or_none(self):
                    return None
            
            return Result()

        def rollback(self):
            pass

        def commit(self):
            pass

        def close(self):
            pass

    with patch("orchestrator.state_sync.get_redis_client", return_value=fake):
        with patch("database.db.SessionLocal", return_value=FakeDB()):
            sync = StateSynchronizer()

            result = sync.sync_state_to_db(
                "missing-session",
                {"status": "running"},
            )

            assert result is False


def test_sync_state_to_db_updates_session():
    fake = FakeRedis()

    class FakeInterview:
        def __init__(self):
            self.status = "pending"
            self.risk_score = None
            self.video_analysis = None
            self.audio_analysis = None
            self.evaluation_analysis = None
            self.updated_at = None

    interview = FakeInterview()

    class FakeResult:
        def scalar_one_or_none(self):
            return interview

    class FakeDB:
        def __init__(self):
            self.committed = False

        def execute(self, *args, **kwargs):
            return FakeResult()

        def commit(self):
            self.committed = True

        def rollback(self):
            pass

        def close(self):
            pass

    fake_db = FakeDB()

    with patch("orchestrator.state_sync.get_redis_client", return_value=fake):
        with patch("database.db.SessionLocal", return_value=fake_db):
            sync = StateSynchronizer()

            data = {
                "status": "completed",
                "risk_score": 95,
            }

            result = sync.sync_state_to_db("session1", data)

            assert result is True
            assert interview.status == "completed"
            assert interview.risk_score == 95
            assert fake_db.committed is True

def test_set_session_state_returns_false_when_redis_fails():
    class FakeRedis:
        def set(self, *args, **kwargs):
            raise Exception("Redis error")

    with patch("orchestrator.state_sync.get_redis_client", return_value=FakeRedis()):
        sync = StateSynchronizer()

        result = sync.set_session_state(
            "session1",
            {"status": "running"},
        )

        assert result is False