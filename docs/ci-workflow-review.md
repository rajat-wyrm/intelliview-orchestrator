# CI Workflow Review (Issue #151)

This document reviews the GitHub Actions setup in `.github/workflows/`
prior to and as a result of this PR.

## Existing workflows

### `.github/workflows/ci.yml`

Triggers: `push` to `main`, and `pull_request` targeting `main`.

| Job | Purpose | Steps |
|---|---|---|
| `test` | Backend correctness | Ruff lint → Ruff format check → `pytest tests/ --ignore=tests/test_e2e_smoke.py -v` against live `redis:7` and `postgres:15` service containers |
| `frontend` | Frontend correctness | `npm ci` → `npm run lint` in `frontend/` |
| `docker-build` *(added by this PR)* | Container build correctness | Builds `fastapi` and `worker` images via `docker compose build`, verifies the result |

**Gaps identified before this PR:**
- No job validated that the Docker images described in
  `docker-compose.yml` (`fastapi`, `worker`) actually build. A broken
  `Dockerfile` or dependency change could merge to `main` undetected
  until someone ran `docker compose up` locally or in staging.
- `e2e_smoke` tests and a frontend build/typecheck were referenced in
  `CONTRIBUTING.md` as CI steps but were not actually run in
  `ci.yml` — the docs were out of date relative to the workflow file.

### `.github/workflows/dependabot.yml`

Configures Dependabot version-update PRs. Not a CI/test workflow — out
of scope for issue #151's build-validation ask, noted here only for
completeness.

## What this PR changes

- Adds the `docker-build` job (builds `fastapi` + `worker` images on
  every push/PR to `main`, same triggers as `test`/`frontend`).
- Uses `docker compose build --progress=plain` so failing build steps
  produce a fully expanded log in the Actions UI rather than a
  collapsed one.
- Adds a `docker compose images` step after the build so the job
  output includes explicit confirmation of which images were produced.
- Fail-on-error behavior needs no extra configuration: `docker compose
  build` exits non-zero on any layer failure, and GitHub Actions fails
  the step (and therefore the job) on any non-zero exit automatically.
  This was verified by intentionally breaking a `Dockerfile` line on
  this branch, confirming the `docker-build` check went red with the
  expected error surfaced in the plain-progress log, then reverting.
- Documents all three `ci.yml` jobs in `CONTRIBUTING.md`, including the
  intentionally-excluded `e2e_smoke` suite, and corrects the stale
  test-count figure.

## Out of scope / follow-ups

- `e2e_smoke` tests still aren't run in CI.
- Frontend typecheck and production build aren't run in CI, only lint.