"""
Shared Redis Client

Provides a singleton Redis connection for all components, plus a circuit
breaker that stops hammering Redis when it is down and automatically
recovers after a cooldown period.
"""

from __future__ import annotations

import enum
import logging
import time
from typing import Any

import redis

from config import REDIS_URL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class _CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker for Redis operations.

    States:
        CLOSED  – normal operation, failures are counted.
        OPEN    – Redis is considered down; all calls short-circuit.
        HALF_OPEN – cooldown elapsed, allow one probe through.

    Transitions:
        CLOSED  -> OPEN      when failure_count >= failure_threshold
        OPEN    -> HALF_OPEN after cooldown_seconds
        HALF_OPEN -> CLOSED  on success
        HALF_OPEN -> OPEN    on failure
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: int = 30,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._state = _CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float = 0.0

    @property
    def state(self) -> _CircuitState:
        if self._state == _CircuitState.OPEN:
            if time.monotonic() - self._opened_at >= self.cooldown_seconds:
                self._state = _CircuitState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        s = self.state
        return s in (_CircuitState.CLOSED, _CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = _CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._state = _CircuitState.OPEN
            self._opened_at = time.monotonic()
            logger.warning(
                "Circuit breaker OPEN after %d consecutive failures",
                self._failure_count,
            )

    def reset(self) -> None:
        self._failure_count = 0
        self._state = _CircuitState.CLOSED


# Module-level singleton breaker
circuit_breaker = CircuitBreaker()


# ---------------------------------------------------------------------------
# Shared Redis client
# ---------------------------------------------------------------------------


class _RedisClientWrapper:
    """Thin wrapper that routes calls through the circuit breaker."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    # Provide the raw client for advanced operations (pipeline, scan_iter …)
    @property
    def raw(self) -> redis.Redis:
        return self._client

    # ---- pass-through helpers -------------------------------------------

    def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        if not circuit_breaker.allow_request():
            raise redis.ConnectionError("Circuit breaker OPEN - Redis is down")
        try:
            result = getattr(self._client, method)(*args, **kwargs)
            circuit_breaker.record_success()
            return result
        except (redis.ConnectionError, redis.TimeoutError):
            circuit_breaker.record_failure()
            raise

    # Common read/write operations
    def get(self, *a: Any, **kw: Any) -> Any:
        return self._call("get", *a, **kw)

    def set(self, *a: Any, **kw: Any) -> Any:
        return self._call("set", *a, **kw)

    def delete(self, *a: Any, **kw: Any) -> Any:
        return self._call("delete", *a, **kw)

    def ping(self) -> bool:
        return self._call("ping")

    def incr(self, *a: Any, **kw: Any) -> Any:
        return self._call("incr", *a, **kw)

    def expire(self, *a: Any, **kw: Any) -> Any:
        return self._call("expire", *a, **kw)

    def hset(self, *a: Any, **kw: Any) -> Any:
        return self._call("hset", *a, **kw)

    def hget(self, *a: Any, **kw: Any) -> Any:
        return self._call("hget", *a, **kw)

    def hgetall(self, *a: Any, **kw: Any) -> Any:
        return self._call("hgetall", *a, **kw)

    def hincrby(self, *a: Any, **kw: Any) -> Any:
        return self._call("hincrby", *a, **kw)

    def sadd(self, *a: Any, **kw: Any) -> Any:
        return self._call("sadd", *a, **kw)

    def srem(self, *a: Any, **kw: Any) -> Any:
        return self._call("srem", *a, **kw)

    def smembers(self, *a: Any, **kw: Any) -> Any:
        return self._call("smembers", *a, **kw)

    def scan(self, *a: Any, **kw: Any) -> Any:
        return self._call("scan", *a, **kw)

    def scan_iter(self, *a: Any, **kw: Any) -> Any:
        if not circuit_breaker.allow_request():
            return iter([])
        try:
            result = self._client.scan_iter(*a, **kw)
            circuit_breaker.record_success()
            return result
        except (redis.ConnectionError, redis.TimeoutError):
            circuit_breaker.record_failure()
            raise

    def lpush(self, *a: Any, **kw: Any) -> Any:
        return self._call("lpush", *a, **kw)

    def lrange(self, *a: Any, **kw: Any) -> Any:
        return self._call("lrange", *a, **kw)

    def ltrim(self, *a: Any, **kw: Any) -> Any:
        return self._call("ltrim", *a, **kw)

    def llen(self, *a: Any, **kw: Any) -> Any:
        return self._call("llen", *a, **kw)

    def info(self, *a: Any, **kw: Any) -> Any:
        return self._call("info", *a, **kw)


def get_redis() -> _RedisClientWrapper:
    """Alias for get_redis_client() for backward compatibility."""
    return get_redis_client()


# Singleton instances
_client_instance: _RedisClientWrapper | None = None
_redis_url: str | None = None


def get_redis_client(url: str | None = None) -> _RedisClientWrapper:
    """Return the shared Redis client, creating it on first call.

    If *url* is provided on a subsequent call and differs from the one used
    to create the existing client a new connection is established (useful
    for testing).
    """
    global _client_instance, _redis_url
    target = url or REDIS_URL
    if _client_instance is not None and _redis_url == target:
        return _client_instance
    try:
        pool = redis.ConnectionPool.from_url(
            target,
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        raw = redis.Redis(connection_pool=pool)
        raw.ping()
        _client_instance = _RedisClientWrapper(raw)
        _redis_url = target
        logger.info("Shared Redis client connected to %s (pool max=%d)", target, 20)
    except Exception as exc:
        logger.error("Failed to connect to Redis at %s: %s", target, exc)
        _client_instance = _RedisClientWrapper(redis.Redis())
        _redis_url = target
    return _client_instance
