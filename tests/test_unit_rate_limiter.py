from fastapi import FastAPI
from fastapi.testclient import TestClient

from orchestrator.rate_limiter import RateLimiterMiddleware

# -------------------------
# Fake Redis implementation
# -------------------------


class FakePipeline:
    def __init__(self, redis_raw):
        self.redis_raw = redis_raw
        self.current_key = None

    def zremrangebyscore(self, redis_key, *args, **kwargs):
        self.current_key = redis_key
        return self

    def zadd(self, redis_key, *args, **kwargs):
        self.current_key = redis_key

        if redis_key not in self.redis_raw.counts:
            self.redis_raw.counts[redis_key] = self.redis_raw.initial_count

        self.redis_raw.counts[redis_key] += 1
        return self

    def zcard(self, redis_key, *args, **kwargs):
        self.current_key = redis_key
        return self

    def expire(self, *args, **kwargs):
        return self

    def execute(self):
        return [
            None,
            None,
            self.redis_raw.counts.get(self.current_key, 0),
            None,
        ]


class FakeRedisRaw:
    def __init__(self, initial_count=0):
        self.initial_count = initial_count
        self.counts = {}

    def pipeline(self, transaction=False):
        return FakePipeline(self)


class FakeRedisClient:
    def __init__(self, count=0):
        self.raw = FakeRedisRaw(count)


# -------------------------
# Helper
# -------------------------


def create_app(monkeypatch, request_count=0, endpoint_limits=None):
    from orchestrator import cache_manager

    monkeypatch.setattr(
        cache_manager,
        "get_redis_client",
        lambda: FakeRedisClient(request_count),
    )
    cache_manager.CacheManager._instance = None

    app = FastAPI()

    app.add_middleware(
        RateLimiterMiddleware,
        limit=5,
        window_seconds=60,
        endpoint_limits=endpoint_limits,
    )

    @app.get("/hello")
    async def hello():
        return {"message": "ok"}

    @app.get("/strict")
    async def strict():
        return {"message": "strict"}

    @app.get("/relaxed")
    async def relaxed():
        return {"message": "relaxed"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return TestClient(app)


# -------------------------
# Existing behavior tests
# -------------------------


def test_request_allowed(monkeypatch):
    client = create_app(monkeypatch, request_count=3)

    response = client.get("/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "ok"}


def test_rate_limit_exceeded(monkeypatch):
    client = create_app(monkeypatch, request_count=10)

    response = client.get("/hello")

    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded"
    assert "Retry-After" in response.headers


def test_health_endpoint_is_exempt(monkeypatch):
    client = create_app(monkeypatch, request_count=100)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_client_key_with_api_token():
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [
            (b"x-api-token", b"abc123"),
        ],
        "client": ("127.0.0.1", 5000),
    }

    request = Request(scope)

    key = RateLimiterMiddleware._client_key(request)

    assert key == "127.0.0.1:abc123"


def test_client_key_without_token():
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [],
        "client": ("127.0.0.1", 5000),
    }

    request = Request(scope)

    key = RateLimiterMiddleware._client_key(request)

    assert key == "127.0.0.1:"


# -------------------------
# New per-endpoint tests
# -------------------------


def test_different_endpoints_have_independent_limits(monkeypatch):
    client = create_app(
        monkeypatch,
        request_count=0,
        endpoint_limits={
            "/strict": 1,
            "/relaxed": 3,
        },
    )

    # /strict has a limit of 1 request per window.
    assert client.get("/strict").status_code == 200
    assert client.get("/strict").status_code == 429

    # /relaxed has its own independent limit of 3 requests per window.
    assert client.get("/relaxed").status_code == 200
    assert client.get("/relaxed").status_code == 200
    assert client.get("/relaxed").status_code == 200
    assert client.get("/relaxed").status_code == 429


def test_configured_exempt_endpoint_uses_custom_limit(monkeypatch):
    client = create_app(
        monkeypatch,
        request_count=0,
        endpoint_limits={
            "/health": 2,
        },
    )

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 429
