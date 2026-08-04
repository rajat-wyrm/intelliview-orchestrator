from pydantic import BaseModel, Field
from typing import Optional, List

class EvaluationRequest(BaseModel):
    question: str = Field(..., description="The technical question asked to the candidate.")
    answer: str = Field(..., description="The candidate's response to be evaluated.")
    domain: Optional[str] = Field(
        None, 
        description="The technical domain of the question (e.g., 'dsa', 'dbms', 'os'). If omitted, it will be auto-detected."
    )

class EvaluationResponse(BaseModel):
    score: float = Field(..., ge=0.0, le=10.0, description="The evaluation score out of 10.")
    feedback: str = Field(..., description="Constructive feedback explaining the score and any missing or incorrect points.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="The confidence level of the evaluation score.")

# --- Dashboard Models ---

class EvaluationLogItem(BaseModel):
    id: int
    timestamp: str
    question: str
    answer: str
    domain: str
    score: float
    feedback: str
    confidence: float
    evaluation_method: str
    llm_provider: Optional[str] = None

class PaginatedLogsResponse(BaseModel):
    logs: List[EvaluationLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class MethodBreakdown(BaseModel):
    llm: int = 0
    rule_based: int = 0

class TrendPoint(BaseModel):
    date: str
    avg_score: float
    count: int

class SummaryStatsResponse(BaseModel):
    total_evaluations: int
    avg_score: float
    avg_confidence: float
    method_breakdown: dict
    domain_breakdown: dict
    score_distribution: List[int]
    recent_trend: List[TrendPoint]
