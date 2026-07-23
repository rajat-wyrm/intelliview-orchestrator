"""
Unified Cache Manager

Provides a single abstraction layer for cache operations over the shared
Redis client.
"""

from __future__ import annotations

from typing import Any

from orchestrator.redis_client import get_redis_client


class CacheManager:
    """Unified cache abstraction over the shared Redis client."""

    _instance: CacheManager | None = None

    def __new__(cls) -> CacheManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = get_redis_client()
        return cls._instance

    @property
    def client(self) -> Any:
        """Return the underlying Redis client wrapper."""
        return self._client

    def get(self, key: str) -> Any:
        return self._client.get(key)

    def set(self, key: str, value: Any, **kwargs: Any) -> Any:
        return self._client.set(key, value, **kwargs)

    def delete(self, *keys: str) -> Any:
        return self._client.delete(*keys)

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown operations to the wrapped Redis client."""
        return getattr(self._client, name)
