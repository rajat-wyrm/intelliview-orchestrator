"""
digest_builder.py

Pure business logic for turning a flat list of upcoming InterviewEvent
objects into a DigestPayload grouped by date. No I/O, no email provider
calls here on purpose — this keeps it easily unit-testable and reusable
regardless of how emails are sent (SendGrid/SES/etc).
"""

from collections import OrderedDict
from collections.abc import Iterable
from datetime import datetime

from models import DigestPayload, DigestRecipient, InterviewEvent


def group_interviews_by_date(
    interviews: Iterable[InterviewEvent],
) -> "OrderedDict[str, list[InterviewEvent]]":
    """
    Groups interviews by calendar date (date_key) and returns them in
    chronological order, with each day's interviews also sorted by time.
    """
    buckets: dict[str, list[InterviewEvent]] = {}
    for event in interviews:
        buckets.setdefault(event.date_key, []).append(event)

    ordered = OrderedDict()
    for date_key in sorted(buckets.keys()):
        ordered[date_key] = sorted(buckets[date_key], key=lambda e: e.scheduled_at)
    return ordered


def build_digest(
    recipient: DigestRecipient,
    interviews: Iterable[InterviewEvent],
    now: datetime | None = None,
) -> DigestPayload:
    """
    Builds a DigestPayload for a single recipient from their list of
    upcoming interviews.

    Args:
        recipient: who this digest is for.
        interviews: all upcoming interviews relevant to this recipient
            (the caller / scheduler is responsible for filtering by
            recipient and by the digest's time window — e.g. next 24h
            for 'daily', next 7 days for 'weekly').
        now: injectable clock for deterministic testing.
    """
    generated_at = now or datetime.now()
    grouped = group_interviews_by_date(interviews)
    return DigestPayload(
        recipient=recipient,
        generated_at=generated_at,
        grouped_interviews=dict(grouped),
    )
