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
    hospital_hotline: str = "1900 232 389"
    info_agent_enabled: bool = Field(default=True)


    # LLM
    llm_provider: str = Field(default="deepseek", description="Nhà cung cấp LLM chính: deepseek | openrouter | gemini | openai")
    openai_api_key: str = ""
    openai_model_name: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    model_name: str = "deepseek-chat"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    openrouter_api_key: str = ""
    openrouter_backup_keys: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model_name: str = "openai/gpt-4o-mini"
    google_ai_api_key: str = ""
    google_ai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    google_ai_model_name: str = "gemini-3.1-flash-lite"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model_name: str = "deepseek-chat"
    enable_llm_fallbacks: bool = Field(default=False, description="Tự động fallback sang các provider khác nếu có cấu hình")
    llm_request_timeout_seconds: float = Field(default=20.0, gt=0.0, le=120.0)
    llm_hedge_delay_seconds: float = Field(default=3.0, gt=0.0, le=30.0)
    llm_total_timeout_seconds: float = Field(default=25.0, gt=0.0, le=120.0)
    llm_failure_cooldown_seconds: float = Field(default=30.0, ge=1.0, le=600.0)

    # Database
    database_url: str = "sqlite:///./data/app.db"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""
    supabase_timeout_seconds: float = Field(default=8.0, gt=0.0, le=60.0)
    supabase_connect_timeout_seconds: float = Field(default=3.0, gt=0.0, le=30.0)
    supabase_max_connections: int = Field(default=50, ge=1, le=500)
    supabase_max_keepalive_connections: int = Field(default=20, ge=1, le=200)

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def is_info_agent_enabled() -> bool:
    """Kiểm tra feature flag INFO_AGENT_ENABLED từ env hoặc settings (mặc định True)."""
    import os

    val = os.getenv("INFO_AGENT_ENABLED")
    if val is not None:
        return val.strip().lower() in ("true", "1", "yes")
    return bool(get_settings().info_agent_enabled)

