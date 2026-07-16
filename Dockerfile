# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user; bind to the standard 8000 port.
RUN groupadd --system --gid 1001 app \
    && useradd  --system --uid 1001 --gid app --create-home app

WORKDIR /app

# System deps. We drop postgresql-client (orchestrator uses SQLAlchemy via
# libpq in psycopg2-binary — the CLI is not needed at runtime).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY --chown=app:app . .

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1
# Create a secure, non-root system group and user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Give our new user ownership over the application files
RUN chown -R appuser:appgroup /app

# Tell Docker to switch from root to this new user for the rest of the execution
USER appuser
CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]
