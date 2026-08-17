# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Production hardening: `pool_pre_ping` + `pool_recycle` on the SQLAlchemy
  engine so connections survive Postgres restarts.
- Graceful lifespan shutdown that closes Redis-backed resources.
- Auth on previously open privileged endpoints:
  `/start-interview`, `/switch-strategy`, `/retry-session/{id}`,
  `/detect-failures`.
- Scheduler rollback: if Celery dispatch fails, the worker active-task
  counter is decremented back.
- `RiskScoringEngine` and AI pipelines (`video`, `audio`, `evaluation`)
  now produce deterministic per-session signals so risk classification
  thresholds actually fire in dev/test.
- Frontend: skip-to-content link, focus trap + `aria-modal` on `Dialog`,
  `prefers-reduced-motion` support via `useReducedMotion`.
- Frontend: per-route `loading.tsx`, `error.tsx`, `not-found.tsx`.
- Frontend: analytics Risk Distribution pie now reads
  `/completed-sessions` and buckets real risk scores (no more hardcoded
  zeros).
- `Dockerfile` now runs as non-root, declares `HEALTHCHECK`, and a
  matching `.dockerignore` keeps secrets and build artefacts out of
  the image.
- CI: `ruff format --check`, `mypy` (best-effort), and a production
  `next build` step.
- Unit tests for `WorkerRegistry`, `RetryManager`, `FaultManager`, and
  the AI pipeline stubs (27 new tests, 91 total).
- Documentation: `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CHANGELOG.md`.

- Hallucination detection module using semantic similarity + NLI entailment,
  integrated into the evaluation pipeline and risk scoring engine (#67)

### Changed
- Removed dead `workers/worker.py` (replaced by `worker_entrypoint.py`).
- Removed duplicate `logging.basicConfig` that appended a handler on
  every `main.py` import.
- Lifespan now logs a loud warning when the default `API_TOKEN` is in
  use.
- README rewritten to reflect the actual production-grade surface area.

### Fixed
- `RiskScoringEngine` was always returning 0.0 because pipelines returned
  empty booleans; now produces a non-trivial per-session signal.

## [0.2.0] - 2026-06-21

### Added
- Structured JSON logging (`JSON_LOGGING` env flag) and `log_event` helper.
- Request-ID middleware (`X-Request-ID` echo + response-time header).
- SQLAlchemy 2.0 migration of all read paths (`select()` syntax).
- Frontend: command palette (`cmdk`), mobile sidebar, session-detail
  modal with live polling, search input, SVG illustrations,
  shimmer skeleton, theme toggle, keyboard-shortcut help dialog.
- Prometheus-style hooks in `MetricsCollector` (no `/metrics` endpoint
  yet — pending).

### Changed
- Tightened `StartInterviewRequest` validation (regex, length,
  whitelist priority).
- API token now checked on worker-management routes.

### Fixed
- Bare `except` clauses wrapped with logging and narrowed exception
  types.

## [0.1.0] - 2026-06-01

- Initial release: FastAPI orchestrator, Celery workers, Redis
  state cache, Postgres source of truth, Next.js dashboard.
