from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI20K Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:5173"

    # LLM
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Database
    database_url: str = ""
    # Schema changes are managed by Alembic. Keep ORM bootstrap opt-in so
    # multiple API/worker processes cannot race while creating tables.
    database_auto_create: bool = False
    booking_maintenance_interval_seconds: int = Field(default=60, ge=5, le=3600)
    appointment_reminder_lead_days: int = Field(default=2, ge=1, le=30)
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)
    database_pool_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    database_pool_recycle_seconds: int = Field(default=900, ge=30, le=86400)
    database_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)

    # Authentication
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    jwt_refresh_token_expire_days: int = Field(default=30, ge=1, le=365)
    otp_expire_minutes: int = Field(default=5, ge=1, le=30)
    otp_max_attempts: int = Field(default=5, ge=1, le=10)
    mock_otp_code: str = ""

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Notification / Kafka
    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    notification_topic: str = "notifications.v1"
    notification_dead_letter_topic: str = "notifications.dead-letter.v1"
    notification_consumer_group: str = "notification-worker"
    notification_poll_interval_seconds: float = Field(default=2.0, gt=0.1, le=60.0)
    notification_processing_timeout_seconds: int = Field(default=300, ge=30, le=86400)
    notification_max_attempts: int = Field(default=5, ge=1, le=20)
    notification_retry_backoff_seconds: int = Field(default=5, ge=1, le=3600)
    notification_retry_backoff_max_seconds: int = Field(default=3600, ge=1, le=86400)

    # Gmail SMTP App Password
    gmail_smtp_host: str = "smtp.gmail.com"
    gmail_smtp_port: int = Field(default=587, ge=1, le=65535)
    gmail_smtp_username: str = ""
    gmail_smtp_app_password: str = ""
    gmail_from_email: str = ""


def parse_cors_origins(value: str) -> list[str]:
    """Parse comma-separated origins into values browsers can match exactly."""
    origins: list[str] = []
    for raw_origin in value.split(","):
        origin = raw_origin.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


@lru_cache
def get_settings() -> Settings:
    """Load and cache application settings from the environment and .env file."""
    return Settings()
