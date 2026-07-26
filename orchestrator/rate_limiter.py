"""
Simple Redis-backed rate limiter middleware for FastAPI.

Uses a sliding-window counter stored in Redis.  Each unique client
(IP + optional API key) gets a separate counter.  When the limit is
exceeded the middleware returns 429 Too Many Requests.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from orchestrator.cache_manager import CacheManager

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 60  # requests per window
_DEFAULT_WINDOW_SECONDS = 60  # 1 minute window


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Per-client sliding-window rate limiter backed by Redis.

    The key is derived from the client IP and the ``X-API-Token``
    header (if present).  Paths under ``/health`` and ``/docs`` are
    exempt from limiting.
    """

    EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/docs", "/openapi.json"})

    def __init__(
        self,
        app,
        limit: int = _DEFAULT_LIMIT,
        window_seconds: int = _DEFAULT_WINDOW_SECONDS,
    ) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in self.EXEMPT_PATHS or path.startswith("/docs"):
            return await call_next(request)

        client_key = self._client_key(request)
        redis_client = CacheManager()

        if redis_client is None:
            return await call_next(request)

        try:
            now = time.time()
            window_start = now - self.window_seconds
            redis_key = f"ratelimit:{client_key}"

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

            if request_count > self.limit:
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
            else request.client.host
            if request.client
            else "unknown"
        )
        token = request.headers.get("x-api-token", "")
        return f"{ip}:{token}"
