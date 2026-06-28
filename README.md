# IntelliView Orchestrator

> **AI-powered interview orchestration platform with real-time monitoring, multi-provider AI evaluation, and fault-tolerant distributed processing.**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/UI-Next.js_14-000.svg)](https://nextjs.org)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](./.github/workflows/ci.yml)

---

## Quick Start

```bash
git clone https://github.com/rajat-wyrm/intelliview-orchestrator
cd intelliview-orchestrator
cp .env.example .env          # edit API_TOKEN, database credentials
docker compose up -d --build
```

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Dashboard UI |
| **API** | http://localhost:8000 | REST API (docs at `/docs`) |
| **Prometheus** | http://localhost:9090 | Metrics |
| **Grafana** | http://localhost:3001 | Dashboards (admin/admin) |

## Architecture

```
┌───────────────────┐     ┌──────────────────┐
│  Next.js Dashboard│────▶│  FastAPI Backend  │
│  (Port 3000)      │     │  (Port 8000)      │
└───────────────────┘     └────┬───────┬──────┘
                               │       │
                    ┌──────────▼─┐  ┌──▼──────────┐
                    │   Redis    │  │  PostgreSQL  │
                    │  (Cache)   │  │  (Truth)     │
                    └──────┬─────┘  └─────────────┘
                           │
              ┌────────────▼────────────┐
              │   Celery Worker Nodes   │
              │  video │ audio │ eval   │
              └─────────────────────────┘
```

## Features

### Real-time Interview Monitoring
- **Live video/audio feed** with browser-based camera access
- **Screen lock** with auto-lock after inactivity and PIN unlock
- **Moment tracking** — logs every key event during interviews
- **WebSocket push** for instant dashboard updates

### Multi-Provider AI Evaluation
- **Gemini** (Google) — primary evaluation and question generation
- **Grok** (xAI) — fallback for answer scoring
- **OpenAI** (GPT-4o) — additional fallback
- Automatic provider fallback with zero downtime

### Production Infrastructure
- **Prometheus + Grafana** dashboards out of the box
- **Circuit breaker** for Redis fault tolerance
- **Rate limiting** and request validation middleware
- **Structured audit logging** for compliance
- **Neon DB / cloud PostgreSQL** SSL support

### Dashboard Pages
- **Overview** — system health, worker status, live sparklines
- **Sessions** — active/completed/failed with pipeline visualization
- **Interview** — real-time video, audio viz, AI feedback, risk score
- **Candidates** — profiles, history, performance analytics
- **Workers** — load balancing, capacity, heartbeat monitoring
- **Analytics** — risk distribution, failure breakdown, trend charts
- **Settings** — token management, theme, strategy switching

## Configuration

All settings via environment variables (or `.env`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_URL` | `redis://localhost:6379/0` | Cache + Celery broker |
| `POSTGRES_HOST` | `localhost` | Database host |
| `DATABASE_SSLMODE` | `disable` | Set `require` for Neon DB |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GROK_API_KEY` | — | xAI Grok API key |
| `API_TOKEN` | `dev-token-change-me` | Auth token for mutations |
| `SCREEN_LOCK_PIN` | `1234` | Dashboard screen lock PIN |

## API Reference

Full OpenAPI docs at `/docs` when running. Key endpoints:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/start-interview` | Yes | Start a new interview session |
| `GET` | `/active-sessions` | No | List active sessions |
| `GET` | `/session-status/{id}` | No | Session details + risk score |
| `POST` | `/interviews/ask-question` | Yes | Get next interview question |
| `POST` | `/interviews/submit-answer` | Yes | Submit answer for evaluation |
| `GET` | `/candidates` | No | List candidate profiles |
| `GET` | `/system-health` | No | Full system health check |
| `GET` | `/metrics` | No | Prometheus metrics |

## Development

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn orchestrator.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Tests
pytest tests/ --ignore=tests/test_e2e_smoke.py -v

# Lint
ruff check . && ruff format --check .
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Celery, SQLAlchemy 2.0 |
| Frontend | Next.js 14, React 18, Tailwind CSS, Recharts |
| Database | PostgreSQL (Neon DB compatible) |
| Cache | Redis 7 |
| AI | Gemini, Grok, OpenAI (pluggable) |
| Monitoring | Prometheus, Grafana |
| Deploy | Docker Compose |

## License

MIT — [Rajat Kumar](https://github.com/rajat-wyrm)
