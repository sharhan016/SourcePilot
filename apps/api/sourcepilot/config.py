from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./sourcepilot.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    company_name: str = "Acme Operations"
    company_location: str = "Bengaluru, India"
    max_concurrent_workflows: int = 2
    max_concurrent_tools: int = 5
    provider_timeout_seconds: float = 20.0
    provider_max_retries: int = 2
    research_max_rounds: int = 2
    llm_provider: str = "openai"
    llm_model: str = "gpt-5-mini"
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    search_provider: str = "exa"
    exa_api_key: str | None = None
    firecrawl_api_key: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("max_concurrent_workflows", "max_concurrent_tools", "research_max_rounds")
    @classmethod
    def positive_integer(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be at least 1")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

