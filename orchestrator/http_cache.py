from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from orchestrator.cache_manager import CacheManager

_TTL_PREFIX = "httpcache:"
_DEFAULT_TTL = 2  # seconds — dashboard polls every 5s

# Memory locks to handle local single-flight concurrency (stampede prevention)
_sync_locks: dict[str, Any] = {}
_async_locks: dict[str, asyncio.Lock] = {}


def _client():
    return CacheManager()


def _make_key(name: str, args: tuple, kwargs: dict) -> str:
    """Generates a unique, deterministic cache key factoring in arguments."""
    if not args and not kwargs:
        return f"{_TTL_PREFIX}{name}"
    
    # Serialize arguments safely for hashing
    arg_str = json.dumps((args, sorted(kwargs.items())), default=str)
    arg_hash = hashlib.md5(arg_str.encode("utf-8")).hexdigest()
    return f"{_TTL_PREFIX}{name}:{arg_hash}"


def get(key: str) -> Any | None:
    c = _client()
    if c is None:
        return None
    try:
        raw = c.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def async_get(key: str) -> Any | None:
    """Non-blocking Redis fetch for async paths."""
    c = _client()
    if c is None:
        return None
    try:
        # Assumes your get_redis_client() provider supports an awaitable client
        if asyncio.iscoroutinefunction(c.get):
            raw = await c.get(key)
        else:
            raw = await asyncio.to_thread(c.get, key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def set_cache(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    c = _client()
    if c is None:
        return
    try:
        c.set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass


async def async_set_cache(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    """Non-blocking Redis storage for async paths."""
    c = _client()
    if c is None:
        return
    try:
        payload = json.dumps(value)
        if asyncio.iscoroutinefunction(c.set):
            await c.set(key, payload, ex=ttl)
        else:
            await asyncio.to_thread(c.set, key, payload, ex=ttl)
    except Exception:
        pass


def invalidate(*names: str) -> None:
    c = _client()
    if c is None:
        return
    try:
        if names:
            # Matches names regardless of argument hash suffixes
            for name in names:
                for k in c.scan_iter(f"{_TTL_PREFIX}{name}*", count=100):
                    c.delete(k)
        else:
            for k in c.scan_iter(f"{_TTL_PREFIX}*", count=100):
                c.delete(k)
    except Exception:
        pass


def cached(name: str, ttl: int = _DEFAULT_TTL) -> Callable:
    """Decorator: Cache function returns in Redis with stampede protection.
    
    Differentiates sync and async logic cleanly without blocking event loops.
    """
    import inspect

    def deco(fn: Callable) -> Callable:
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                cache_key = _make_key(name, args, kwargs)
                
                # First check
                hit = await async_get(cache_key)
                if hit is not None:
                    return hit

                # Get or create single-flight lock for this specific cache key
                if cache_key not in _async_locks:
                    _async_locks[cache_key] = asyncio.Lock()
                
                async with _async_locks[cache_key]:
                    # Double-check pattern: look again now that we hold the lock
                    hit = await async_get(cache_key)
                    if hit is not None:
                        return hit

                    result = await fn(*args, **kwargs)
                    if isinstance(result, (dict, list)):
                        await async_set_cache(cache_key, result, ttl=ttl)
                    return result

            return async_wrapper

        else:

            @wraps(fn)
            def sync_wrapper(*args, **kwargs):
                import threading
                cache_key = _make_key(name, args, kwargs)
                
                hit = get(cache_key)
                if hit is not None:
                    return hit

                if cache_key not in _sync_locks:
                    _sync_locks[cache_key] = threading.Lock()

                with _sync_locks[cache_key]:
                    hit = get(cache_key)
                    if hit is not None:
                        return hit

                    result = fn(*args, **kwargs)
                    if isinstance(result, (dict, list)):
                        set_cache(cache_key, result, ttl=ttl)
                    return result

            return sync_wrapper

    return deco
