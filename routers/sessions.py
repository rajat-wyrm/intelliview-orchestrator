"""Interview session lifecycle, fault-tolerance/retry, and Q&A routes."""

import io
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Candidate, InterviewSession
from metrics.prometheus_metrics import SESSIONS_ACTIVE, SESSIONS_CREATED
from orchestrator import http_cache
from orchestrator.scheduler import TaskPriority
from workers.adaptive_difficulty import get_next_difficulty
from orchestrator.security import get_current_user, require_role

logger = logging.getLogger(__name__)


class StartInterviewRequest(BaseModel):
    """Request model for starting an interview"""

    candidate_id: str = Field(
        min_length=1, max_length=128, description="Unique candidate identifier"
    )
    candidate_name: str | None = Field(default=None, max_length=200)
    position: str | None = Field(default=None, max_length=120)
    language: str = Field(
    default="en",
    max_length=10,
    description="Interview language code",
    )
    priority: str = Field(default="medium", description="One of: low, medium, high")

    @field_validator("candidate_id")
    @classmethod
    def _candidate_id_format(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[A-Za-z0-9._-]+$", v):
            raise ValueError(
                "candidate_id may only contain letters, digits, '.', '_', '-'"
            )
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


class InterviewSessionResponse(BaseModel):
    """Response model for interview session"""

    session_id: str
    status: str
    created_at: str | None = None
    candidate_id: str
    language: str = "en"
    risk_score: float | None = None
    estimated_wait_time: int | None = None


class SessionStatusResponse(BaseModel):
    """Response model for session status"""

    session_id: str
    status: str
    candidate_id: str
    language: str = "en"
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


class CoachingQuestionFeedback(BaseModel):
    question_id: str
    question: str
    answer: str | None = None
    score: float | None = None
    feedback: str | None = None


class CoachingResponse(BaseModel):
    session_id: str
    candidate_id: str
    overall_score: float | None = None
    strengths: list[str] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    question_feedback: list[CoachingQuestionFeedback] = Field(default_factory=list)
    recommendation: str | None = None
    detailed_feedback: str | None = None


class TaskStatusResponse(BaseModel):
    """Response model for Celery task status (used by /task-status/{task_id})."""

    session_id: str
    task_id: str
    status: str
    result: dict | None = None


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
        headers={
            "Content-Disposition": f"attachment; filename=risk_report_{report['session_id']}.pdf"
        },
    )


def create_session_routes(
    session_manager,
    session_tracker,
    scheduler,
    fault_manager,
    retry_manager,
    health_monitor,
    worker_registry,
    question_bank,
) -> APIRouter:
    """Create interview session lifecycle, fault-tolerance/retry, and Q&A routes.

    Args:
        session_manager: SessionManager instance
        session_tracker: SessionTracker instance
        scheduler: Scheduler instance
        fault_manager: FaultManager instance
        retry_manager: RetryManager instance
        health_monitor: HealthMonitor instance
        worker_registry: WorkerRegistry instance
        question_bank: QuestionBank instance

    Returns:
        APIRouter with session routes
    """

    router = APIRouter()

    # ========== Interview Session Endpoints ==========

    @router.post(
        "/start-interview",
        response_model=InterviewSessionResponse,
        dependencies=[Depends(get_current_user)],
    )
    async def start_interview(
        request: StartInterviewRequest,
        session_db: Session = Depends(get_db),
    ):
        """
        Start a new interview session using intelligent scheduling
        """
        if not re.match(r"^[A-Za-z0-9._-]+$", request.candidate_id):
            raise HTTPException(status_code=422, detail="Invalid candidate_id")

        try:

            logger.info(
                f"API: Creating interview session for candidate {request.candidate_id}"
            )

            priority_map = {
                "low": TaskPriority.LOW,
                "medium": TaskPriority.MEDIUM,
                "high": TaskPriority.HIGH,
            }
            priority = priority_map.get(request.priority.lower(), TaskPriority.MEDIUM)

            session_id = session_manager.create_session(
                candidate_id=request.candidate_id,
                candidate_name=request.candidate_name,
                position=request.position,
                language=request.language,
            )

            # Increment total interview sessions created
            SESSIONS_CREATED.inc()
            # Increase active interview session count
            SESSIONS_ACTIVE.inc()

            logger.info(f"Session created: {session_id}")

            session_manager.update_session_status(
                session_id, session_manager.QUEUED, {"priority": priority.name}
            )

            if not scheduler.can_accept_task():
                logger.warning(f"System at capacity, queuing task: {session_id}")

            scheduler.schedule_task(session_id, priority=priority)

            wait_time = scheduler.get_estimated_wait_time(priority)

            # Invalidate the read caches so the next poll reflects the new
            # session immediately instead of waiting for the TTL.
            http_cache.invalidate(
                "active-sessions", "session-statistics", "workers", "worker-statistics"
            )

            session_data = session_manager.get_session(session_id)

            return InterviewSessionResponse(
                session_id=session_id,
                status=session_manager.QUEUED,
                created_at=session_data.get("created_at"),
                candidate_id=request.candidate_id,
                language=request.language,
                risk_score=None,
                estimated_wait_time=wait_time if wait_time >= 0 else None,
            )

        except Exception as e:
            logger.error(f"Error starting interview session: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Error starting interview: {e!s}"
            )

    @router.get("/session-status/{session_id}", response_model=SessionStatusResponse)
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
                language=session_data.get("language", "en"),
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
            raise HTTPException(
                status_code=500, detail=f"Error fetching session: {e!s}"
            )

    @router.get(
        "/interviews/{session_id}/report", response_model=InterviewReportResponse
    )
    async def get_interview_report(
        session_id: str,
        db: Session = Depends(get_db),
    ):
        """
        Get comprehensive final interview report.
        """
        try:
            session_obj = db.execute(
                select(InterviewSession).where(
                    InterviewSession.session_id == session_id
                )
            ).scalar_one_or_none()

            if not session_obj:
                raise HTTPException(status_code=404, detail="Session not found")

            candidate_obj = db.execute(
                select(Candidate).where(
                    Candidate.candidate_id == session_obj.candidate_id
                )
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
                        feedback=q_data.get("feedback"),
                    )
                )

            eval_analysis = session_obj.evaluation_analysis or {}
            llm_feedback = eval_analysis.get("llm_feedback", {})

            # Since evaluation_analysis structure might differ based on other PRs,
            # we will handle nested or flat structures for strengths/improvements.
            strengths = eval_analysis.get(
                "strengths", llm_feedback.get("strengths", [])
            )
            improvements = eval_analysis.get(
                "improvements", llm_feedback.get("improvements", [])
            )
            recommendation = eval_analysis.get(
                "recommendation", llm_feedback.get("recommendation")
            )
            detailed_feedback = eval_analysis.get(
                "detailed_feedback", llm_feedback.get("detailed_feedback")
            )

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
                    email=candidate_obj.email,
                ),
                interview_summary=ReportInterviewSummary(
                    start_time=(
                        session_obj.start_time.isoformat()
                        if session_obj.start_time
                        else None
                    ),
                    end_time=(
                        session_obj.end_time.isoformat()
                        if session_obj.end_time
                        else None
                    ),
                    duration_minutes=duration_minutes,
                ),
                questions=questions_list,
                overall_evaluation=ReportEvaluation(
                    quality=eval_analysis.get("quality"),
                    accuracy=eval_analysis.get("accuracy"),
                    clarity=eval_analysis.get("clarity"),
                ),
                llm_feedback=ReportLLMFeedback(
                    strengths=strengths,
                    improvements=improvements,
                    recommendation=recommendation,
                    detailed_feedback=detailed_feedback,
                ),
                risk_assessment=ReportRiskAssessment(
                    score=risk_score,
                    classification=classification,
                    factors=eval_analysis.get("risk_factors", []),
                ),
                metadata=ReportMetadata(
                    token_usage=None,  # Feature #3 not yet merged
                    estimated_cost_usd=None,
                ),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching interview report: {e!s}")
            raise HTTPException(status_code=500, detail=f"Error fetching report: {e!s}")

    @router.get(
        "/interviews/{session_id}/coaching",
        response_model=CoachingResponse,
    )
    async def get_interview_coaching(
        session_id: str,
        db: Session = Depends(get_db),
    ):
        """Get structured coaching feedback for an interview session."""
        try:
            session_obj = db.execute(
                select(InterviewSession).where(
                    InterviewSession.session_id == session_id
                )
            ).scalar_one_or_none()

            if not session_obj:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found",
                )

            # Get questions, answers, and generated feedback.
            q_asked = session_obj.questions_asked or []
            a_provided = session_obj.answers_provided or []
            f_generated = session_obj.feedback_generated or []

            # Build question lookup by question_id.
            q_dict = {q.get("question_id"): q for q in q_asked if q.get("question_id")}

            # Attach answers to their questions.
            for answer in a_provided:
                q_id = answer.get("question_id")
                if q_id in q_dict:
                    q_dict[q_id]["answer"] = answer.get("answer_text")

            # Attach feedback and score to their questions.
            for feedback in f_generated:
                q_id = feedback.get("question_id")
                if q_id in q_dict:
                    q_dict[q_id]["feedback"] = feedback.get("feedback")
                    q_dict[q_id]["score"] = feedback.get("score")

            # Convert mapped questions into coaching question feedback.
            question_feedback = [
                CoachingQuestionFeedback(
                    question_id=q_id,
                    question=q_data.get("text", ""),
                    answer=q_data.get("answer"),
                    score=q_data.get("score"),
                    feedback=q_data.get("feedback"),
                )
                for q_id, q_data in q_dict.items()
            ]

            # Get overall evaluation feedback.
            eval_analysis = session_obj.evaluation_analysis or {}
            llm_feedback = eval_analysis.get("llm_feedback", {})

            strengths = eval_analysis.get(
                "strengths",
                llm_feedback.get("strengths", []),
            )

            improvements = eval_analysis.get(
                "improvements",
                llm_feedback.get("improvements", []),
            )

            recommendation = eval_analysis.get(
                "recommendation",
                llm_feedback.get("recommendation"),
            )

            detailed_feedback = eval_analysis.get(
                "detailed_feedback",
                llm_feedback.get("detailed_feedback"),
            )

            return CoachingResponse(
                session_id=session_obj.session_id,
                candidate_id=session_obj.candidate_id,
                overall_score=session_obj.overall_score,
                strengths=strengths,
                focus_areas=improvements,
                action_items=[],
                question_feedback=question_feedback,
                recommendation=recommendation,
                detailed_feedback=detailed_feedback,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Error fetching interview coaching: %s",
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Error fetching interview coaching",
            )

    @router.get("/session-status/{session_id}/risk-report")
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

    @router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
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
                "session_id": (
                    result.result.get("session_id")
                    if isinstance(result.result, dict)
                    else None
                ),
                "task_id": task_id,
                "status": status,
                "result": result.result if status == "SUCCESS" else None,
            }
            return TaskStatusResponse(**payload)
        except Exception as e:
            logger.error(f"Error fetching task status for {task_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching task status: {e}"
            )

    # ========== Session Tracking Endpoints ==========

    @router.get("/active-sessions")
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
            raise HTTPException(
                status_code=500, detail="Error fetching active sessions"
            )

    @router.get("/completed-sessions")
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
            raise HTTPException(
                status_code=500, detail="Error fetching completed sessions"
            )

    @router.get("/stuck-sessions")
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

    @router.get("/session-statistics")
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

    @router.get("/high-risk-sessions")
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
            high_risk = session_tracker.get_high_risk_sessions(
                threshold=threshold, limit=limit
            )
            return {
                "count": len(high_risk),
                "threshold": threshold,
                "sessions": high_risk,
            }
        except Exception as e:
            logger.error(f"Error fetching high-risk sessions: {e!s}")
            raise HTTPException(
                status_code=500, detail="Error fetching high-risk sessions"
            )

    @router.get("/interviews")
    async def list_interviews(
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        session_db: Session = Depends(get_db),
    ):
        """
        List interview sessions, newest first.
        """

        stmt = select(InterviewSession)

        if status:
            stmt = stmt.where(InterviewSession.status == status.upper())

        stmt = (
            stmt.order_by(InterviewSession.created_at.desc().nullslast())
            .offset(offset)
            .limit(limit)
        )
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

    # ========== Interview Q&A Endpoints ==========

    @router.post("/interviews/ask-question")
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
                difficulty=session_data.get("next_difficulty"),
                exclude_ids=(
                    [q.get("question_id") for q in asked_ids] if asked_ids else []
                ),
            )
            if not question and session_data.get("next_difficulty"):
                question = question_bank.get_next_question(
                    category=request.category,
                    exclude_ids=(
                        [q.get("question_id") for q in asked_ids] if asked_ids else []
                    ),
                )
                  
            if not question:
                raise HTTPException(
                    status_code=404, detail="No more questions available"
                )

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

    @router.post("/interviews/submit-answer")
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

            next_difficulty = None
            if request.score is not None:
                next_difficulty = get_next_difficulty(request.score)

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
                    "score": score,
                }
            )
            feedbacks = session_data.get("feedback_generated", [])
            feedbacks.append(
                {
                    "question_id": request.question_id,
                    "score": score,
                    "reasoning": ai_result["reasoning"],
                    "strengths": ai_result["strengths"],
                    "gaps": ai_result["gaps"],
                }
            )

            scores = [a.get("score") for a in answers if a.get("score") is not None]
            overall_score = sum(scores) / len(scores) if scores else None

            session_data["questions_asked"] = questions_asked
            session_data["answers_provided"] = answers
            session_data["feedback_generated"] = feedbacks
            session_data["overall_score"] = overall_score
            session_data["next_difficulty"] = next_difficulty
            session_manager.state_sync.set_session_state(
                request.session_id, session_data
            )

            return SubmitAnswerResponse(
                session_id=request.session_id,
                question_id=request.question_id,
                feedback=feedback,
                score=score,
                questions_asked=len(questions_asked),
                overall_score=overall_score,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error submitting answer: {e!s}")
            raise HTTPException(status_code=500, detail="Error submitting answer")

    # ========== Fault Tolerance & Recovery Endpoints ==========

    @router.get("/failed-sessions")
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

            failed = session_tracker.get_failed_sessions(limit=limit)

            return {
                "count": len(failed),
                "failed_sessions": failed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error fetching failed sessions: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching failed sessions: {e!s}"
            )

    @router.post(
        "/retry-session/{session_id}", dependencies=[Depends(require_role("admin"))]
    )
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

            if not retry_manager.can_retry(session_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Session {session_id} has exceeded maximum retry attempts",
                )

            # Get retry info
            retry_manager.get_retry_info(session_id)

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
            scheduler.schedule_task(session_id=session_id, priority=TaskPriority.MEDIUM)

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
            raise HTTPException(
                status_code=500, detail=f"Error retrying session: {e!s}"
            )

    @router.get("/recovery-queue")
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
            raise HTTPException(
                status_code=500, detail=f"Error fetching recovery queue: {e!s}"
            )

    @router.get("/failure-log")
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
            raise HTTPException(
                status_code=500, detail=f"Error fetching failure log: {e!s}"
            )

    @router.get("/dead-letter-queue")
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
            raise HTTPException(
                status_code=500, detail=f"Error fetching dead letter queue: {e!s}"
            )

    @router.get("/fault-statistics")
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
            raise HTTPException(
                status_code=500, detail=f"Error generating fault statistics: {e!s}"
            )

    @router.post("/detect-failures", dependencies=[Depends(require_role("admin"))])
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

            failed_sessions = fault_manager.detect_failed_sessions()

            unhealthy_workers = health_monitor.detect_worker_failures(worker_registry)

            stuck_sessions = health_monitor.detect_stuck_sessions(session_manager)

            handled = 0
            for worker_id in unhealthy_workers:
                if fault_manager.handle_worker_failure(
                    worker_id, "Detected as unhealthy"
                ):
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
            raise HTTPException(
                status_code=500, detail=f"Error during failure detection: {e!s}"
            )

    return router
