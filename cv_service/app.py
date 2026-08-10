from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from processing import run_video_analysis
from pydantic import BaseModel
import io
from pypdf import PdfReader

app = FastAPI(
    title="CV Processing Service",
    description="Standalone OpenCV + MediaPipe microservice",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your frontend's real origin before deploying
    allow_methods=["*"],
    allow_headers=["*"],
)


class VideoRequest(BaseModel):
    session_id: str


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "cv-processing",
    }


@app.post("/analyze-video")
async def analyze_video(request: VideoRequest):
    """
    Run OpenCV + MediaPipe video analysis.
    """
    return run_video_analysis(request.session_id)


ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Placeholder keyword list — swap for real NLP/regex extraction if a teammate owns that.
SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "react", "sql",
    "aws", "docker", "kubernetes", "fastapi", "django", "flask",
    "machine learning", "git", "c++", "go", "postgresql",
]


def extract_skills(text: str) -> list[str]:
    lower = text.lower()
    return sorted({kw for kw in SKILL_KEYWORDS if kw in lower})


@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    try:
        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read PDF")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable text found")

    return {
        "filename": file.filename,
        "resume_text": text[:10000],
        "skills": extract_skills(text),
    }