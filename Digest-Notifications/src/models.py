"""
Data models for the Digest Notifications module.

These are intentionally framework-agnostic (plain dataclasses) so this
module can be dropped into any backend (Flask/FastAPI/Django) used by
the larger Orchestrator project without forcing an ORM choice.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DigestFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class InterviewEvent:
    """
    A single upcoming interview to be summarised in a digest.
    This mirrors the kind of record the Notification Event Catalog
    (events_catalog.yaml) would emit for an 'interview.booked' /
    'interview.reminder' event.
    """

    interview_id: str
    candidate_name: str
    role_title: str
    interviewer_name: str
    scheduled_at: datetime
    meeting_link: str | None = None
    location: str | None = None

    @property
    def date_key(self) -> str:
        """Group key used to bucket interviews by calendar date."""
        return self.scheduled_at.strftime("%Y-%m-%d")

    @property
    def display_date(self) -> str:
        return self.scheduled_at.strftime("%A, %d %B %Y")

    @property
    def display_time(self) -> str:
        return self.scheduled_at.strftime("%I:%M %p")


@dataclass
class DigestRecipient:
    """Minimal recipient info needed to render and send a digest."""

    user_id: str
    email: str
    display_name: str
    timezone: str = "UTC"
    frequency: DigestFrequency = DigestFrequency.DAILY


@dataclass
class DigestPayload:
    """The fully assembled digest, ready for template rendering."""

    recipient: DigestRecipient
    generated_at: datetime
    grouped_interviews: "dict[str, list[InterviewEvent]]" = field(default_factory=dict)
    total_upcoming_count: int = 0

    @property
    def total_count(self) -> int:
        return sum(len(v) for v in self.grouped_interviews.values())
