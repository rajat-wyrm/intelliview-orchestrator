# Fix: E2E Authentication Regression

## Root Cause
In commit `a5b868f`, two changes to `tests/conftest.py` broke E2E auth:

1. `from workers.celery_app import celery_app` was moved to the **top** of the file, **before** `os.environ.setdefault("API_TOKEN", ...)`. Since `celery_app.py` triggers `config.py` to load (via `from config import REDIS_URL`), `Settings()` gets instantiated and cached via `@lru_cache` **before** the test sets the env var. pydantic-settings reads `.env` first → `API_TOKEN = "ci-test-token"`.

2. The default changed from `"test-token"` to `"dev-token-change-me"`, which doesn't match `.env`'s `ci-test-token`.

## Plan

### Step 1: Fix `tests/conftest.py` ✅
- Moved `from workers.celery_app import celery_app` back to the bottom (after `setdefault` calls)
- Changed default from `"dev-token-change-me"` to `"ci-test-token"` to match `.env`

### Step 2: Run full test suite ✅
- **188 passed, 1 warning** — all E2E tests pass

