"""Anti-cheat integrity signal ingestion routes."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/integrity", tags=["integrity"])


# In-memory storage of integrity events grouped by session_id.
# This keeps the endpoint independent of the existing database models.
integrity_events: dict[str, list[dict[str, Any]]] = {}

# Event-type values that count as a browser tab switch for integrity scoring.
_TAB_SWITCH_EVENT_TYPES = {"tab_switch", "tab_switching", "tab-switch"}


def get_tab_switch_count(session_id: str) -> int:
    """Count stored tab-switch events for a session.

    Used by the session-status API to feed the live integrity-score fusion
    (see ``workers/integrity_score.py``) so the score reflects tab-switch
    signals as soon as they're ingested via ``POST /integrity/events``.
    """
    events = integrity_events.get(session_id, [])
    return sum(
        1
        for e in events
        if e.get("event_type", "").strip().lower() in _TAB_SWITCH_EVENT_TYPES
    )


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
