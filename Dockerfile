FROM python:3.11-slim-bookworm
# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# ---------------------------------------------------------
# Working directory
# ---------------------------------------------------------
WORKDIR /app

# ---------------------------------------------------------
# System dependencies
# ---------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# Create non-root user
# ---------------------------------------------------------
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system \
    --uid 1001 \
    --gid appgroup \
    --create-home \
    --home-dir /home/appuser \
    appuser

# ---------------------------------------------------------
# Copy dependency file first
# This improves Docker layer caching
# ---------------------------------------------------------
COPY requirements.txt /app/requirements.txt

# ---------------------------------------------------------
# Install PyTorch CPU version
# ---------------------------------------------------------
RUN pip install --no-cache-dir \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

# ---------------------------------------------------------
# Install Python dependencies
# ---------------------------------------------------------
RUN pip install --no-cache-dir -r /app/requirements.txt

# ---------------------------------------------------------
# Copy application
# ---------------------------------------------------------
COPY . /app

# ---------------------------------------------------------
# Create writable directories
# ---------------------------------------------------------
RUN mkdir -p \
    /app/data \
    /app/.cache \
    /app/logs \
    /app/tmp

# ---------------------------------------------------------
# Set ownership
# ---------------------------------------------------------
RUN chown -R appuser:appgroup /app

# ---------------------------------------------------------
# Run as non-root
# ---------------------------------------------------------
USER appuser

# ---------------------------------------------------------
# Port
# ---------------------------------------------------------
EXPOSE 8000

# ---------------------------------------------------------
# FastAPI healthcheck
# ---------------------------------------------------------
HEALTHCHECK --interval=30s \
    --timeout=10s \
    --start-period=40s \
    --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# ---------------------------------------------------------
# Default application
# docker-compose overrides this for worker/flower
# ---------------------------------------------------------
CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]