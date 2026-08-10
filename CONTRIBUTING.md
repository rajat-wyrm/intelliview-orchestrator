# Contributing to IntelliView Orchestrator

Thanks for your interest in contributing. This document covers development
setup, code conventions, and the pull-request process.

## Development setup

```bash
git clone https://github.com/rajat-wyrm/intelliview-orchestrator
cd intelliview-orchestrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio ruff mypy

# Frontend
cd frontend && npm install && cd ..

# Run the full stack locally
docker compose up -d --build
```

## Code conventions

### Backend (Python)

- **Style:** Ruff (PEP 8 + project rules). Run `ruff check .` and
  `ruff format --check .` before pushing. CI runs both.
- **Typing:** Annotate new public functions. `mypy` runs in CI on a
  best-effort basis.
- **Logging:** Use the existing structured logger
  (`from orchestrator.logging_config import log_event`) for events you
  want operators to be able to grep; use the standard `logger.info` for
  debug chatter.
- **Tests:** Add unit tests in `tests/test_unit_*.py` for new modules.
  Add a contract entry to `tests/test_api_contract.py` for any new
  route. Use mocks for Redis / Celery.

### Frontend (TypeScript / Next.js)

- **Style:** Next.js defaults + the project's Tailwind theme. Run
  `npm run lint` and `npm run typecheck` locally.
- **Components:** Keep them headless when possible. Use the existing
  `Card`, `Stat`, `Badge`, `Skeleton`, `ErrorState`, `EmptyState`
  primitives.
- **Accessibility:** Provide `aria-label` on icon-only buttons, prefer
  semantic landmarks, respect `prefers-reduced-motion` (use
  `useReducedMotion` from `framer-motion`).
- **API access:** Go through `lib/api.ts` and `lib/types.ts`. Don't
  hand-roll `fetch` calls.

### Database

- **Migrations:** Schema changes must ship with a migration under
  `database/migrations/`. `Base.metadata.create_all` is for dev/test only.
- **Models:** Don't add columns to `database/models.py` without
  coordinating the migration with the rollout plan.

## Pull request process

1. Fork the repo and create a topic branch:
   `git checkout -b feat/short-description`
2. Commit in small, logical chunks with imperative subject lines
   (`Fix CORS env var typo`, not `fixed stuff`).
3. Push and open a PR against `main`.
4. Fill in the PR template (auto-loaded from `.github/` if present).
5. Wait for CI to pass:
   - Ruff lint + format
   - Pytest (91+ tests, all green)
   - Frontend typecheck + lint + production build
6. Address review feedback by pushing additional commits (don't force-push
   while the PR is open unless asked).


## Commit messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/)
format for commit messages.

### Format

```text
<type>(<scope>): <subject>

## Reporting security issues

See `SECURITY.md` for the disclosure policy. **Do not file public issues
for security bugs.**

## Code of conduct

Be kind. We're all here to ship good software.
