# Pull Request

## Description

Implements API endpoints allowing recruiters to customize risk weights per job position, fixing the issue where the risk scoring engine applied the same weights to every interview regardless of role.

Previously, all job positions used identical risk weights. This meant a coding assessment and a customer support interview were evaluated with the same emphasis on every signal, which did not reflect real-world requirements.

This PR introduces a full CRUD API for managing per-position risk weight configurations. The risk engine now loads the correct weights for each job position at scoring time. If no configuration exists for a position, the engine falls back to the existing default weights — so all existing functionality remains unaffected.

Fixes #12

## Type of change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [x] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Checklist

- [x] My code follows the style guidelines of this project
- [x] I have performed a self-review of my code
- [x] I have commented my code, particularly in hard-to-understand areas
- [x] I have added tests that prove my fix is effective or that my feature works
- [x] New and existing unit tests pass locally with my changes
- [x] Any dependent changes have been merged and published in downstream modules
- [x] I have only committed once

## Changes

**`src/models.py`**
- `RiskWeights` — Pydantic model for per-signal weight values with validation (all >= 0, at least one > 0)
- `RiskConfigCreate` / `RiskConfigUpdate` / `RiskConfigResponse` — request and response schemas

**`src/store.py`**
- In-memory config store with full CRUD operations
- `get_weights_for_position()` — used by risk engine; returns custom weights or defaults, never raises
- Case-insensitive job position lookup
- `clear_all()` — test isolation helper

**`src/router.py`**
- `POST /risk-configs/` — create config (409 on duplicate position)
- `GET /risk-configs/` — list all configs
- `GET /risk-configs/{id}` — get by ID
- `GET /risk-configs/by-position/{name}` — get by position name (case-insensitive)
- `PUT /risk-configs/{id}` — partial update
- `DELETE /risk-configs/{id}` — delete

**`src/main.py`**
- Mounts router
- `GET /risk-engine/weights/{job_position}` — always returns weights; fallback to defaults if no config exists
- Seeds three example configs on startup (Software Engineer, Customer Support, Remote Proctored Exam)

**`tests/test_api.py`**
- 26 unit tests covering all endpoints, validation rules, edge cases, and risk engine integration
- All 26 pass: `PYTHONPATH=src pytest tests/test_api.py -v`

## How the Risk Engine Integrates

```python
# Before (hardcoded weights)
score = calculate_risk(signals, weights=DEFAULT_WEIGHTS)

# After (position-aware weights)
weights = get_weights_for_position(job_position)  # GET /risk-engine/weights/{job_position}
score = calculate_risk(signals, weights=weights)
```

The `get_weights_for_position()` call always returns valid weights — it never raises or returns None — so the existing risk scoring function requires no changes to its interface.
