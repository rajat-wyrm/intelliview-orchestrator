from fastapi import APIRouter, HTTPException

# Create a router for your new API
router = APIRouter(prefix="/new-api", tags=["new-api"])


@router.get("/status")
async def get_status():
    """
    Simple health check endpoint.
    """
    return {"status": "ok", "message": "New API is working!"}


@router.post("/process")
async def process_data(payload: dict):
    """
    Example POST endpoint that accepts JSON payload.
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Payload is required")
    # Add your business logic here
    return {"status": "success", "received": payload}
