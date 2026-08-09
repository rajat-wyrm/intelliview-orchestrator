# Contributing to IntelliView Orchestrator

This document describes the coding standards, Git workflow, and PR process every intern/contributor follows. Follow this exact sequence for every task — no exceptions.

## 1. Sync with `main` first

Before starting any work, pull the latest `main` so you're building on the most current codebase:

```bash
git checkout main
git pull origin main
```

## 2. Create your own feature branch off `main`

Never work directly on `main`.

```bash
git checkout -b feature/task-<team>-<task>-<short-name>
```

**Branch naming convention:** `feature/task-<team>-<task>-<short-name>`, e.g.:
- `feature/task-1-1-jwt-login`
- `fix/task-5-2-ci-pipeline`

## 3. Scope your work

Do your allotted task only, on this branch. Implement exactly the work assigned to you/your sub-team for that task — don't mix in unrelated changes.

## 4. Integrate and test locally before pushing

Once your part is built:

- Pull latest `main` into your branch again to catch any changes merged by other teams:
  ```bash
  git pull origin main
  ```
- Run the full app locally and confirm your feature works end-to-end with the rest of the system:
  ```bash
  docker-compose up
  ```
- Run all relevant tests (`pytest`, `eslint`, etc.) and make sure nothing else breaks.
- Only once everything checks out locally should you commit and push your branch.

## 5. Push your branch and open a Pull Request into `main`

```bash
git push origin feature/task-<team>-<task>-<short-name>
```

- A PR requires **at least 1 code review approval + CI passing** before it can be merged.
- **Do not merge your own PR without review.**

## 6. Daily standup

Be ready to answer: What did you do? What will you do? Any blockers?

## 7. Environment variables

Never hardcode secrets, tokens, or passwords. Use environment variables (see `.env.example`) for all credentials and keys.

## 8. Tests

Write tests for every function you create — **minimum 1 unit test per function.**

## 9. Documentation

Document any new API endpoints you create (see `Task 10.3 — API Reference Site`).

## 10. Never push directly to `main`

Everything goes through a branch → PR → review, with no exceptions, at any point in this process.

---

## Commit message format

This project uses conventional commits so release notes can be generated automatically:

```
feat: add JWT-based login flow
fix: correct off-by-one error in interview scoring
chore: bump dependency versions
```

## Code style

```
TODO: fill in the actual linter/formatter config used by the repo
(e.g. black + isort for Python, eslint + prettier for JS/TS)
```

## Questions

If you're blocked, raise it at daily standup or ping the task lead before spending more than ~30 minutes stuck on a blocker.
