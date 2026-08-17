import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from processing import run_video_analysis
from pydantic import BaseModel

from orchestrator.resume_parser import parse_resume as parse_resume_file

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


# Resume parsing configuration
ALLOWED_CONTENT_TYPES = {"application/pdf"}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    """
    Upload a PDF resume and parse it using the shared resume parser.


    Extracts:

    The resume parser extracts:

    - Resume text
    - Technical skills
    - Education
    - Years of experience
    """

    # Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted",
        )

    # Read uploaded file
    raw = await file.read()

    # Validate file size
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large (max 5MB)",
        )

    if not raw:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    temp_path = None

    try:

        # The shared parser expects a file path,
        # so temporarily save the uploaded PDF.

        # Save uploaded PDF temporarily because the shared parser
        # expects a file path.

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temp_file:
            temp_file.write(raw)
            temp_path = temp_file.name

        # Use the shared resume parsing logic.
        parsed_resume = parse_resume_file(temp_path)

        # Return the parsed information to the frontend

        return {
            "filename": file.filename,
            **parsed_resume,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not parse PDF",
        )

    finally:

        # Always remove the temporary PDF.
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
