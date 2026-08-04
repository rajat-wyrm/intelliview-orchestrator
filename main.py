from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional
import logging

from app.schemas import (
    EvaluationRequest,
    EvaluationResponse,
    PaginatedLogsResponse,
    SummaryStatsResponse,
)
from app.evaluator import evaluate_answer
from app.database import init_db, get_logs, get_log_by_id, get_summary_stats

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Response Quality Dashboard API",
    description="Automated system to evaluate technical candidate answers with a built-in quality monitoring dashboard.",
    version="2.0.0",
)

# CORS — allow dashboard requests from anywhere during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the dashboard frontend
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Initialize DB on startup
@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized.")


# =============================================================================
#  Original Endpoints
# =============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirects root URL to the dashboard."""
    return RedirectResponse(url="/dashboard")

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """Simple health check endpoint to verify the service is running."""
    return {"status": "healthy"}

@app.post("/evaluate", response_model=EvaluationResponse, status_code=status.HTTP_200_OK, tags=["Evaluation"])
async def evaluate(payload: EvaluationRequest):
    """
    Evaluates candidate answers to technical questions.
    
    Checks for relevance, completeness, and correctness using a rule-based pre-filter
    and falls back/augments via OpenAI/Gemini LLM API calls.
    Results are automatically logged for dashboard analytics.
    """
    try:
        result = evaluate_answer(
            question=payload.question,
            answer=payload.answer,
            domain=payload.domain
        )
        return EvaluationResponse(**result)
    except Exception as e:
        logger.error(f"Internal server error during evaluation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )


# =============================================================================
#  Dashboard Endpoints
# =============================================================================

@app.get("/dashboard", include_in_schema=False)
async def serve_dashboard():
    """Serve the dashboard single-page application."""
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/api/stats", response_model=SummaryStatsResponse, tags=["Dashboard"])
async def api_stats():
    """Get aggregate evaluation statistics for dashboard KPI cards and charts."""
    return get_summary_stats()

@app.get("/api/logs", response_model=PaginatedLogsResponse, tags=["Dashboard"])
async def api_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    domain: Optional[str] = Query(None, description="Filter by domain (dsa, dbms, os)"),
    min_score: Optional[float] = Query(None, ge=0.0, le=10.0, description="Minimum score"),
    max_score: Optional[float] = Query(None, ge=0.0, le=10.0, description="Maximum score"),
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601)"),
    search: Optional[str] = Query(None, description="Free-text search in question, answer, and feedback"),
    evaluation_method: Optional[str] = Query(None, description="Filter by method (llm, rule_based)"),
    sort_by: str = Query("timestamp", description="Sort column"),
    sort_order: str = Query("desc", description="Sort direction (asc, desc)"),
):
    """Get paginated evaluation logs with optional filters."""
    return get_logs(
        page=page,
        page_size=page_size,
        domain=domain,
        min_score=min_score,
        max_score=max_score,
        start_date=start_date,
        end_date=end_date,
        search=search,
        evaluation_method=evaluation_method,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@app.get("/api/logs/{log_id}", tags=["Dashboard"])
async def api_log_detail(log_id: int):
    """Get a single evaluation log by ID."""
    log = get_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Evaluation log not found.")
    return log
