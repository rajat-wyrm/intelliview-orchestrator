"""
Configuration for the AI Interview Orchestrator.

Settings are loaded from environment variables (or a `.env` file in dev)
via `pydantic-settings`. All values have sensible local defaults but
should be overridden in production.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _CsvList(list):
    """Marker type that prevents pydantic-settings from JSON-parsing."""

    pass


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
    api_token: str = "dev-token-change-me"
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
            raise ValueError(
                "Database configuration values cannot be empty"
            )
        return value


    @field_validator("postgres_port")
    @classmethod
    def validate_database_port(cls, value: int) -> int:
        if value <= 0 or value > 65535:
            raise ValueError(
                "PostgreSQL port must be between 1 and 65535"
            )
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
            raise ValueError(
                f"Invalid database SSL mode: {value}"
            )

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
    def cors_allow_origins(self) -> List[str]:
        raw = (self.cors_allow_origins_raw or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [v.strip() for v in raw.split(",") if v.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor (per-process)."""
    return Settings()


# Module-level aliases for backwards compatibility with imports like
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
