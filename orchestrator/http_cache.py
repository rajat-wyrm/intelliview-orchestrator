"""Small HTTP-cache helper backed by Redis.

Lets us stamp a TTL on a JSON response so the dashboard's `refreshInterval`
polls return in microseconds when nothing has changed. The cache is
best-effort: on any Redis error we fall back to recomputing the value.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from orchestrator.cache_manager import CacheManager

_TTL_PREFIX = "httpcache:"
_DEFAULT_TTL = 2  # seconds — short, dashboard polls every 5s


def _client():
    return CacheManager()


def _key(name: str) -> str:
    return f"{_TTL_PREFIX}{name}"


def get(name: str) -> Any | None:
    c = _client()
    if c is None:
        return None
    try:
        raw = c.get(_key(name))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def set(name: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    c = _client()
    if c is None:
        return
    try:
        c.set(_key(name), json.dumps(value), ex=ttl)
    except Exception:
        pass


def invalidate(*names: str) -> None:
    c = _client()
    if c is None:
        return
    try:
        if names:
            c.delete(*[_key(n) for n in names])
        else:
            for k in c.scan_iter(f"{_TTL_PREFIX}*", count=100):
                c.delete(k)
    except Exception:
        pass


def cached(name: str, ttl: int = _DEFAULT_TTL) -> Callable:
    """Decorator: cache the wrapped function's return value in Redis.

    Works for both sync and async callables. Returns the cached value
    on hit; otherwise invokes the function, caches the result, and
    returns it.
    """

    def deco(fn: Callable) -> Callable:
        if _is_coro(fn):

            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                hit = get(name)
                if hit is not None:
                    return hit
                result = await fn(*args, **kwargs)
                if isinstance(result, (dict, list)):
                    set(name, result, ttl=ttl)
                return result

            return async_wrapper

        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            hit = get(name)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            if isinstance(result, (dict, list)):
                set(name, result, ttl=ttl)
            return result

        return sync_wrapper

    return deco


def _is_coro(fn: Callable) -> bool:
    import inspect

    return inspect.iscoroutinefunction(fn)
