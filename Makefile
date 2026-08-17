# IntelliView Orchestrator — top-level developer commands.
# Run `make help` for the full list.

SHELL := /bin/bash
PY    := python3
VENV ?= .venv
PIP  := $(VENV)/bin/pip
PYTHON := $(VENV)/bin/python

# --- Help ----------------------------------------------------------------

.PHONY: help
help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# --- Setup ---------------------------------------------------------------

.PHONY: install
install: ## Install backend + frontend deps.
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio ruff mypy
	cd frontend && npm ci

.PHONY: seed
seed: ## Seed the demo dataset (idempotent).
	$(PYTHON) scripts/seed.py

.PHONY: seed-reset
seed-reset: ## Wipe & reseed the demo dataset.
	$(PYTHON) scripts/seed.py --reset

# --- Run -----------------------------------------------------------------

.PHONY: up
up: ## Bring the whole stack up via docker-compose.
	docker compose up -d --build

.PHONY: down
down: ## Stop the docker-compose stack.
	docker compose down

.PHONY: logs
logs: ## Tail logs from all docker-compose services.
	docker compose logs -f --tail=100

.PHONY: api
api: ## Run the FastAPI server locally (needs Postgres + Redis up).
	$(PYTHON) -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: worker
worker: ## Run a Celery worker locally.
	$(PYTHON) -m workers.worker_entrypoint

.PHONY: frontend
frontend: ## Run the Next.js dev server.
	cd frontend && npm run dev

.PHONY: demo
demo: up seed ## Full one-shot: bring up the stack + seed demo data.
	@echo
	@echo "  API      → http://localhost:8000  (docs at /docs)"
	@echo "  Frontend → http://localhost:3000"
	@echo "  Flower   → http://localhost:5555/flower"
	@echo
	@echo "  Default API_TOKEN: dev-token-change-me  (paste it into the top bar)"

# --- Quality -------------------------------------------------------------

.PHONY: lint
lint: ## Ruff lint + format check on the backend.
	$(PYTHON) -m ruff check orchestrator workers monitoring database tests scripts
	$(PYTHON) -m ruff format --check orchestrator workers monitoring database tests scripts

.PHONY: fmt
fmt: ## Auto-format backend code.
	$(PYTHON) -m ruff format orchestrator workers monitoring database tests scripts
	$(PYTHON) -m ruff check --fix orchestrator workers monitoring database tests scripts

.PHONY: test
test: ## Run pytest (unit + contract, no live stack needed).
	$(PYTHON) -m pytest tests/ --ignore=tests/test_e2e_smoke.py -v

.PHONY: test-e2e
test-e2e: ## Run end-to-end smoke (requires full stack).
	$(PYTHON) -m pytest tests/test_e2e_smoke.py -v

.PHONY: test-all
test-all: test test-e2e lint ## Run everything.

.PHONY: fe-lint
fe-lint: ## Lint the frontend.
	cd frontend && npm run lint

.PHONY: fe-build
fe-build: ## Production build of the frontend.
	cd frontend && npm run build

.PHONY: clean
clean: ## Remove build artefacts and the local venv.
	rm -rf $(VENV) frontend/node_modules frontend/.next frontend/out
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	find . -name .pytest_cache -type d -prune -exec rm -rf {} +
	find . -name .ruff_cache -type d -prune -exec rm -rf {} +
	find . -name .mypy_cache -type d -prune -exec rm -rf {} +
