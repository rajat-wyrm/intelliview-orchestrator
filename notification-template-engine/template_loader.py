import logging
import os
import re

import pytest


def test_path_traversal_event_is_rejected():
    with pytest.raises(ValueError, match="Unsupported event"):
        load_template("en", "../../secret")


def test_unknown_event_is_rejected():
    with pytest.raises(ValueError, match="Unsupported event"):
        load_template("en", "random_event")


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
SUPPORTED_EVENTS = {
    "interview_scheduled",
    "interview_reminder",
    "interview_cancelled",
    "interview_completed",
    "interview_rescheduled",
}

# Supported placeholders
VALID_PLACEHOLDERS = {"{{name}}", "{{date}}", "{{time}}"}


def validate_template_variables(template, variables):
    """
    Validate that all variables referenced in the template are provided in the variables dictionary.
    Raises ValueError if any required variable is missing or None.
    """
    if variables is None:
        variables = {}

    placeholders = re.findall(r"\{\{(.*?)\}\}", template)
    missing = []
    for placeholder in placeholders:
        key = placeholder.strip()
        if key not in variables or variables[key] is None:
            if key not in missing:
                missing.append(key)

    if missing:
        missing_str = ", ".join(f"'{m}'" for m in missing)
        raise ValueError(f"Missing required template variable(s): {missing_str}")

    return True


def validate_template(template, variables=None):
    """
    Validate template content.
    """

    # Empty template
    if not template.strip():
        raise ValueError("Template is empty.")

    # Find placeholders
    placeholders = set(re.findall(r"\{\{.*?\}\}", template))

    # Invalid placeholder detection
    invalid = placeholders - VALID_PLACEHOLDERS

    if invalid:
        raise ValueError(f"Invalid placeholders found: {invalid}")

    if variables is not None:
        validate_template_variables(template, variables)

    return True


def load_template(locale, event, format="txt"):
    """
    Loads a notification template in text or HTML format.
    Falls back to English if the locale template does not exist.
    """

    supported_formats = {"txt", "html"}

    if not isinstance(event, str) or not event.strip():
        raise ValueError("Invalid event name.")

    event = event.strip()

    if event not in SUPPORTED_EVENTS:
        raise ValueError(f"Unsupported event: {event}")

    if format not in supported_formats:
        raise ValueError(
            f"Unsupported template format '{format}'. Supported formats: {sorted(supported_formats)}"
        )

    if format == "html":
        file_path = os.path.join("templates", locale, "html", f"{event}.html")
    else:
        file_path = os.path.join("templates", locale, f"{event}.txt")

    if not os.path.exists(file_path):
        logging.warning(
            f"Template for locale '{locale}' not found. Falling back to English."
        )

        if format == "html":
            file_path = os.path.join("templates", "en", "html", f"{event}.html")
        else:
            file_path = os.path.join("templates", "en", f"{event}.txt")

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Template not found for event '{event}' with format '{format}'."
        )

    try:
        with open(file_path, encoding="utf-8") as file:
            template = file.read()

    except OSError as e:
        logging.error(f"Unable to read template: {e}")
        raise

    validate_template(template)

    logging.info(f"Loaded template: {file_path}")

    return template
