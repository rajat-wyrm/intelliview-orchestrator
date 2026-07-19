"""
Configuration for the AI Interview Orchestrator.

Settings are loaded from environment variables (or a `.env` file in dev)
via `pydantic-settings`. All values have sensible local defaults but
should be overridden in production.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _CsvList(list):
    """Marker type that prevents pydantic-settings from JSON-parsing."""


class Settings(BaseSettings):
    """Application configuration loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Service discovery ---
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_interview_db"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # --- Worker / Celery ---
    worker_concurrency: int = 4
    max_retries: int = 3
    worker_id: str = "worker-1"

    # --- API / Security ---
    api_token: str = Field(default="dev-token-change-me", validation_alias="API_TOKEN", alias="api_token")
    cors_allow_origins_raw: str = Field(default="*", alias="cors_allow_origins")

    # --- Request validation ---
    max_request_body_bytes: int = 1048576  # 1 MB

    # --- Audit logging ---
    audit_log_file: str = ""

    # --- Prometheus ---
    enable_prometheus: bool = True

    # --- AI Provider Keys ---
    gemini_api_key: str = ""
    grok_api_key: str = ""

    # --- Screen Lock ---
    screen_lock_timeout: int = 300
    screen_lock_pin: str = "1234"

    # --- Real-time Tracking ---
    realtime_enabled: bool = True
    realtime_tick_interval: int = 1
    moment_tracking_enabled: bool = True

    # --- Celery ---
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # --- Database SSL ---
    database_sslmode: str = "disable"

    @field_validator("postgres_host", "postgres_db", "postgres_user")
    @classmethod
    def validate_required_database_fields(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Database configuration values cannot be empty")
        return value

    @field_validator("postgres_port")
    @classmethod
    def validate_database_port(cls, value: int) -> int:
        if value <= 0 or value > 65535:
            raise ValueError("PostgreSQL port must be between 1 and 65535")
        return value

    @field_validator("database_sslmode")
    @classmethod
    def validate_database_sslmode(cls, value: str) -> str:
        allowed_modes = {
            "disable",
            "allow",
            "prefer",
            "require",
            "verify-ca",
            "verify-full",
        }

        if value not in allowed_modes:
            raise ValueError(f"Invalid database SSL mode: {value}")

        return value

    # --- Feature flags ---
    enable_celery_broker: bool = True
    json_logging: bool = True
    auto_seed_demo_data: bool = False

    # --- Derived ---
    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        base = (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        if self.database_sslmode and self.database_sslmode != "disable":
            return f"{base}?sslmode={self.database_sslmode}"
        return base

    @property
    def is_default_token(self) -> bool:
        return self.api_token == "dev-token-change-me"

    @property
    def cors_allow_origins(self) -> list[str]:
        raw = (self.cors_allow_origins_raw or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [v.strip() for v in raw.split(",") if v.strip()]


def get_settings() -> Settings:
    """Load settings from the current environment.

    Intentionally not cached to avoid stale values when environment variables
    are injected after module import (e.g., in E2E tests).
    """
    return Settings()


# Backwards compatible security token export.
# Must match request-time settings, so compute dynamically.


def _get_api_token() -> str:
    return get_settings().api_token


class _TokenProxy:
    def __str__(self) -> str:  # pragma: no cover
        return _get_api_token()

    def __repr__(self) -> str:  # pragma: no cover
        return repr(_get_api_token())

    def __eq__(self, other) -> bool:  # pragma: no cover
        return _get_api_token() == other


# Expose as API_TOKEN so legacy modules keep working.
API_TOKEN = _TokenProxy()


# ---- Legacy module-level exports (single source of truth) ----
# These names are imported across the codebase at import-time.

REDIS_URL = get_settings().redis_url
WORKER_CONCURRENCY = get_settings().worker_concurrency
DATABASE_URL = get_settings().database_url
DATABASE_SSLMODE = get_settings().database_sslmode

# Used by FastAPI app for CORS / request limits / prometheus.
CORS_ALLOW_ORIGINS = ",".join(get_settings().cors_allow_origins)
MAX_REQUEST_BODY_BYTES = get_settings().max_request_body_bytes
ENABLE_PROMETHEUS = get_settings().enable_prometheus


# Module-level aliases for backwards compatibility with imports like
# `from config import REDIS_URL`.
#
# IMPORTANT: Do not instantiate Settings at import-time for security-sensitive
# values (e.g., API tokens). Settings are environment-driven and may change
# during tests.
#
# For non-security critical aliases, we keep lazy access via functions.


def get_redis_url() -> str:
    return get_settings().redis_url


def get_database_url() -> str:
    return get_settings().database_url


def get_worker_concurrency() -> int:
    return get_settings().worker_concurrency


def get_cors_allow_origins() -> str:
    return ",".join(get_settings().cors_allow_origins)


def get_max_request_body_bytes() -> int:
    return get_settings().max_request_body_bytes


def get_enable_prometheus() -> bool:
    return get_settings().enable_prometheus


def get_database_sslmode() -> str:
    return get_settings().database_sslmode


# Backwards-compatible module-level aliases expected by other modules.
# These are non-auth values; computing them at import-time is acceptable.
# IMPORTANT: Do NOT add API_TOKEN module-level alias.
CORS_ALLOW_ORIGINS = get_cors_allow_origins()
MAX_REQUEST_BODY_BYTES = get_max_request_body_bytes()
ENABLE_PROMETHEUS = get_enable_prometheus()

# Used by database/db.py
DATABASE_SSLMODE = get_database_sslmode()
DATABASE_URL = get_database_url()


# `from config import REDIS_URL`. New code should use `get_settings()`.
settings = get_settings()
REDIS_URL = settings.redis_url
DATABASE_URL = settings.resolved_database_url
WORKER_CONCURRENCY = settings.worker_concurrency
API_TOKEN = settings.api_token
CORS_ALLOW_ORIGINS = ",".join(settings.cors_allow_origins)
MAX_REQUEST_BODY_BYTES = settings.max_request_body_bytes
ENABLE_PROMETHEUS = settings.enable_prometheus
DATABASE_SSLMODE = settings.database_sslmode

# ---------------------------------------------------------------------------
# EEOC / legal compliance — banned interview topics (Issue #121)
# ---------------------------------------------------------------------------
# Keywords whose presence in a generated question signals a legally or
# ethically prohibited interview topic under EEOC and similar regulations.
# The list is intentionally kept here so it can be extended in one place
# without touching the validation logic in workers/evaluation_pipeline.py.
BANNED_TOPICS: list[str] = [
    "age",
    "how old",
    "old are you",
    "pregnant",
    "children",
    "family planning",
    "religion",
    "religious",
    "citizenship",
    "nationality",
    "marital status",
    "married",
    "disability",
    "disabled",
    "medical condition",
    "health condition",
]
