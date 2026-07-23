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

import io
import logging
import re
import time as _time
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from monitoring.prometheus_metrics import (REQUEST_COUNT,REQUEST_DURATION,)

from config import (
    API_TOKEN,
    CORS_ALLOW_ORIGINS,
    ENABLE_PROMETHEUS,
    MAX_REQUEST_BODY_BYTES,
)
from database.db import engine, get_db
from database.models import Base, InterviewSession, Candidate
from sqlalchemy import select
from monitoring.dashboard_api import create_dashboard_routes
from monitoring.metrics_collector import MetricsCollector
from monitoring.websocket_manager import ws_manager
from orchestrator import http_cache
from orchestrator.candidate_manager import CandidateManager
from orchestrator.fault_manager import FaultManager
from orchestrator.health_monitor import HealthMonitor
from orchestrator.interview_templates import InterviewTemplateManager
from orchestrator.load_balancer import BalancingStrategy, LoadBalancer
from orchestrator.logging_config import configure_logging, log_event
from orchestrator.question_bank import QuestionBank
from orchestrator.rate_limiter import RateLimiterMiddleware
from orchestrator.redis_client import circuit_breaker
from orchestrator.request_validation import RequestValidationMiddleware
from orchestrator.retry_manager import RetryManager, RetryStrategy
from orchestrator.scheduler import Scheduler, TaskPriority
from orchestrator.session_manager import SessionManager
from orchestrator.session_tracker import SessionTracker
from orchestrator.state_sync import StateSynchronizer
from orchestrator.worker_registry import WorkerRegistry
from workers.bias_auditor import BiasAuditor

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
    Base.metadata.create_all(bind=engine)
    if API_TOKEN == "dev-token-change-me":
        logger.warning(
            "API_TOKEN is the built-in dev default — set a strong token "
            "in production via the API_TOKEN env var."
        )
    logger.info("AI Interview Orchestrator server starting...")
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
        start = _time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (_time.perf_counter() - start) * 1000
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
        elapsed_ms = (_time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.1f}"
        if request.url.path != "/health":
            log_event(
                logger,
                logging.INFO,
                "request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                elapsed_ms=round(elapsed_ms, 1),
            )
        return response


app.add_middleware(RequestContextMiddleware)

# CORS — configurable via env. Default "*" is for local dev only.
_cors_origins = (
    ["*"]
    if CORS_ALLOW_ORIGINS in ("*", "")
    else [o.strip() for o in CORS_ALLOW_ORIGINS.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimiterMiddleware, limit=60, window_seconds=60)
app.add_middleware(
    RequestValidationMiddleware,
    max_body_size_bytes=MAX_REQUEST_BODY_BYTES,
)


# ========== Auth ==========


def require_token(x_api_token: str | None = Header(default=None)) -> None:
    """Dependency that requires a valid API token.

    Worker agents (and any privileged caller) must send `X-API-Token`.
    Set the expected token via the API_TOKEN env var.
    """
    if not API_TOKEN or API_TOKEN == "dev-token-change-me":
        # In dev with the default token, accept but log.
        logger.debug("Using default API token — set API_TOKEN in production")
    if x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="invalid or missing API token")


# Initialize managers and orchestrators
session_manager = SessionManager()
session_tracker = SessionTracker()
state_sync = StateSynchronizer()
load_balancer = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
scheduler = Scheduler(load_balancer=load_balancer)
worker_registry = WorkerRegistry()
fault_manager = FaultManager()
retry_manager = RetryManager(max_retries=3, strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
health_monitor = HealthMonitor()
metrics_collector = MetricsCollector()
question_bank = QuestionBank()
candidate_manager = CandidateManager()
interview_template_manager = InterviewTemplateManager()

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


# ========== Request/Response Models ==========


class StartInterviewRequest(BaseModel):
    """Request model for starting an interview"""

    candidate_id: str = Field(min_length=1, max_length=128, description="Unique candidate identifier")
    candidate_name: str | None = Field(default=None, max_length=200)
    position: str | None = Field(default=None, max_length=120)
    priority: str = Field(default="medium", description="One of: low, medium, high")

    @field_validator("candidate_id")
    @classmethod
    def _candidate_id_format(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[A-Za-z0-9._-]+$", v):
            raise ValueError("candidate_id may only contain letters, digits, '.', '_', '-'")
        return v

    @field_validator("priority")
    @classmethod
    def _priority_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"low", "medium", "high"}:
            raise ValueError("priority must be one of: low, medium, high")
        return v

    @field_validator("candidate_name", "position")
    @classmethod
    def _strip_optional(cls, v):
        return v.strip() if isinstance(v, str) else v


class WorkerRegistrationRequest(BaseModel):
    """Request model for worker registration"""

    worker_id: str
    capacity: int = 4


class WorkerHeartbeatRequest(BaseModel):
    """Request model for worker heartbeat"""

    worker_id: str
    active_tasks: int


class InterviewSessionResponse(BaseModel):
    """Response model for interview session"""

    session_id: str
    status: str
    created_at: str | None = None
    candidate_id: str
    risk_score: float | None = None
    estimated_wait_time: int | None = None


class SessionStatusResponse(BaseModel):
    """Response model for session status"""

    session_id: str
    status: str
    candidate_id: str
    risk_score: float | None = None
    assigned_node: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    updated_at: str | None = None


class ReportCandidate(BaseModel):
    candidate_id: str
    name: str
    email: str


class ReportInterviewSummary(BaseModel):
    start_time: str | None = None
    end_time: str | None = None
    duration_minutes: float | None = None


class ReportQuestion(BaseModel):
    question_id: str
    text: str
    answer: str | None = None
    score: float | None = None
    feedback: str | None = None


class ReportEvaluation(BaseModel):
    quality: float | None = None
    accuracy: float | None = None
    clarity: float | None = None


class ReportLLMFeedback(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    detailed_feedback: str | None = None


class ReportRiskAssessment(BaseModel):
    score: float | None = None
    classification: str | None = None
    factors: list[str] = Field(default_factory=list)


class ReportMetadata(BaseModel):
    token_usage: int | None = None
    estimated_cost_usd: float | None = None


class InterviewReportResponse(BaseModel):
    """Comprehensive final interview report"""

    session_id: str
    candidate: ReportCandidate
    interview_summary: ReportInterviewSummary
    questions: list[ReportQuestion] = Field(default_factory=list)
    overall_evaluation: ReportEvaluation
    llm_feedback: ReportLLMFeedback
    risk_assessment: ReportRiskAssessment
    metadata: ReportMetadata


class TaskStatusResponse(BaseModel):
    """Response model for Celery task status (used by /task-status/{task_id})."""

    session_id: str
    task_id: str
    status: str
    result: dict | None = None


# ========== Interview Feature Request/Response Models ==========


class AskQuestionRequest(BaseModel):
    """Request model for getting next question in a session"""

    session_id: str
    category: str | None = None


class AskQuestionResponse(BaseModel):
    """Response model for a question"""

    session_id: str
    question_id: str
    text: str
    category: str
    difficulty: str


class SubmitAnswerRequest(BaseModel):
    """Request model for submitting an answer"""

    session_id: str
    question_id: str
    answer_text: str
    score: float | None = Field(default=None, ge=0, le=10)


class SubmitAnswerResponse(BaseModel):
    """Response model after submitting an answer"""

    session_id: str
    question_id: str
    feedback: str
    score: float | None = None
    questions_asked: int
    overall_score: float | None = None


class AddQuestionRequest(BaseModel):
    """Request model for adding a question to the bank"""

    text: str = Field(min_length=1, max_length=1000)
    category: str
    difficulty: str = "medium"
    tags: list[str] | None = None


class CreateCandidateRequest(BaseModel):
    """Request model for creating a candidate profile"""

    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1, max_length=255)
    resume_text: str | None = None
    skills: list[str] | None = None


class CreateTemplateRequest(BaseModel):
    """Request model for creating an interview template"""

    name: str = Field(min_length=1, max_length=200)
    interview_type: str
    description: str | None = None
    duration_minutes: int = 60
    question_count: int = 10
    category_distribution: dict[str, float] | None = None
    difficulty_distribution: dict[str, float] | None = None


@app.get("/health")

# ========== Deep Health & Probe Endpoints ==========


@app.get("/livez")
async def liveness_probe():
    """Kubernetes-style liveness probe. Returns 200 if the process is alive."""
    return health_monitor.liveness_check()


@app.get("/readyz")
async def readiness_probe():
    """Kubernetes-style readiness probe. Returns 200 only when all dependencies are up."""
    result = health_monitor.readiness_check()
    if not result["ready"]:
        from fastapi.responses import JSONResponse as _JSONResponse

        return _JSONResponse(status_code=503, content=result)
    return result


@app.get("/dependencies")
async def get_dependency_statuses():
    """Deep health check of all dependencies (Redis, Postgres, Celery broker)."""
    return health_monitor._check_all_dependencies()


@app.get("/admin/fairness-audit", dependencies=[Depends(require_token)])
async def get_fairness_audit_report():
    """Return a lightweight fairness audit report for recent scoring patterns.

    This endpoint uses the existing BiasAuditor heuristic for scoring-dispersion
    review. It is intentionally informational and does not replace a full
    compliance or fairness assessment framework.
    """
    try:
        auditor = BiasAuditor(db_session=None)
        evaluations = []
        return auditor.analyze_scoring_consistency(evaluations, "gender")
    except Exception as exc:
        logger.error("Fairness audit endpoint failed: %s", exc)
        raise HTTPException(status_code=500, detail="Fairness audit unavailable") from exc


# ========== Prometheus Metrics Endpoint ==========


if ENABLE_PROMETHEUS:
    from fastapi.responses import Response as _Response

    from monitoring.prometheus_metrics import get_metrics_text

    @app.get("/metrics")
    async def prometheus_metrics():
        REDIS_HEALTH.set(...)
        POSTGRES_HEALTH.set(...)
        WORKERS_REGISTERED.set(...)
        WORKERS_HEALTHY.set(...)
        WORKERS_UNHEALTHY.set(...)
        """Prometheus metrics endpoint."""
        return _Response(
            content=get_metrics_text(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )


@app.get("/circuit-breaker")
async def get_circuit_breaker_status():
    """Return the current state of the Redis circuit breaker."""
    return {
        "state": circuit_breaker.state.value,
        "failure_count": circuit_breaker._failure_count,
        "failure_threshold": circuit_breaker.failure_threshold,
        "cooldown_seconds": circuit_breaker.cooldown_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ========== Interview Session Endpoints ==========


@app.post(
    "/start-interview",
    response_model=InterviewSessionResponse,
    dependencies=[Depends(require_token)],
)
async def start_interview(
    request: StartInterviewRequest,
    session_db: Session = Depends(get_db),
):
    """
    Start a new interview session using intelligent scheduling

    Execution flow:
    1. Create session in database (status: CREATED)
    2. Cache session in Redis
    3. Update status to QUEUED
    4. Use Scheduler to intelligently assign to worker
    5. Task pushed to Redis queue and/or assigned to specific worker

    Args:
        request: Interview session request with candidate details

    Returns:
        InterviewSessionResponse: Created session details with estimated wait time

    Raises:
        HTTPException: On creation failure
    """
    try:
        logger.info(f"API: Creating interview session for candidate {request.candidate_id}")

        # Parse priority
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
        }
        priority = priority_map.get(request.priority.lower(), TaskPriority.MEDIUM)

        # Create session
        session_id = session_manager.create_session(
            candidate_id=request.candidate_id,
            candidate_name=request.candidate_name,
            position=request.position,
        )

        logger.info(f"Session created: {session_id}")

        # Update status to QUEUED
        session_manager.update_session_status(session_id, session_manager.QUEUED, {"priority": priority.name})

        # Check if system can accept task
        if not scheduler.can_accept_task():
            logger.warning(f"System at capacity, queuing task: {session_id}")

        # Use scheduler to intelligently assign task
        scheduler.schedule_task(session_id, priority=priority)

        # Get estimated wait time
        wait_time = scheduler.get_estimated_wait_time(priority)

        # Invalidate the read caches so the next poll reflects the new
        # session immediately instead of waiting for the TTL.
        http_cache.invalidate("active-sessions", "session-statistics", "workers", "worker-statistics")

        # Retrieve and return session details
        session_data = session_manager.get_session(session_id)

        return InterviewSessionResponse(
            session_id=session_id,
            status=session_manager.QUEUED,
            created_at=session_data.get("created_at"),
            candidate_id=request.candidate_id,
            risk_score=None,
            estimated_wait_time=wait_time if wait_time >= 0 else None,
        )

    except Exception as e:
        logger.error(f"Error starting interview session: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error starting interview: {e!s}")


@app.get("/session-status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    session_db: Session = Depends(get_db),
):
    """
    Get current status of an interview session

    Retrieves real-time session information including:
    - Current status (CREATED, QUEUED, PROCESSING, COMPLETED, FAILED)
    - Risk score if available
    - Processing node information
    - Timestamps

    Args:
        session_id: Interview session identifier

    Returns:
        SessionStatusResponse: Current session status and details

    Raises:
        HTTPException: If session not found
    """
    try:
        logger.debug(f"API: Fetching status for session {session_id}")

        session_data = session_manager.get_session(session_id)

        if not session_data:
            logger.warning(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionStatusResponse(
            session_id=session_id,
            status=session_data.get("status"),
            candidate_id=session_data.get("candidate_id"),
            risk_score=session_data.get("risk_score"),
            assigned_node=session_data.get("assigned_node"),
            start_time=session_data.get("start_time"),
            end_time=session_data.get("end_time"),
            updated_at=session_data.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session status: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching session: {e!s}")


@app.get("/interviews/{session_id}/report", response_model=InterviewReportResponse)
async def get_interview_report(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Get comprehensive final interview report.
    """
    try:
        session_obj = db.execute(
            select(InterviewSession).where(InterviewSession.session_id == session_id)
        ).scalar_one_or_none()

        if not session_obj:
            raise HTTPException(status_code=404, detail="Session not found")

        candidate_obj = db.execute(
            select(Candidate).where(Candidate.candidate_id == session_obj.candidate_id)
        ).scalar_one_or_none()

        if not candidate_obj:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Calculate duration
        duration_minutes = None
        if session_obj.start_time and session_obj.end_time:
            duration_delta = session_obj.end_time - session_obj.start_time
            duration_minutes = round(duration_delta.total_seconds() / 60.0, 2)

        # Map questions, answers, feedback
        q_asked = session_obj.questions_asked or []
        a_provided = session_obj.answers_provided or []
        f_generated = session_obj.feedback_generated or []
        
        # Build question lookup
        q_dict = {q.get("question_id"): q for q in q_asked}
        for a in a_provided:
            q_id = a.get("question_id")
            if q_id in q_dict:
                q_dict[q_id]["answer"] = a.get("answer_text")
        for f in f_generated:
            q_id = f.get("question_id")
            if q_id in q_dict:
                q_dict[q_id]["feedback"] = f.get("feedback")
                q_dict[q_id]["score"] = f.get("score")
                
        questions_list = []
        for q_id, q_data in q_dict.items():
            questions_list.append(
                ReportQuestion(
                    question_id=q_id,
                    text=q_data.get("text", ""),
                    answer=q_data.get("answer"),
                    score=q_data.get("score"),
                    feedback=q_data.get("feedback")
                )
            )
            
        eval_analysis = session_obj.evaluation_analysis or {}
        llm_feedback = eval_analysis.get("llm_feedback", {})
        
        # Since evaluation_analysis structure might differ based on other PRs, 
        # we will handle nested or flat structures for strengths/improvements.
        strengths = eval_analysis.get("strengths", llm_feedback.get("strengths", []))
        improvements = eval_analysis.get("improvements", llm_feedback.get("improvements", []))
        recommendation = eval_analysis.get("recommendation", llm_feedback.get("recommendation"))
        detailed_feedback = eval_analysis.get("detailed_feedback", llm_feedback.get("detailed_feedback"))
        
        # Determine risk classification
        risk_score = session_obj.risk_score
        classification = "LOW"
        if risk_score is not None:
            if risk_score > 0.7:
                classification = "HIGH"
            elif risk_score > 0.3:
                classification = "MEDIUM"

        return InterviewReportResponse(
            session_id=session_id,
            candidate=ReportCandidate(
                candidate_id=candidate_obj.candidate_id,
                name=candidate_obj.name,
                email=candidate_obj.email
            ),
            interview_summary=ReportInterviewSummary(
                start_time=session_obj.start_time.isoformat() if session_obj.start_time else None,
                end_time=session_obj.end_time.isoformat() if session_obj.end_time else None,
                duration_minutes=duration_minutes
            ),
            questions=questions_list,
            overall_evaluation=ReportEvaluation(
                quality=eval_analysis.get("quality"),
                accuracy=eval_analysis.get("accuracy"),
                clarity=eval_analysis.get("clarity")
            ),
            llm_feedback=ReportLLMFeedback(
                strengths=strengths,
                improvements=improvements,
                recommendation=recommendation,
                detailed_feedback=detailed_feedback
            ),
            risk_assessment=ReportRiskAssessment(
                score=risk_score,
                classification=classification,
                factors=eval_analysis.get("risk_factors", [])
            ),
            metadata=ReportMetadata(
                token_usage=None,  # Feature #3 not yet merged
                estimated_cost_usd=None
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching interview report: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching report: {e!s}")

@app.get("/session-status/{session_id}/risk-report")
async def get_session_risk_report(session_id: str, format: str = "json"):
    """
    Get a full detailed risk report for a session, as JSON or downloadable PDF.

    Args:
        session_id: Interview session identifier
        format: "json" (default) or "pdf"
    """
    try:
        session_data = session_manager.get_session(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        report = {
            "session_id": session_id,
            "candidate_id": session_data.get("candidate_id"),
            "status": session_data.get("status"),
            "risk_score": session_data.get("risk_score"),
            "assigned_node": session_data.get("assigned_node"),
            "start_time": session_data.get("start_time"),
            "end_time": session_data.get("end_time"),
            "created_at": session_data.get("created_at"),
            "updated_at": session_data.get("updated_at"),
            "video_analysis": session_data.get("video_analysis"),
            "audio_analysis": session_data.get("audio_analysis"),
            "evaluation_analysis": session_data.get("evaluation_analysis"),
        }

        if format == "pdf":
            return _build_risk_report_pdf(report)

        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating risk report for {session_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Error generating risk report")


def _build_risk_report_pdf(report: dict) -> Response:
    """Render a one-page PDF risk report using reportlab."""
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "Interview Risk Report")

    c.setFont("Helvetica", 11)
    y = 760
    fields = [
        ("Session ID", report.get("session_id")),
        ("Candidate ID", report.get("candidate_id")),
        ("Status", report.get("status")),
        ("Risk Score", report.get("risk_score")),
        ("Start Time", report.get("start_time")),
        ("End Time", report.get("end_time")),
        ("Created At", report.get("created_at")),
        ("Updated At", report.get("updated_at")),
    ]
    for label, value in fields:
        c.drawString(50, y, f"{label}: {value}")
        y -= 22

    c.save()
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=risk_report_{report['session_id']}.pdf"},
    )



@app.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    session_db: Session = Depends(get_db),
):
    """
    Get the status of a Celery task by its ID.

    Args:
        task_id: Celery task identifier (returned by the scheduler).

    Returns:
        TaskStatusResponse: Current task status and result if available.
    """
    try:
        from workers.celery_app import celery_app

        result = celery_app.AsyncResult(task_id)
        status = result.status
        payload = {
            "session_id": result.result.get("session_id") if isinstance(result.result, dict) else None,
            "task_id": task_id,
            "status": status,
            "result": result.result if status == "SUCCESS" else None,
        }
        return TaskStatusResponse(**payload)
    except Exception as e:
        logger.error(f"Error fetching task status for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching task status: {e}")


# ========== Session Tracking Endpoints ==========


@app.get("/active-sessions")
@http_cache.cached("active-sessions", ttl=2)
async def get_active_sessions(
    session_db: Session = Depends(get_db),
):
    """
    Get all currently active sessions

    Returns sessions in states: CREATED, QUEUED, PROCESSING

    Returns:
        dict: List of active sessions with brief details
    """
    try:
        active = session_tracker.get_active_sessions()
        return {"count": len(active), "sessions": active}
    except Exception as e:
        logger.error(f"Error fetching active sessions: {e!s}")
        raise HTTPException(status_code=500, detail="Error fetching active sessions")


@app.get("/completed-sessions")
@http_cache.cached("completed-sessions", ttl=3)
async def get_completed_sessions(limit: int = 100):
    """
    Get recently completed sessions

    Args:
        limit: Maximum number of sessions to retrieve (default: 100)

    Returns:
        dict: List of completed sessions with results
    """
    try:
        completed = session_tracker.get_completed_sessions(limit=limit)
        return {"count": len(completed), "sessions": completed}
    except Exception as e:
        logger.error(f"Error fetching completed sessions: {e!s}")
        raise HTTPException(status_code=500, detail="Error fetching completed sessions")


@app.get("/stuck-sessions")
async def get_stuck_sessions(
    timeout_minutes: int = 30,
    session_db: Session = Depends(get_db),
):
    """
    Get sessions that appear to be stuck in PROCESSING

    Args:
        timeout_minutes: Timeout threshold in minutes (default: 30)

    Returns:
        dict: List of stuck sessions
    """
    try:
        stuck = session_tracker.get_stuck_sessions(timeout_minutes=timeout_minutes)
        return {
            "count": len(stuck),
            "timeout_minutes": timeout_minutes,
            "sessions": stuck,
        }
    except Exception as e:
        logger.error(f"Error fetching stuck sessions: {e!s}")
        raise HTTPException(status_code=500, detail="Error fetching stuck sessions")


# ========== Statistics Endpoints ==========


@app.get("/session-statistics")
@http_cache.cached("session-statistics", ttl=2)
async def get_session_statistics(
    session_db: Session = Depends(get_db),
):
    """
    Get comprehensive session statistics

    Returns statistics including:
    - Total sessions by status
    - Average processing duration
    - Risk score distribution
    - High-risk session count

    Returns:
        dict: Session statistics
    """
    try:
        return session_tracker.get_session_statistics()
    except Exception as e:
        logger.error(f"Error generating statistics: {e!s}")
        raise HTTPException(status_code=500, detail="Error generating statistics")


@app.get("/worker-distribution")
async def get_worker_distribution(
    session_db: Session = Depends(get_db),
):
    """
    Get distribution of sessions across worker nodes

    Returns:
        dict: Worker node -> session count mapping
    """
    try:
        distribution = session_tracker.get_worker_distribution()
        return {"workers": distribution, "total_active": sum(distribution.values())}
    except Exception as e:
        logger.error(f"Error fetching worker distribution: {e!s}")
        raise HTTPException(status_code=500, detail="Error fetching worker distribution")


@app.get("/high-risk-sessions")
async def get_high_risk_sessions(
    threshold: float = 0.8,
    limit: int = 50,
    session_db: Session = Depends(get_db),
):
    """
    Get high-risk completed sessions

    Args:
        threshold: Risk score threshold (0-1, default: 0.8)
        limit: Maximum sessions to return (default: 50)

    Returns:
        dict: List of high-risk sessions
    """
    try:
        high_risk = session_tracker.get_high_risk_sessions(threshold=threshold, limit=limit)
        return {"count": len(high_risk), "threshold": threshold, "sessions": high_risk}
    except Exception as e:
        logger.error(f"Error fetching high-risk sessions: {e!s}")
        raise HTTPException(status_code=500, detail="Error fetching high-risk sessions")


# ========== Cache Management Endpoints ==========


@app.get("/cache-stats")
async def get_cache_stats():
    """
    Get Redis cache statistics

    Returns:
        dict: Cache health and statistics
    """
    try:
        return state_sync.get_cache_stats()
    except Exception as e:
        logger.error(f"Error fetching cache stats: {e!s}")
        raise HTTPException(status_code=500, detail="Error fetching cache stats")


@app.post("/sync-to-database", dependencies=[Depends(require_token)])
async def sync_cache_to_database(session_id: str | None = None):
    """
    Manually sync cache to database

    Args:
        session_id: Specific session to sync, or None to sync all active sessions

    Returns:
        dict: Sync result
    """
    try:
        if session_id:
            session_data = state_sync.get_session_state(session_id)
            if session_data:
                state_sync.sync_state_to_db(session_id, session_data)
                return {"message": f"Synced session {session_id}", "status": "success"}
            raise HTTPException(status_code=404, detail="Session not found in cache")
        # Sync all active sessions
        active_sessions = state_sync.get_active_sessions()
        for sid in active_sessions:
            session_data = state_sync.get_session_state(sid)
            if session_data:
                state_sync.sync_state_to_db(sid, session_data)

        return {
            "message": f"Synced {len(active_sessions)} sessions",
            "status": "success",
            "synced_count": len(active_sessions),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing to database: {e!s}")
        raise HTTPException(status_code=500, detail="Error syncing to database")


@app.delete("/clear-cache", dependencies=[Depends(require_token)])
async def clear_session_cache():
    """
    Clear all session cache from Redis

    WARNING: This will clear all cached session states

    Returns:
        dict: Clear operation result
    """
    try:
        logger.warning("Clearing all session cache from Redis")
        result = state_sync.clear_cache()
        return {"message": "Cache cleared", "status": "success" if result else "failed"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e!s}")
        raise HTTPException(status_code=500, detail="Error clearing cache")


@app.get("/interviews")
async def list_interviews(
    limit: int = 100,
    status: str | None = None,
    session_db: Session = Depends(get_db),
):
    """
    List interview sessions, newest first.
    """

    stmt = select(InterviewSession)

    if status:
        stmt = stmt.where(InterviewSession.status == status.upper())

    stmt = stmt.order_by(InterviewSession.created_at.desc().nullslast()).limit(limit)
    rows = session_db.execute(stmt).scalars().all()
    return {
        "total_count": len(rows),
        "sessions": [
            {
                "session_id": r.session_id,
                "candidate_id": r.candidate_id,
                "status": r.status,
                "risk_score": r.risk_score,
                "assigned_node": r.assigned_node,
                "start_time": r.start_time.isoformat() if r.start_time else None,
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
    }


# ========== Question Endpoints ==========


@app.get("/questions")
async def list_questions(
    category: str | None = None,
    difficulty: str | None = None,
    limit: int = 100,
    session_db: Session = Depends(get_db),
):
    """List questions with optional category/difficulty filter"""
    try:
        questions = question_bank.get_questions(
            category=category,
            difficulty=difficulty,
            limit=limit,
        )
        return {"count": len(questions), "questions": questions}
    except Exception as e:
        logger.error(f"Error listing questions: {e}")
        raise HTTPException(status_code=500, detail="Error listing questions")


@app.post("/questions")
async def add_question(
    request: AddQuestionRequest,
    session_db: Session = Depends(get_db),
):
    """Add a new question to the bank"""
    try:
        question = question_bank.add_question(
            text=request.text,
            category=request.category,
            difficulty=request.difficulty,
            tags=request.tags,
        )
        return question
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding question: {e!s}")
        raise HTTPException(status_code=500, detail="Error adding question")


# ========== Candidate Endpoints ==========


@app.get("/candidates")
async def list_candidates(
    limit: int = 100,
    session_db: Session = Depends(get_db),
):
    """List all candidates"""
    try:
        candidates = candidate_manager.list_candidates(limit=limit)
        return {"count": len(candidates), "candidates": candidates}
    except Exception as e:
        logger.error(f"Error listing candidates: {e!s}")
        raise HTTPException(status_code=500, detail="Error listing candidates")


@app.post("/candidates")
async def create_candidate(
    request: CreateCandidateRequest,
    session_db: Session = Depends(get_db),
):
    """Create a new candidate profile"""
    try:
        candidate = candidate_manager.create_candidate(
            name=request.name,
            email=request.email,
            resume_text=request.resume_text,
            skills=request.skills,
        )
        return candidate
    except Exception as e:
        logger.error(f"Error creating candidate: {e!s}")
        raise HTTPException(status_code=500, detail="Error creating candidate")


@app.get("/candidates/{candidate_id}")
async def get_candidate(
    candidate_id: str,
    session_db: Session = Depends(get_db),
):
    """Get candidate details by ID"""
    try:
        candidate = candidate_manager.get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return candidate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching candidate: {e!s}")
        raise HTTPException(status_code=500, detail="Error fetching candidate")


@app.get("/candidates/{candidate_id}/history")
async def get_candidate_history(
    candidate_id: str,
    session_db: Session = Depends(get_db),
):
    """Get candidate interview history"""
    try:
        candidate = candidate_manager.get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        history = candidate_manager.get_interview_history(candidate_id)
        return {"candidate_id": candidate_id, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching candidate history: {e!s}")
        raise HTTPException(status_code=500, detail="Error fetching candidate history")


# ========== Template Endpoints ==========


@app.get("/templates")
async def list_templates(interview_type: str | None = None, limit: int = 100):
    """List interview templates with optional type filter"""
    try:
        templates = interview_template_manager.list_templates(interview_type=interview_type, limit=limit)
        return {"count": len(templates), "templates": templates}
    except Exception as e:
        logger.error(f"Error listing templates: {e!s}")
        raise HTTPException(status_code=500, detail="Error listing templates")


@app.post("/templates")
async def create_template(
    request: CreateTemplateRequest,
    session_db: Session = Depends(get_db),
):
    """Create a new interview template"""
    try:
        template = interview_template_manager.create_template(
            name=request.name,
            interview_type=request.interview_type,
            description=request.description,
            duration_minutes=request.duration_minutes,
            question_count=request.question_count,
            category_distribution=request.category_distribution,
            difficulty_distribution=request.difficulty_distribution,
        )
        return template
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating template: {e!s}")
        raise HTTPException(status_code=500, detail="Error creating template")


# ========== Interview Q&A Endpoints ==========


@app.post("/interviews/ask-question")
async def ask_question(
    request: AskQuestionRequest,
    session_db: Session = Depends(get_db),
):
    """Get next question for a session"""
    try:
        session_data = session_manager.get_session(request.session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        asked_ids = session_data.get("questions_asked", [])
        question = question_bank.get_next_question(
            category=request.category,
            exclude_ids=[q.get("question_id") for q in asked_ids] if asked_ids else [],
        )
        if not question:
            raise HTTPException(status_code=404, detail="No more questions available")

        return AskQuestionResponse(
            session_id=request.session_id,
            question_id=question["question_id"],
            text=question["text"],
            category=question["category"],
            difficulty=question["difficulty"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting question: {e!s}")
        raise HTTPException(status_code=500, detail="Error getting question")


@app.post("/interviews/submit-answer")
async def submit_answer(
    request: SubmitAnswerRequest,
    session_db: Session = Depends(get_db),
):
    """Submit an answer and get feedback"""
    try:
        session_data = session_manager.get_session(request.session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        question = question_bank.get_question(request.question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        question_bank.record_usage(request.question_id, score=request.score)

        feedback = f"Answer recorded for: {question['text'][:80]}..."
        if request.score is not None:
            if request.score >= 7:
                feedback = f"Strong answer ({request.score}/10). Good demonstration of knowledge."
            elif request.score >= 5:
                feedback = f"Acceptable answer ({request.score}/10). Some areas for improvement."
            else:
                feedback = f"Needs improvement ({request.score}/10). Consider reviewing core concepts."

        questions_asked = session_data.get("questions_asked", [])
        questions_asked.append(
            {
                "question_id": request.question_id,
                "text": question["text"],
                "category": question["category"],
            }
        )

        answers = session_data.get("answers_provided", [])
        answers.append(
            {
                "question_id": request.question_id,
                "answer_text": request.answer_text,
                "score": request.score,
            }
        )

        feedbacks = session_data.get("feedback_generated", [])
        feedbacks.append(
            {
                "question_id": request.question_id,
                "feedback": feedback,
                "score": request.score,
            }
        )

        scores = [a.get("score") for a in answers if a.get("score") is not None]
        overall_score = sum(scores) / len(scores) if scores else None

        session_data["questions_asked"] = questions_asked
        session_data["answers_provided"] = answers
        session_data["feedback_generated"] = feedbacks
        session_data["overall_score"] = overall_score
        session_manager.state_sync.set_session_state(request.session_id, session_data)

        return SubmitAnswerResponse(
            session_id=request.session_id,
            question_id=request.question_id,
            feedback=feedback,
            score=request.score,
            questions_asked=len(questions_asked),
            overall_score=overall_score,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer: {e!s}")
        raise HTTPException(status_code=500, detail="Error submitting answer")


# ========== Worker Management Endpoints ==========


@app.post("/register-worker", dependencies=[Depends(require_token)])
async def register_worker(request: WorkerRegistrationRequest):
    """
    Register a new worker node

    Args:
        request: Worker registration details (worker_id, capacity)

    Returns:
        dict: Registration confirmation
    """
    try:
        logger.info(f"Registering worker: {request.worker_id} with capacity {request.capacity}")

        # Register worker in registry
        worker_registry.register_worker(worker_id=request.worker_id, capacity=request.capacity)

        # Log successful registration
        logger.info(f"Worker registered successfully: {request.worker_id}")
        WORKERS_REGISTERED.inc()
        WORKERS_HEALTHY.inc()

        return {
            "status": "success",
            "message": f"Worker {request.worker_id} registered",
            "worker_id": request.worker_id,
            "capacity": request.capacity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error registering worker: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error registering worker: {e!s}")


@app.post("/worker/heartbeat", dependencies=[Depends(require_token)])
async def worker_heartbeat(request: WorkerHeartbeatRequest):
    """
    Process heartbeat from worker node

    Workers send periodic heartbeats to indicate they are alive
    and to report current active task count

    Args:
        request: Heartbeat data (worker_id, active_tasks)

    Returns:
        dict: Heartbeat confirmation
    """
    try:
        logger.debug(f"Heartbeat from worker: {request.worker_id} (active_tasks: {request.active_tasks})")

        # Update worker heartbeat in registry
        worker_registry.heartbeat(worker_id=request.worker_id, active_tasks=request.active_tasks)
        WORKER_HEARTBEAT_AGE_SECONDS.labels(worker_id=request.worker_id).set(0)

        WORKER_ACTIVE_TASKS.labels(worker_id=request.worker_id).set(request.active_tasks)

        worker_status = worker_registry.get_worker(request.worker_id)
        if worker_status:
          WORKER_CAPACITY.labels(worker_id=request.worker_id).set(worker_status.get("capacity", 0))


        # Invalidate the workers + load caches so the next dashboard poll is fresh.
        http_cache.invalidate("workers", "worker-statistics", "load-status")

        # Get worker health status
        worker_status = worker_registry.get_worker(request.worker_id)
        health_status = (
            "healthy" if worker_status and worker_status.get("health_status") == "healthy" else "unknown"
        )

        return {
            "status": "success",
            "message": "Heartbeat received",
            "worker_id": request.worker_id,
            "health": health_status,
            "active_tasks": request.active_tasks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error processing heartbeat: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error processing heartbeat: {e!s}")


@app.get("/workers")
@http_cache.cached("workers", ttl=2)
async def list_workers():
    """
    Get list of all registered workers with status

    Returns:
        dict: Worker nodes with status information
    """
    try:
        logger.debug("Fetching worker list")

        # Get all workers from registry
        all_workers = worker_registry.get_all_workers()

        # Detect unhealthy workers (no heartbeat for timeout period)
        unhealthy = worker_registry.detect_unhealthy_workers()

        # Build worker list with status
        workers_list = []
        for worker_id, worker_data in all_workers.items():
            is_healthy = worker_id not in unhealthy
            workers_list.append(
                {
                    "worker_id": worker_id,
                    "capacity": worker_data.get("capacity", 0),
                    "active_tasks": worker_data.get("active_tasks", 0),
                    "available_capacity": worker_data.get("capacity", 0) - worker_data.get("active_tasks", 0),
                    "health_status": "healthy" if is_healthy else "unhealthy",
                    "last_heartbeat": worker_data.get("last_heartbeat", None),
                    "joined_at": worker_data.get("joined_at", None),
                }
            )

        return {
            "total_workers": len(all_workers),
            "healthy_workers": len(all_workers) - len(unhealthy),
            "unhealthy_workers": len(unhealthy),
            "workers": workers_list,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching worker list: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching worker list: {e!s}")


@app.get("/worker-statistics")
@http_cache.cached("worker-statistics", ttl=2)
async def get_worker_stats():
    """
    Get detailed worker statistics and utilization metrics

    Returns:
        dict: Worker utilization and performance metrics
    """
    try:
        logger.debug("Generating worker statistics")

        # Get worker statistics
        stats = worker_registry.get_worker_statistics()

        # Calculate aggregate metrics
        total_capacity = stats.get("total_capacity", 0)
        total_active = stats.get("total_active_tasks", 0)
        utilization = (total_active / total_capacity * 100) if total_capacity > 0 else 0

        return {
            "total_workers": stats.get("total_workers", 0),
            "total_capacity": total_capacity,
            "total_active_tasks": total_active,
            "system_utilization_percent": round(utilization, 2),
            "average_utilization_per_worker": stats.get("average_active_tasks", 0),
            "min_worker_load": stats.get("min_active_tasks", 0),
            "max_worker_load": stats.get("max_active_tasks", 0),
            "idle_workers": stats.get("idle_workers", 0),
            "worker_details": stats.get("workers", []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating worker statistics: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error generating worker statistics: {e!s}")


@app.get("/load-status")
async def get_load_status():
    """
    Get current system load and capacity status

    Provides visualization of:
    - Overall system utilization
    - Queue depth
    - Worker availability
    - Load balancer strategy recommendations

    Returns:
        dict: System load information
    """
    try:
        logger.debug("Fetching system load status")

        # Get load status from load balancer
        load_status = load_balancer.get_load_status()

        return {
            "current_strategy": load_status.get("current_strategy", "unknown"),
            "system_utilization_percent": load_status.get("system_utilization", 0),
            "available_workers": load_status.get("total_workers", 0),
            "busy_workers": load_status.get("busy_workers", 0),
            "idle_workers": load_status.get("idle_workers", 0),
            "system_at_capacity": load_status.get("system_at_capacity", False),
            "system_overloaded": load_status.get("system_overloaded", False),
            "recommended_strategy": load_status.get("recommended_strategy", "LEAST_LOADED"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching load status: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching load status: {e!s}")


@app.get("/scheduling-status")
async def get_scheduling_status():
    """
    Get scheduler status and health information

    Returns:
        dict: Scheduler operational status and metrics
    """
    try:
        logger.debug("Fetching scheduler status")

        # Get scheduling status
        status_info = scheduler.get_scheduling_status()

        return {
            "scheduler_active": True,
            "current_strategy": load_balancer.strategy.name,
            "system_overloaded": status_info.get("system_overloaded", False),
            "available_workers": status_info.get("available_workers", 0),
            "can_accept_tasks": scheduler.can_accept_task(),
            "recommendation": status_info.get("recommendation"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching scheduling status: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching scheduling status: {e!s}")


@app.post("/switch-strategy", dependencies=[Depends(require_token)])
async def switch_load_balancing_strategy(strategy: str):
    """
    Change the active load balancing strategy

    Supported strategies:
    - ROUND_ROBIN: Sequential worker assignment (even task distribution)
    - LEAST_LOADED: Assign to worker with fewest active tasks (recommended)
    - QUEUE_BASED: Use Redis queue length as selection metric

    Args:
        strategy: Strategy name (ROUND_ROBIN, LEAST_LOADED, QUEUE_BASED)

    Returns:
        dict: Strategy change confirmation
    """
    try:
        logger.info(f"Switching load balancing strategy to: {strategy}")

        # Validate strategy
        valid_strategies = {
            "ROUND_ROBIN": BalancingStrategy.ROUND_ROBIN,
            "LEAST_LOADED": BalancingStrategy.LEAST_LOADED,
            "QUEUE_BASED": BalancingStrategy.QUEUE_BASED,
        }

        if strategy.upper() not in valid_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy. Valid options: {', '.join(valid_strategies.keys())}",
            )

        # Switch strategy
        new_strategy = valid_strategies[strategy.upper()]
        load_balancer.switch_strategy(new_strategy)

        logger.info(f"Load balancing strategy switched to: {strategy}")

        return {
            "status": "success",
            "message": f"Strategy switched to {strategy}",
            "previous_strategy": load_balancer.strategy.name,
            "new_strategy": strategy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching strategy: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error switching strategy: {e!s}")


@app.delete("/deregister-worker/{worker_id}", dependencies=[Depends(require_token)])
async def deregister_worker(worker_id: str):
    """
    Deregister a worker node (remove from active pool)

    Use this when a worker is permanently removed from the system

    Args:
        worker_id: ID of worker to deregister

    Returns:
        dict: Deregistration confirmation
    """
    try:
        logger.info(f"Deregistering worker: {worker_id}")

        # Deregister worker
        worker_registry.deregister_worker(worker_id)

        logger.info(f"Worker deregistered successfully: {worker_id}")

        return {
            "status": "success",
            "message": f"Worker {worker_id} deregistered",
            "worker_id": worker_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error deregistering worker: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error deregistering worker: {e!s}")


# ========== Fault Tolerance & Recovery Endpoints ==========


@app.get("/failed-sessions")
@http_cache.cached("failed-sessions", ttl=3)
async def get_failed_sessions(limit: int = 100):
    """
    Get sessions that failed during processing

    Args:
        limit: Maximum number of failed sessions to return

    Returns:
        dict: List of failed sessions with details
    """
    try:
        logger.debug("Fetching failed sessions")

        # Get from session tracker
        failed = session_tracker.get_failed_sessions(limit=limit)

        return {
            "count": len(failed),
            "failed_sessions": failed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching failed sessions: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching failed sessions: {e!s}")


@app.post("/retry-session/{session_id}", dependencies=[Depends(require_token)])
async def retry_failed_session(session_id: str):
    """
    Retry a failed interview session

    Attempts to reschedule the session if it hasn't exceeded max retries.

    Args:
        session_id: ID of session to retry

    Returns:
        dict: Retry scheduling result
    """
    try:
        logger.info(f"Retry request for session: {session_id}")

        # Check if can retry
        if not retry_manager.can_retry(session_id):
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_id} has exceeded maximum retry attempts",
            )

        # Get retry info
        retry_info = retry_manager.get_retry_info(session_id)

        # Schedule retry with exponential backoff
        # Schedule retry
        retry_scheduled = retry_manager.schedule_retry(session_id)

        if not retry_scheduled:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to schedule retry for session {session_id}",
            )

        # -----------------------------
        # Actually requeue the interview
        # -----------------------------
        from orchestrator.scheduler import TaskPriority

        scheduler.schedule_task(
            session_id=session_id,
            priority=TaskPriority.MEDIUM
        )

        logger.info(
            "Session %s requeued successfully after retry scheduling.",
            session_id,
        )

        return {
            "status": "success",
            "message": f"Session {session_id} scheduled and requeued",
            "session_id": session_id,
            "retry_info": retry_manager.get_retry_info(session_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying session: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error retrying session: {e!s}")


@app.get("/system-health")
async def get_system_health():
    """
    Get comprehensive system health status

    Performs health checks on:
    - Redis connectivity
    - Worker nodes
    - Active sessions
    - Queue backlog

    Returns:
        dict: System health status and metrics
    """
    try:
        logger.debug("Performing system health check")

        # Perform comprehensive health check
        return health_monitor.check_system_health(
            worker_registry=worker_registry, session_manager=session_manager
        )

    except Exception as e:
        logger.error(f"Error checking system health: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error checking system health: {e!s}")


@app.get("/worker-health")
async def get_worker_health():
    """
    Get detailed health status of all workers

    Returns:
        dict: Worker health information
    """
    try:
        logger.debug("Fetching worker health status")

        # Check worker health
        return health_monitor.check_worker_health(worker_registry)

    except Exception as e:
        logger.error(f"Error fetching worker health: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching worker health: {e!s}")


@app.get("/recovery-queue")
async def get_recovery_queue(limit: int = 50):
    """
    Get sessions queued for recovery/retry

    Args:
        limit: Maximum number to return

    Returns:
        dict: Recovery queue entries
    """
    try:
        logger.debug("Fetching recovery queue")

        recovery_queue = fault_manager.get_recovery_queue(limit=limit)

        return {
            "count": len(recovery_queue),
            "recovery_queue": recovery_queue,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching recovery queue: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching recovery queue: {e!s}")


@app.get("/failure-log")
async def get_failure_log(limit: int = 100):
    """
    Get system failure log entries

    Args:
        limit: Maximum number of entries to return

    Returns:
        dict: Failure log entries
    """
    try:
        logger.debug("Fetching failure log")

        failures = fault_manager.get_failure_log(limit=limit)

        return {
            "count": len(failures),
            "failures": failures,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching failure log: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching failure log: {e!s}")


@app.get("/dead-letter-queue")
async def get_dead_letter_queue(limit: int = 50):
    """
    Get permanently failed sessions in dead letter queue

    Args:
        limit: Maximum number to return

    Returns:
        dict: Dead letter queue entries
    """
    try:
        logger.debug("Fetching dead letter queue")

        dlq = fault_manager.get_dead_letter_queue(limit=limit)

        return {
            "count": len(dlq),
            "dead_letter_queue": dlq,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching dead letter queue: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching dead letter queue: {e!s}")


@app.get("/fault-statistics")
async def get_fault_statistics():
    """
    Get aggregate fault and recovery statistics

    Returns:
        dict: System fault metrics and trends
    """
    try:
        logger.debug("Generating fault statistics")

        fault_stats = fault_manager.get_system_fault_stats()
        retry_stats = retry_manager.get_retry_statistics()

        return {
            "fault_statistics": fault_stats,
            "retry_statistics": retry_stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating fault statistics: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error generating fault statistics: {e!s}")


@app.post("/detect-failures", dependencies=[Depends(require_token)])
async def detect_and_handle_failures():
    """
    Manually trigger failure detection and recovery

    Scans for:
    - Failed sessions (stuck in PROCESSING)
    - Unhealthy workers
    - Stuck sessions

    Triggers recovery for detected failures.

    Returns:
        dict: Detection and recovery results
    """
    try:
        logger.info("Manual failure detection triggered")

        # Detect failed sessions
        failed_sessions = fault_manager.detect_failed_sessions()

        # Detect unhealthy workers
        unhealthy_workers = health_monitor.detect_worker_failures(worker_registry)

        # Detect stuck sessions
        stuck_sessions = health_monitor.detect_stuck_sessions(session_manager)

        # Handle worker failures
        handled = 0
        for worker_id in unhealthy_workers:
            if fault_manager.handle_worker_failure(worker_id, "Detected as unhealthy"):
                handled += 1

        results = {
            "status": "success",
            "failed_sessions_detected": len(failed_sessions),
            "failed_sessions": failed_sessions,
            "unhealthy_workers_detected": len(unhealthy_workers),
            "unhealthy_workers": unhealthy_workers,
            "workers_handled": handled,
            "stuck_sessions_detected": len(stuck_sessions),
            "stuck_sessions": stuck_sessions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Failure detection complete: {len(failed_sessions)} failed, "
            f"{len(unhealthy_workers)} unhealthy workers, {len(stuck_sessions)} stuck"
        )

        # Drop every cache so dashboards reflect the recovery pass.
        http_cache.invalidate()

        return results

    except Exception as e:
        logger.error(f"Error during failure detection: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error during failure detection: {e!s}")


# ========== Moment Tracking Endpoints ==========


@app.post("/moments/track")
async def track_moment(session_id: str, moment_type: str, metadata: dict | None = None):
    """Track a real-time moment during an interview session."""
    from orchestrator.moment_tracker import moment_tracker

    try:
        moment = moment_tracker.track_moment(session_id, moment_type, metadata)
        http_cache.invalidate(f"moments:{session_id}")
        return {"status": "success", "moment": moment}
    except Exception as e:
        logger.error(f"Error tracking moment: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error tracking moment: {e!s}")


@app.get("/moments/{session_id}")
async def get_session_moments(session_id: str, moment_type: str | None = None, limit: int = 100):
    """Get all tracked moments for a session."""
    from orchestrator.moment_tracker import moment_tracker

    try:
        moments = moment_tracker.get_session_moments(session_id, moment_type, limit)
        return {"session_id": session_id, "count": len(moments), "moments": moments}
    except Exception as e:
        logger.error(f"Error fetching moments: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching moments: {e!s}")


@app.get("/moments/{session_id}/timeline")
async def get_session_timeline(session_id: str):
    """Get the moment timeline for a session."""
    from orchestrator.moment_tracker import moment_tracker

    try:
        timeline = moment_tracker.get_timeline(session_id)
        return {"session_id": session_id, "count": len(timeline), "timeline": timeline}
    except Exception as e:
        logger.error(f"Error fetching timeline: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching timeline: {e!s}")


@app.get("/moments/{session_id}/summary")
async def get_session_moment_summary(session_id: str):
    """Get a summary of moments for a session."""
    from orchestrator.moment_tracker import moment_tracker

    try:
        summary = moment_tracker.get_session_summary(session_id)
        return summary
    except Exception as e:
        logger.error(f"Error fetching moment summary: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching moment summary: {e!s}")


@app.get("/moments/analytics")
async def get_moment_analytics(time_range_hours: int = 24):
    """Get moment analytics across all sessions."""
    from orchestrator.moment_tracker import moment_tracker

    try:
        analytics = moment_tracker.get_analytics(time_range_hours)
        return analytics
    except Exception as e:
        logger.error(f"Error fetching moment analytics: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error fetching moment analytics: {e!s}")


# ========== Dashboard HTML Endpoint ==========


@app.get("/dashboard")
async def get_dashboard():
    """
    Serve the monitoring dashboard HTML

    Returns:
        HTML content of the dashboard
    """
    try:
        import os

        dashboard_path = os.path.join(os.path.dirname(__file__), "..", "monitoring", "dashboard.html")

        if os.path.exists(dashboard_path):
            with open(dashboard_path, encoding="utf-8") as f:
                html_content = f.read()

            from fastapi.responses import HTMLResponse

            return HTMLResponse(content=html_content)
        raise HTTPException(status_code=404, detail="Dashboard HTML not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving dashboard: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error serving dashboard: {e!s}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
