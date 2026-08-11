import json
from pathlib import Path

OPENAPI_FILE = Path("openapi.json")

with OPENAPI_FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)


def get_tag(path, operation):
    text = (path + " " + operation.get("summary", "")).lower()

    # Health
    if (
        "health" in text
        or "livez" in path.lower()
        or "readiness" in text
        or "liveness" in text
    ):
        return "Health"

    # Metrics / monitoring
    if (
        "/monitoring/" in path.lower()
        or "metric" in text
        or "dashboard" in text
    ):
        return "Metrics"

    # Workers
    if (
        "worker" in path.lower()
        or "worker" in text
    ):
        return "Workers"

    # Candidates
    if (
        "candidate" in path.lower()
        or "candidate" in text
    ):
        return "Candidates"

    # Interviews
    if (
        "interview" in path.lower()
        or "interview" in text
    ):
        return "Interviews"

    # Questions
    if (
        "question" in path.lower()
        or "question" in text
    ):
        return "Questions"

    # Notifications
    if (
        "notification" in path.lower()
        or "notification" in text
    ):
        return "Notifications"

    # Configuration
    if (
        "config" in path.lower()
        or "configuration" in text
    ):
        return "Configurations"

    # Retrieval
    if (
        "retrieval" in path.lower()
        or "retrieval" in text
    ):
        return "Retrieval"

    # Scheduler
    if (
        "schedul" in path.lower()
        or "schedul" in text
    ):
        return "Scheduler"

    # Authentication
    if (
        "auth" in path.lower()
        or "login" in path.lower()
        or "token" in path.lower()
        or "authentication" in text
    ):
        return "Authentication"

    # Default
    return "Other"


# Create/update top-level OpenAPI tags
tag_names = [
    "Health",
    "Metrics",
    "Workers",
    "Candidates",
    "Interviews",
    "Questions",
    "Notifications",
    "Configurations",
    "Retrieval",
    "Scheduler",
    "Authentication",
    "Other",
]

data["tags"] = [
    {
        "name": tag,
        "description": f"{tag} related APIs"
    }
    for tag in tag_names
]


# Add tags to every operation
changed = 0

for path, path_item in data.get("paths", {}).items():

    if not isinstance(path_item, dict):
        continue

    for method, operation in path_item.items():

        if method.lower() not in {
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "options",
            "head",
        }:
            continue

        if not isinstance(operation, dict):
            continue

        tag = get_tag(path, operation)

        operation["tags"] = [tag]

        changed += 1

        print(f"{method.upper():6} {path:60} -> {tag}")


# Save updated OpenAPI file
with OPENAPI_FILE.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print()
print("=" * 70)
print(f"Updated {changed} API operations.")
print("openapi.json has been updated successfully.")
print("=" * 70)