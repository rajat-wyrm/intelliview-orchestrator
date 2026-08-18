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
style for the subject line:

```
<type>(<scope>): <subject>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`,
`ci`, `build`. Scopes: `orchestrator`, `workers`, `monitoring`,
`database`, `frontend`, `ci`, `docs`.

## Release and Changelog Workflow

This project uses Conventional Commits to maintain a consistent commit
history and support automated release management.

Use the following commit types for project changes:

- `feat`: Adds a new feature
- `fix`: Fixes a bug
- `chore`: Maintenance or tooling changes
- `docs`: Documentation changes
- `refactor`: Code restructuring without changing behavior
- `test`: Adds or updates tests

Examples:

```text
feat(orchestrator): add interview session management
fix(workers): handle failed task execution
docs: update contributing guide
refactor(database): simplify connection handling
test: add interview session tests
chore: update project dependencies
```

### Release Automation

This repository uses Semantic Release to automate versioning and publishing. Every merge into `main` triggers the release workflow, which inspects the commit history since the last release and decides whether a new version is needed.

1. What Semantic Release does
   - Reads commit messages that follow Conventional Commits.
   - Calculates the next semantic version.
   - Generates a changelog entry and release notes.
   - Creates a GitHub Release tied to the repository.
   - Updates project metadata when a releasable change is detected.

2. How the version is determined
   - `feat:` triggers a minor release.
   - `fix:` triggers a patch release.
   - `BREAKING CHANGE:` in the footer or `!` in the type/scope triggers a major release.
   - `docs:`, `style:`, `refactor:`, `test:`, and `chore:` are normally non-release changes unless a breaking change is present.

3. Which commit types trigger releases
   - `feat:` → minor release
   - `fix:` → patch release
   - `feat!:` or `feat: ...` with `BREAKING CHANGE:` → major release
   - `docs:`, `style:`, `refactor:`, `test:`, `chore:` → usually no release

4. How GitHub Actions starts the release
   - A push to `main` triggers the workflow in `.github/workflows/release.yml`.
   - The workflow checks out the repository, sets up Node.js, installs the Semantic Release dependencies, and runs `semantic-release` with `GITHUB_TOKEN`.

5. What happens after a PR is merged into `main`
   - The CI checks finish first.
   - Once the merge lands on `main`, GitHub Actions starts.
   - Semantic Release analyzes all relevant commits since the last release.
   - The tool decides whether a release is needed.

6. How release notes are generated
   - Semantic Release uses the Conventional Commits parser and the changelog plugin.
   - Release notes are grouped by feature, fix, documentation, and other commit types.
   - The generated notes are attached to the GitHub Release automatically.

7. How GitHub Releases are created
   - If a releasable commit is found, Semantic Release creates a tag such as `vX.Y.Z`.
   - It updates `CHANGELOG.md` and publishes a GitHub Release for that tag.

8. How developers should write Conventional Commits
   - Use descriptive subject lines and the correct commit type.
   - Examples:

```text
feat: add article credibility scoring
fix: correct URL extraction
docs: update installation instructions
refactor: simplify verification module
chore: update dependencies
```

Breaking changes can be written either as:

```text
feat!: redesign verification API
```

or:

```text
feat: redesign verification API

BREAKING CHANGE: API response format has changed
```

9. How to test the workflow safely
   - Run the project tests locally before merging.
   - Validate the Semantic Release config with a dry run on a feature branch if needed.
   - Do not publish a production release from a personal branch.
   - The actual release is only created from `main` after the merge is live.

10. What happens when there are no releasable commits
   - Semantic Release exits without creating a tag or release.
   - `CHANGELOG.md` remains unchanged unless a release-worthy commit is present.

Example flow:

```text
Developer commit
↓
Pull Request
↓
Merge into main
↓
GitHub Actions starts
↓
Semantic Release analyzes commits
↓
Next version calculated
↓
CHANGELOG generated/updated
↓
GitHub Release created
↓
Release notes published
```

## Reporting security issues

See `SECURITY.md` for the disclosure policy. **Do not file public issues
for security bugs.**

## Code of conduct

Be kind. We're all here to ship good software.
