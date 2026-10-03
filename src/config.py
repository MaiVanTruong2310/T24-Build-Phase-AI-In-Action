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
    auth_database_url: str = ""
    supabase_auth_redirect_url: str = "http://localhost:5173"
    auth_provider: Literal["custom", "supabase"] = "custom"
    database_auto_create: bool = True
    booking_hold_cleanup_interval_seconds: int = Field(default=60, ge=5, le=3600)
    database_pool_size: int = Field(default=3, ge=1, le=100)
    database_max_overflow: int = Field(default=1, ge=0, le=200)
    database_pool_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    database_pool_recycle_seconds: int = Field(default=900, ge=30, le=86400)
    database_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)

    # Authentication
    auth_cookie_secure: bool | None = None
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
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
