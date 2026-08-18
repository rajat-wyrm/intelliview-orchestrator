"""
renderer.py

Renders a DigestPayload into a final HTML string using Jinja2.

Designed to interoperate with the project's central Email Template
Engine module: if that module exposes a shared Jinja2 Environment
(e.g. with locale loaders for multi-language support), pass it in via
`env` instead of using the default one created here. This avoids two
competing template engines existing in the same project.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template
from models import DigestPayload

DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
DEFAULT_TEMPLATE_NAME = "digest_template.html"


def _default_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(DEFAULT_TEMPLATE_DIR)),
        autoescape=True,
    )


def render_digest_html(
    payload: DigestPayload,
    unsubscribe_url: str,
    env: Environment | None = None,
    template_name: str = DEFAULT_TEMPLATE_NAME,
) -> str:
    """
    Renders the given digest payload to an HTML string.

    Args:
        payload: the assembled digest (see digest_builder.build_digest).
        unsubscribe_url: fully-formed unsubscribe link for this recipient,
            typically produced by the Unsubscribe & Compliance module.
        env: optional shared Jinja2 Environment from the central template
            engine. If omitted, a local environment pointed at this
            module's own templates/ folder is used.
        template_name: override if the host project renames/relocates
            the template.
    """
    environment = env or _default_environment()
    template: Template = environment.get_template(template_name)

    grouped_for_template = {
        next(iter(events)).display_date: events
        for events in payload.grouped_interviews.values()
    }

    return template.render(
        greeting_name=payload.recipient.display_name,
        frequency=payload.recipient.frequency.value,
        total_count=payload.total_count,
        total_upcoming_count=payload.total_upcoming_count,
        generated_at=payload.generated_at.strftime("%d %b %Y, %H:%M UTC"),
        grouped_interviews=grouped_for_template,
        unsubscribe_url=unsubscribe_url,
    )


def render_digest_text(payload: DigestPayload, unsubscribe_url: str) -> str:
    """
    Renders a plain-text fallback version of the digest.

    Should be sent alongside the HTML body as the text/plain MIME part
    to improve email deliverability scores and support text-only clients.
    """
    freq = payload.recipient.frequency.value.capitalize()
    summary_line = f"  {payload.total_count} upcoming interview{'s' if payload.total_count != 1 else ''}"
    if payload.total_upcoming_count > payload.total_count:
        summary_line = f"  Showing {payload.total_count} of {payload.total_upcoming_count} upcoming interviews (batch size limit)"

    lines = [
        f"{'=' * 52}",
        f"  {freq} Interview Digest — Orchestrator",
        f"  Hello {payload.recipient.display_name},",
        summary_line,
        f"  Generated: {payload.generated_at.strftime('%d %b %Y, %H:%M UTC')}",
        f"{'=' * 52}",
        "",
    ]

    if payload.total_count == 0:
        lines.append("No upcoming interviews scheduled for this period.")
    else:
        for events in payload.grouped_interviews.values():
            if not events:
                continue
            date_label = events[0].display_date
            lines.append(f"--- {date_label} ---")
            for event in events:
                lines.append(f"  [{event.display_time}]  {event.candidate_name}")
                lines.append(f"     Role      : {event.role_title}")
                lines.append(f"     Interviewer: {event.interviewer_name}")
                if event.meeting_link:
                    lines.append(f"     Link       : {event.meeting_link}")
                elif event.location:
                    lines.append(f"     Location   : {event.location}")
                lines.append("")

    lines += [
        f"{'─' * 52}",
        "To manage preferences or unsubscribe, visit:",
        unsubscribe_url,
    ]
    return "\n".join(lines)
