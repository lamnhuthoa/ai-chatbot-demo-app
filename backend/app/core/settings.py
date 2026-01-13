from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
from functools import lru_cache

class AppSettings(BaseSettings):
    # Optional to allow running without a configured Gemini API key
    gemini_api_key: Optional[str] = None
    allowed_origins: str = "http://localhost:5173"
    gemini_model: str = "gemini-2.5-flash"

    # Pydantic v2 style settings config
    model_config = SettingsConfigDict(
        # Resolve to backend/app/.env regardless of current working directory
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        # Accept extra env vars (e.g., DATABASE_URL) without failing
        extra="ignore",
    )

class DatabaseSettings(BaseSettings):
    # Provide a safe default using environment; override in .env
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


settings = AppSettings()
