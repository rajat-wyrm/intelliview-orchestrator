from fastapi import FastAPI
from fastapi.responses import JSONResponse
from processing import run_video_analysis
from pydantic import BaseModel

app = FastAPI(
    title="CV Processing Service",
    description="Standalone OpenCV + MediaPipe microservice",
    version="1.0.0",
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
    # Reject empty or whitespace-only session_id
    if not request.session_id.strip():
        return JSONResponse(
            status_code=422,
            content={
                "session_id": request.session_id,
                "status": "error",
                "error_message": "session_id must not be empty",
            },
        )

    try:
        result = run_video_analysis(request.session_id)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "session_id": request.session_id,
                "status": "error",
                "error_message": f"Video analysis failed: {exc}",
            },
        )

    result["status"] = "ok"
    return result
