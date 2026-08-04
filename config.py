"""
Configuration for the AI Interview Orchestrator.

Settings are loaded from environment variables (or a `.env` file in dev)
via `pydantic-settings`. All values have sensible local defaults but
should be overridden in production.
"""
import json
import os
from functools import lru_cache

from pydantic import Field
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
    def database_url(self) -> str:
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
DATABASE_URL = settings.database_url
WORKER_CONCURRENCY = settings.worker_concurrency
API_TOKEN = settings.api_token
CORS_ALLOW_ORIGINS = ",".join(settings.cors_allow_origins)
MAX_REQUEST_BODY_BYTES = settings.max_request_body_bytes
ENABLE_PROMETHEUS = settings.enable_prometheus
DATABASE_SSLMODE = settings.database_sslmode
