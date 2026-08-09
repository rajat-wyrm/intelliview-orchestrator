"""
sender.py

Thin orchestration layer that ties build_digest() + render_digest_html()
to an actual email-sending call.

This module depends on an `EmailSenderProtocol` — it does NOT
import SendGrid/SES directly. The calling service should provide
an adapter implementing this protocol, keeping this module provider-agnostic
and easy to test with a fake.
"""

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from digest_builder import build_digest
from models import DigestRecipient, InterviewEvent
from renderer import render_digest_html


class EmailSenderProtocol(Protocol):
    """
    Minimal contract the email service provider adapter should satisfy.
    Matches output shape: {"status": "sent", "provider": "...", ...}
    """

    def send_html_email(self, to_email: str, subject: str, html_body: str) -> dict: ...


def build_unsubscribe_url(base_url: str, user_id: str) -> str:
    """
    Builds the unsubscribe URL for a given recipient.
    Expects the host project's Unsubscribe & Compliance module to
    expose an endpoint like GET/POST {base_url}/unsubscribe?user_id=...
    """
    return f"{base_url.rstrip('/')}/unsubscribe?user_id={user_id}"


def send_digest_for_recipient(
    recipient: DigestRecipient,
    interviews: Iterable[InterviewEvent],
    email_sender: EmailSenderProtocol,
    unsubscribe_base_url: str,
    now: datetime | None = None,
) -> dict:
    """
    Builds and sends a single digest email for one recipient.

    Returns the dict produced by the email_sender (status/provider/etc),
    annotated with digest-specific metadata for logging/analytics
    (which the Delivery Analytics module can consume downstream).
    """
    payload = build_digest(recipient, interviews, now=now)

    if payload.total_count == 0:
        # No upcoming interviews -> skip sending, nothing to digest.
        return {
            "status": "skipped",
            "reason": "no_upcoming_interviews",
            "user_id": recipient.user_id,
        }

    unsubscribe_url = build_unsubscribe_url(unsubscribe_base_url, recipient.user_id)
    html_body = render_digest_html(payload, unsubscribe_url=unsubscribe_url)

    subject = f"Your {recipient.frequency.value.capitalize()} Interview Digest ({payload.total_count} upcoming)"

    result = email_sender.send_html_email(
        to_email=recipient.email,
        subject=subject,
        html_body=html_body,
    )

    result.update(
        {
            "digest_type": recipient.frequency.value,
            "interview_count": payload.total_count,
            "user_id": recipient.user_id,
        }
    )
    return result


def send_digests_batch(
    recipients: list[DigestRecipient],
    interviews_by_user: dict,
    email_sender: EmailSenderProtocol,
    unsubscribe_base_url: str,
    now: datetime | None = None,
) -> list[dict]:
    """
    Sends digests for many recipients in one pass (e.g. invoked by a
    daily/weekly cron job or scheduler task in the main project).

    Args:
        interviews_by_user: maps user_id -> list[InterviewEvent], already
            pre-filtered by the caller to each recipient's relevant window.
    """
    results = []
    for recipient in recipients:
        interviews = interviews_by_user.get(recipient.user_id, [])
        result = send_digest_for_recipient(
            recipient=recipient,
            interviews=interviews,
            email_sender=email_sender,
            unsubscribe_base_url=unsubscribe_base_url,
            now=now,
        )
        results.append(result)
    return results
