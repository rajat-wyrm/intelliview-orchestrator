"""Anti-cheat integrity signal ingestion routes."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/integrity", tags=["integrity"])


# In-memory storage of integrity events grouped by session_id.
# This keeps the endpoint independent of the existing database models.
integrity_events: dict[str, list[dict[str, Any]]] = {}


class IntegrityEvent(BaseModel):
    session_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/events")
async def ingest_integrity_event(event: IntegrityEvent):
    """Receive and store an anti-cheat integrity event for a session."""

    stored_event = {
        "session_id": event.session_id,
        "event_type": event.event_type,
        "timestamp": (
            event.timestamp.isoformat()
            if event.timestamp
            else datetime.now(timezone.utc).isoformat()
        ),
        "metadata": event.metadata,
    }

    integrity_events.setdefault(event.session_id, []).append(stored_event)

    return {
        "success": True,
        "message": "Integrity event stored",
        "session_id": event.session_id,
        "event": stored_event,
    }


@router.get("/events/{session_id}")
async def get_integrity_events(session_id: str):
    """Return all stored integrity events for a session."""

    return {
        "session_id": session_id,
        "events": integrity_events.get(session_id, []),
    }
