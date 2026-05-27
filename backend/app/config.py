from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _root_env() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_root_env()), extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")
    direct_url: str | None = Field(default=None, alias="DIRECT_URL")

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    main_model: str = Field(default="anthropic/claude-sonnet-4.5", alias="MAIN_MODEL")
    compile_model: str = Field(default="anthropic/claude-sonnet-4.5", alias="COMPILE_MODEL")
    judge_model: str = Field(default="anthropic/claude-haiku-4.5", alias="JUDGE_MODEL")

    basic_auth_user: str = Field(default="admin", alias="BASIC_AUTH_USER")
    basic_auth_pass: str = Field(default="guardrails", alias="BASIC_AUTH_PASS")

    @property
    def sync_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
