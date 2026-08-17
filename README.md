# Risk Weight Configuration API
**Task:** Expose API endpoints allowing recruiters to customize risk weights per job position

---

## Project Structure

```
risk-weights/
├── src/
│   ├── main.py      ← FastAPI app entry point (seeded with example configs)
│   ├── router.py    ← All CRUD endpoints
│   ├── models.py    ← Pydantic schemas & validation
│   └── store.py     ← In-memory store (drop-in replaceable with DB)
└── tests/
    └── test_api.py  ← 26 unit tests
```

---

## Setup & Run

Running `docker compose up -d --build` automatically builds and starts the entire stack, including both the FastAPI backend and the Next.js frontend.

```bash
pip install fastapi uvicorn pydantic pytest httpx

# Start server
cd src && python3 main.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/risk-configs/` | Create config for a job position |
| `GET` | `/risk-configs/` | List all configs |
| `GET` | `/risk-configs/{id}` | Get config by ID |
| `GET` | `/risk-configs/by-position/{name}` | Get config by job position name |
| `PUT` | `/risk-configs/{id}` | Update a config |
| `DELETE` | `/risk-configs/{id}` | Delete a config |
| `GET` | `/risk-engine/weights/{job_position}` | Used by risk engine — always returns weights (fallback to defaults) |

---

## Example Usage

```bash
# Create a config for Software Engineer
curl -X POST http://localhost:8000/risk-configs/ \
  -H "Content-Type: application/json" \
  -d '{
    "job_position": "Software Engineer",
    "weights": {
      "tab_switching": 3.0,
      "browser_activity": 3.0,
      "audio_interruptions": 1.0,
      "multiple_persons": 2.0,
      "candidate_absence": 2.0,
      "gaze_deviation": 1.5,
      "background_noise": 0.5
    }
  }'

# Risk engine fetches weights (never breaks even if no config exists)
curl http://localhost:8000/risk-engine/weights/Software%20Engineer
```

---

## Validation Rules

- `job_position` — required, 1–100 chars, unique (case-insensitive)
- All weights — must be `>= 0`
- At least one weight must be `> 0`
- Duplicate job positions → `409 Conflict`
- Invalid/missing config for risk engine → falls back to **default weights (all 1.0)**

---

## Run Tests

```bash
PYTHONPATH=src pytest tests/test_api.py -v
# 26 passed
```
