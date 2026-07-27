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

<!-- <<<<<<< HEAD -->

## Authentication

The application uses API Token authentication to protect privileged API endpoints.

### API Token

Configure the API token in the `.env` file:

```env
API_TOKEN=your-api-token
```

### Protected Endpoints

Protected endpoints require the `X-API-Token` request header.

Example:

```http
X-API-Token: api123
```

### Authentication Responses

- **200 OK** – Valid API token.
- **401 Unauthorized** – Missing or invalid API token.

Authentication is enforced through the `require_token` dependency for protected API endpoints.


## License

MIT — [Rajat Kumar](https://github.com/rajat-wyrm)
<!-- =======
# Delivery Analytics API

A FastAPI-based webhook analytics service that receives email delivery events, stores them in SQLite using SQLAlchemy, and exposes analytics through a REST API.

---

## Features

- Receive email webhook events
- Store events in SQLite database
- Delivery analytics endpoint
- Duplicate event detection
- Event normalization (case-insensitive)
- Automated regression tests using Pytest
- FastAPI interactive Swagger documentation

---

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Pytest
- Uvicorn

---

## Project Structure

```
Delivery_Analytics/
│
├── app.py
├── crud.py
├── database.py
├── models.py
├── schemas.py
├── generate_data.py
├── requirements.txt
├── README.md
├── delivery.db
└── tests/
    └── test_app.py
```

---

## Installation

Clone the repository

```bash
git clone https://github.com/nandithasri2006/Delivery_Analytics.git
```

Go into the project

```bash
cd Delivery_Analytics
```

Create virtual environment

```bash
python -m venv venv
```

Activate

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
uvicorn app:app --reload
```

Open Swagger UI

```
http://127.0.0.1:8000/docs
```

---

## API Endpoints

### GET /

Returns welcome message.

---

### POST /webhook

Stores an email webhook event.

Example

```json
{
  "event_id": "evt101",
  "email": "user@example.com",
  "event": "Delivered",
  "timestamp": "2026-07-10T10:00:00"
}
```

Response

```json
{
  "message": "Webhook stored successfully"
}
```

---

### GET /analytics

Returns analytics including

- Sent
- Delivered
- Opened
- Clicked
- Bounced
- Delivery Rate
- Open Rate
- Click Rate
- Bounce Rate

Example

```json
{
  "email_sent": 200,
  "delivered": 196,
  "delivery_rate": "98.0%",
  "opened": 150,
  "open_rate": "76.53%",
  "clicked": 90,
  "click_rate": "60.0%",
  "bounced": 4,
  "bounce_rate": "2.0%"
}
```

---

# Reliability Improvements

## Event Normalization

Webhook events are normalized to lowercase before storage.

Example

Incoming

```json
{
    "event":"Delivered"
}
```

Stored

```
delivered
```

This ensures analytics remain accurate regardless of input casing.

---

## Case-insensitive Analytics

Analytics queries perform case-insensitive comparisons to avoid silent undercounting caused by inconsistent event casing.

---

## Duplicate Event Protection

Duplicate webhook deliveries are detected using the unique `event_id`.

Duplicate requests return

```
400 Bad Request
```

with

```json
{
    "detail":"Duplicate Event"
}
```

---

## Database Session Management

Database sessions are managed using FastAPI dependency injection (`Depends(get_db)`), ensuring sessions are always closed even if an exception occurs during request handling.

---

## Testing

Run tests

```bash
python -m pytest
```

Regression test included

- Mixed-case event ("Delivered") is counted correctly.
- Duplicate event detection.
- Invalid event rejection.

---

## Current Database

SQLite

```
delivery.db
```

---

## Future Improvements

The following enhancements are planned:

- Email validation using `EmailStr`
- Timestamp validation using `datetime`
- Webhook authentication (shared secret / HMAC)
- Date range filtering for `/analytics`
- GET `/events` endpoint with pagination
- PostgreSQL support through `DATABASE_URL`
- Concurrency tests for duplicate webhook handling
- Alembic database migrations

---

## Author

**Nandhitha Sri Maraka**

GitHub

https://github.com/nandithasri2006

LinkedIn

https://www.linkedin.com/in/nandhitha-maraka-905678293/
>>>>>>> upstream/main -->
<!-- =======
## License

MIT — [Rajat Kumar](https://github.com/rajat-wyrm)
>>>>>>> upstream/main -->
