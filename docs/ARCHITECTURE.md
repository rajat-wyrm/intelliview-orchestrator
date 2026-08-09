# Architecture — IntelliView Orchestrator

## 1. System Overview

IntelliView Orchestrator is a distributed AI interview processing platform built around a FastAPI API, PostgreSQL persistence, Redis-backed state and task coordination, Celery workers, and a Next.js frontend.

The repository separates the application into the following major areas:

- `orchestrator/` — core interview orchestration, session management, worker management, security, fault handling, scheduling, caching, and state synchronization.
- `routers/` — FastAPI API route modules for candidates, sessions, questions, templates, workers, administration, health, and metrics.
- `workers/` — Celery-based background processing for interview evaluation, AI processing, video/audio processing, risk analysis, and worker execution.
- `database/` — SQLAlchemy database configuration and models plus the database schema and persistence helpers.
- `frontend/` — Next.js web application and reusable UI components.
- `monitoring/` — Prometheus metrics, monitoring APIs, dashboard, WebSocket management, and monitoring configuration.
- `cv_service/` — separate service for CV/resume processing.
- `Digest-Notifications/` — notification digest service.
- `retrieval/` — document retrieval and embedding/indexing functionality.
- `tests/` — unit, integration, contract, regression, and end-to-end test coverage.

---

## 2. Runtime Architecture

```mermaid
flowchart TD
    USER[User / HR / Candidate]

    subgraph FRONTEND["Frontend"]
        FE[Next.js Frontend<br/>Port 3000]
    end

    subgraph API["Application API"]
        FASTAPI[FastAPI<br/>Port 8000]
        ROUTERS[FastAPI Routers]
        ORCH[Orchestrator]
    end

    subgraph DATA["Data & Coordination"]
        PG[(PostgreSQL 15<br/>Port 5432)]
        REDIS[(Redis 7<br/>Port 6379)]
    end

    subgraph WORKERS["Background Processing"]
        CELERY[Celery Workers]
        VIDEO[Video Pipeline]
        AUDIO[Audio Pipeline]
        EVAL[Evaluation Pipeline]
        RISK[Risk Scoring Engine]
    end

    subgraph SERVICES["Supporting Services"]
        CV[CV Service<br/>Port 8001]
        DIGEST[Digest Notifications<br/>Port 8080]
    end

    subgraph OBS["Observability"]
        PROM[Prometheus<br/>Port 9090]
        GRAFANA[Grafana<br/>Port 3001]
        FLOWER[Flower<br/>Port 5555]
        JAEGER[Jaeger<br/>Port 16686]
    end

    USER --> FE
    FE -->|HTTP / REST| FASTAPI
    FE -->|WebSocket| FASTAPI

    FASTAPI --> ROUTERS
    ROUTERS --> ORCH

    ORCH --> PG
    ORCH --> REDIS
    ORCH --> CELERY

    CELERY --> VIDEO
    CELERY --> AUDIO
    CELERY --> EVAL
    CELERY --> RISK

    CELERY --> CV
    FASTAPI --> DIGEST

    ORCH --> PROM
    CELERY --> PROM
    REDIS --> FLOWER
    PROM --> GRAFANA
    FASTAPI --> JAEGER
