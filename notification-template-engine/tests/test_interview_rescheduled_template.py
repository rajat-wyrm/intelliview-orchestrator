import re

from notification_template_engine.template_loader import (
    load_template,
    validate_template,
)


def test_interview_rescheduled_template_loads_and_renders():
    template = load_template("en", "interview_rescheduled", format="html")

    assert "{{name}}" in template
    assert "{{date}}" in template
    assert "{{time}}" in template

    assert validate_template(template) is True

    rendered = (
        template.replace("{{name}}", "Test Candidate")
        .replace("{{date}}", "2026-08-21")
        .replace("{{time}}", "10:00 AM")
    )

    assert not re.search(
        r"\{\{.*?\}\}", rendered
    ), "Template still contains unfilled placeholders"
