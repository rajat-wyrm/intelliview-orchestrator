"""
FastAPI Orchestration Server
Main entry point for the AI Interview Orchestrator API

Integrates:
- Session Manager for lifecycle management
- Session Tracker for monitoring
- State Synchronizer for Redis/DB consistency
- Scheduler for intelligent task scheduling
- Load Balancer for worker distribution
- Worker Registry for node tracking
- Task Queue integration with Celery
"""

import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from config import (
    CORS_ALLOW_ORIGINS,
    MAX_REQUEST_BODY_BYTES,
    get_settings,
)
from database.db import engine
from database.models import Base
from database.subscriber_store import create_table, list_subscribers
from metrics.prometheus_metrics import REQUEST_COUNT, REQUEST_DURATION
from monitoring.dashboard_api import create_dashboard_routes
from monitoring.metrics_collector import MetricsCollector
from monitoring.websocket_manager import ws_manager
from orchestrator.candidate_manager import CandidateManager
from orchestrator.fault_manager import FaultManager
from orchestrator.health_monitor import HealthMonitor
from orchestrator.interview_templates import InterviewTemplateManager
from orchestrator.load_balancer import BalancingStrategy, LoadBalancer
from orchestrator.logging_config import configure_logging, log_event
from orchestrator.middleware.capacity_guard import CapacityGuardMiddleware
from orchestrator.notification_manager import NotificationManager
from orchestrator.question_bank import QuestionBank
from orchestrator.rate_limiter import RateLimiterMiddleware
from orchestrator.redis_client import get_redis_client
from orchestrator.request_validation import RequestValidationMiddleware
from orchestrator.retry_manager import RetryManager, RetryStrategy
from orchestrator.router import router as risk_configs_router
from orchestrator.scheduler import Scheduler
from orchestrator.session_manager import SessionManager
from orchestrator.session_tracker import SessionTracker
from orchestrator.state_sync import StateSynchronizer
from orchestrator.store import DEFAULT_WEIGHTS
from orchestrator.worker_registry import WorkerRegistry
from routers.admin import create_admin_routes
from routers.candidates import create_candidate_routes
from routers.health import create_health_routes
from routers.metrics import router as metrics_router
from routers.questions import create_question_routes
from routers.sessions import (  # noqa: F401 (re-exported for tests)
    StartInterviewRequest,
    create_session_routes,
)
from routers.templates import create_template_routes
from routers.workers import create_worker_routes

# Configure logging after imports so startup messages are structured.
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Execute on application startup/shutdown.

    Startup: ensure schema exists, run an initial health probe, and warn
    loudly if the default API token is still in use.

    Shutdown: best-effort graceful drain — flush the request-id log line,
    close the shared Redis client, and notify clients.
    """

    settings = get_settings()
    settings.validate_configuration()
    Base.metadata.create_all(bind=engine)

    # Seed admin user
    import uuid

    from passlib.context import CryptContext

    from database.db import SessionLocal
    from database.models import User

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def bcrypt_safe_password(password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer for bcrypt")
        return password

    with SessionLocal() as db:
        try:
            if not db.query(User).first():
                admin = User(
                    user_id=str(uuid.uuid4()),
                    email="admin@example.com",
                    password_hash=pwd_context.hash(bcrypt_safe_password("admin123")),
                    role="admin",
                )
                db.add(admin)
                db.commit()
                logger.info("Created initial admin user: admin@example.com / admin123")
        except ValueError as exc:
            logger.error("Startup user initialization failed: %s", exc)

    # Initialize webhook subscriber store
    create_table()

    subscribers = list_subscribers()
    logger.info("Loaded %d webhook subscribers", len(subscribers))

    logger.info("AI Interview Orchestrator server starting...")

    settings = get_settings()
    redis_client = get_redis_client()

    try:
        redis_client.hset(
            "config:startup",
            mapping={
                "worker_concurrency": str(settings.worker_concurrency),
                "max_retries": str(settings.max_retries),
                "cors_allow_origins": json.dumps(settings.cors_allow_origins),
                "realtime_enabled": str(settings.realtime_enabled),
                "moment_tracking_enabled": str(settings.moment_tracking_enabled),
            },
        )

        logger.info("Configuration cache warmed successfully.")

    except Exception as exc:
        logger.warning(
            "Configuration cache warm-up failed: %s",
            exc,
        )

    try:
        yield

    finally:
        logger.info("AI Interview Orchestrator server shutting down...")

        for resource in (ws_manager, state_sync, metrics_collector):
            close = getattr(resource, "close", None)
            if callable(close):
                try:
                    close()
                except Exception as exc:
                    logger.debug("shutdown close failed: %s", exc)
        # Close the shared Redis client
        from orchestrator.cache_manager import CacheManager

        rc = CacheManager()
        if rc is not None:
            try:
                rc.raw.close()
            except Exception:
                pass


# Initialize FastAPI application
app = FastAPI(
    title="AI Interview Orchestrator",
    description="Orchestration API for distributed interview processing",
    version="1.0.0",
    lifespan=lifespan,
)

logging.getLogger("opentelemetry.exporter.otlp.proto.grpc.exporter").setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()
otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True)
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

FastAPIInstrumentor.instrument_app(app)


@app.middleware("http")
async def prometheus_middleware(request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    duration = time.perf_counter() - start

    REQUEST_COUNT.labels(
        method=request.method,
        path=request.url.path,
        status=response.status_code,
    ).inc()

    REQUEST_DURATION.labels(
        method=request.method,
        path=request.url.path,
    ).observe(duration)

    return response


# ========== Request ID + duration middleware ==========

_VALID_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID, measures duration, and tags the response.

    Honours an incoming `X-Request-ID` header if it matches a safe format;
    otherwise generates a new UUID4. The ID is attached to the response as
    `X-Request-ID` so callers can correlate logs.
    """

    async def dispatch(self, request: StarletteRequest, call_next):
        incoming = request.headers.get("x-request-id", "").strip()
        request_id = incoming if _VALID_ID_RE.match(incoming) else uuid4().hex
        request.state.request_id = request_id
        trace.get_current_span().set_attribute("request_id", request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            log_event(
                logger,
                logging.ERROR,
                "unhandled_error",
                request_id=request_id,
                path=request.url.path,
                elapsed_ms=round(elapsed_ms, 1),
            )
            logger.debug("traceback", exc_info=True)
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.1f}"
        log_event(
            logger,
            logging.DEBUG if request.url.path == "/health" else logging.INFO,
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=round(elapsed_ms, 1),
        )
        return response


app.add_middleware(RequestContextMiddleware)
app.add_middleware(CapacityGuardMiddleware)

# CORS — configurable via env. Default "*" is for local dev only.
_cors_origins = (
    ["*"]
    if CORS_ALLOW_ORIGINS in ("*", "")
    else [o.strip() for o in CORS_ALLOW_ORIGINS.split(",") if o.strip()]
)
_allow_credentials = _cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    RateLimiterMiddleware,
    limit=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    window_seconds=60,
)
app.add_middleware(
    RequestValidationMiddleware,
    max_body_size_bytes=MAX_REQUEST_BODY_BYTES,
)


# Initialize managers and orchestrators
session_manager = SessionManager()
session_tracker = SessionTracker()
state_sync = StateSynchronizer()
load_balancer = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
worker_registry = WorkerRegistry()
scheduler = Scheduler(load_balancer=load_balancer, worker_registry=worker_registry)
fault_manager = FaultManager()
retry_manager = RetryManager(max_retries=3, strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
health_monitor = HealthMonitor()
metrics_collector = MetricsCollector()
question_bank = QuestionBank()
candidate_manager = CandidateManager()
interview_template_manager = InterviewTemplateManager()
notification_manager = NotificationManager()

# Register dashboard routes
dashboard_routes = create_dashboard_routes(
    metrics_collector=metrics_collector,
    session_manager=session_manager,
    worker_registry=worker_registry,
    session_tracker=session_tracker,
    fault_manager=fault_manager,
    retry_manager=retry_manager,
    health_monitor=health_monitor,
    ws_manager=ws_manager,
)
app.include_router(dashboard_routes, prefix="/monitoring", tags=["monitoring"])

# Register application routes
app.include_router(
    create_health_routes(
        health_monitor=health_monitor,
        worker_registry=worker_registry,
        session_manager=session_manager,
    )
)
app.include_router(
    create_session_routes(
        session_manager=session_manager,
        session_tracker=session_tracker,
        scheduler=scheduler,
        fault_manager=fault_manager,
        retry_manager=retry_manager,
        health_monitor=health_monitor,
        worker_registry=worker_registry,
        question_bank=question_bank,
    )
)
app.include_router(create_candidate_routes(candidate_manager=candidate_manager))
app.include_router(create_question_routes(question_bank=question_bank))
app.include_router(create_template_routes(interview_template_manager=interview_template_manager))
app.include_router(
    create_worker_routes(
        worker_registry=worker_registry,
        load_balancer=load_balancer,
        scheduler=scheduler,
        session_tracker=session_tracker,
    )
)
app.include_router(create_admin_routes(state_sync=state_sync, load_balancer=load_balancer))
app.include_router(risk_configs_router)

app.include_router(metrics_router)

from routers.auth import router as auth_router

app.include_router(auth_router)


@app.get("/risk-engine/weights/{role}")
def get_weights(role: str):
    from orchestrator import store

    config = store.get_config_by_position(role)
    weights = config.weights if config else DEFAULT_WEIGHTS
    return {"role": role, "weights": weights, "is_custom": config is not None}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
