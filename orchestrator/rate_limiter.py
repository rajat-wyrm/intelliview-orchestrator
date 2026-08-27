"""
Simple Redis-backed rate limiter middleware for FastAPI.

Uses a sliding-window counter stored in Redis. Each unique client
(IP + optional API key) gets a separate counter for each endpoint.
When the limit is exceeded the middleware returns 429 Too Many Requests.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from orchestrator.cache_manager import CacheManager

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 60
_DEFAULT_WINDOW_SECONDS = 60


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Per-client, per-endpoint sliding-window rate limiter backed by Redis.

    ``limit`` is the global fallback limit.

    ``endpoint_limits`` can override the global limit for specific paths,
    for example:

        {
            "/login": 5,
            "/health": 100,
        }

    Each endpoint uses its own Redis bucket, so limits are independent.
    """

    EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/docs", "/openapi.json"})

    def __init__(
        self,
        app,
        limit: int = _DEFAULT_LIMIT,
        window_seconds: int = _DEFAULT_WINDOW_SECONDS,
        endpoint_limits: Mapping[str, int] | None = None,
    ) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.endpoint_limits = dict(endpoint_limits or {})

    def _limit_for_path(self, path: str) -> int:
        """Return the endpoint-specific limit or the global fallback."""
        return self.endpoint_limits.get(path, self.limit)

    def _is_exempt(self, path: str) -> bool:
        """Return whether a path should bypass rate limiting.

        An explicitly configured endpoint takes precedence over the
        default exemption so paths such as /health can have a custom
        rate limit when required.
        """
        if path in self.endpoint_limits:
            return False

        return (
            path in self.EXEMPT_PATHS
            or path.startswith("/docs")
            or path == "/metrics/web-vitals"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if self._is_exempt(path):
            return await call_next(request)

        client_key = self._client_key(request)
        redis_client = CacheManager()

        if redis_client is None:
            return await call_next(request)

        try:
            now = time.time()
            window_start = now - self.window_seconds
            limit = self._limit_for_path(path)

            # Include the endpoint in the key so each endpoint has
            # an independent sliding-window counter.
            redis_key = f"ratelimit:{client_key}:{path}"

            pipe = redis_client.raw.pipeline(transaction=False)

            # Remove entries outside the window
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # Add current request
            pipe.zadd(redis_key, {str(now): now})

            # Count requests in window
            pipe.zcard(redis_key)

            # Set TTL so old keys are cleaned up automatically
            pipe.expire(redis_key, self.window_seconds * 2)

            results = pipe.execute()
            request_count = results[2]

            if request_count > limit:
                retry_after = int(self.window_seconds - (now - window_start))

                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": max(retry_after, 1),
                    },
                    headers={"Retry-After": str(max(retry_after, 1))},
                )

        except Exception as exc:
            logger.debug("Rate limiter error (allowing request): %s", exc)

        return await call_next(request)

    @staticmethod
    def _client_key(request: Request) -> str:
        """Build a composite key: IP + optional API token."""
        forwarded = request.headers.get("x-forwarded-for")

        ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else request.client.host if request.client else "unknown"
        )

        token = request.headers.get("x-api-token", "")

        return f"{ip}:{token}"
