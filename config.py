"""
Configuration for the AI Interview Orchestrator.

Settings are loaded from environment variables (or a `.env` file in dev)
via `pydantic-settings`. All values have sensible local defaults but
should be overridden in production.
"""

import json
import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@lru_cache(maxsize=1)
def get_aws_secrets(secret_name: str, region_name: str = "us-east-1") -> dict:
    """Fetches and caches JSON secrets from AWS Secrets Manager."""
    import boto3
    from botocore.exceptions import ClientError

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        if "SecretString" in response:
            return json.loads(response["SecretString"])
    except ClientError as e:
        print(f"Error fetching secrets: {e}")
    return {}


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

    environment: str = "development"
    aws_secret_name: str = "intelliview-secrets"
    aws_region: str = "us-east-1"

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
    jwt_secret_key: str = "change-this-to-a-long-random-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
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

    def __init__(self, **values):
        super().__init__(**values)
        if self.environment.lower() == "production":
            secrets = get_aws_secrets(self.aws_secret_name, self.aws_region)
            for key, val in secrets.items():
                if hasattr(self, key.lower()):
                    setattr(self, key.lower(), val)

    # --- Feature flags ---
    enable_celery_broker: bool = True
    json_logging: bool = True
    auto_seed_demo_data: bool = False

    def validate_configuration(self) -> None:
        errors = []

        if not self.api_token.strip():
            errors.append("API_TOKEN is required.")

        if self.worker_concurrency <= 0:
            errors.append("WORKER_CONCURRENCY must be greater than 0.")

        if self.max_retries < 0:
            errors.append("MAX_RETRIES cannot be negative.")

        if self.max_request_body_bytes <= 0:
            errors.append("MAX_REQUEST_BODY_BYTES must be greater than 0.")

        if errors:
            raise ValueError(
                "Configuration validation failed:\n- " + "\n- ".join(errors)
            )

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
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes
JWT_REFRESH_TOKEN_EXPIRE_DAYS = settings.jwt_refresh_token_expire_days

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
