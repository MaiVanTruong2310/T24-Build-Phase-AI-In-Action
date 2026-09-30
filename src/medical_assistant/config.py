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
    cors_origins: str = "http://localhost:3000"

    # LLM
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    openrouter_api_key: str = ""
    openrouter_backup_keys: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model_name: str = "openai/gpt-4o-mini"
    google_ai_api_key: str = ""
    google_ai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    google_ai_model_name: str = "gemini-3.1-flash-lite"
    llm_request_timeout_seconds: float = Field(default=20.0, gt=0.0, le=120.0)

    # Database
    database_url: str = "sqlite:///./data/app.db"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"


@lru_cache
def get_settings() -> Settings:
    return Settings()
