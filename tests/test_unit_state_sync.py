"""Unit tests for StateSynchronizer."""

import json
<<<<<<< HEAD
from unittest.mock import patch
=======
from unittest.mock import  MagicMock ,patch

>>>>>>> 9869eb6 (Updated unit tests for state sync)
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

# ...continue with all the remaining StateSynchronizer tests exactly as they were...
