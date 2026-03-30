from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    tavily_base_url: str = Field(default="https://api.tavily.com", alias="TAVILY_BASE_URL")
    brave_search_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BRAVE_SEARCH_API_KEY", "BRAVE_API_KEY"),
    )
    brave_base_url: str = Field(default="https://api.search.brave.com/res/v1", alias="BRAVE_BASE_URL")
    exa_api_key: str | None = Field(default=None, alias="EXA_API_KEY")
    exa_base_url: str = Field(default="https://api.exa.ai", alias="EXA_BASE_URL")
    firecrawl_api_key: str | None = Field(default=None, alias="FIRECRAWL_API_KEY")
    firecrawl_base_url: str = Field(default="https://api.firecrawl.dev/v2", alias="FIRECRAWL_BASE_URL")
    request_timeout_seconds: float = Field(default=20.0, alias="REQUEST_TIMEOUT_SECONDS")
    retry_max_attempts: int = Field(default=2, alias="RETRY_MAX_ATTEMPTS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    mcp_host: str = Field(default="127.0.0.1", alias="MCP_HOST")
    mcp_port: int = Field(default=8000, alias="MCP_PORT")
    mcp_path: str = Field(default="/mcp", alias="MCP_PATH")
    fastmcp_stateless_http: bool = Field(default=True, alias="FASTMCP_STATELESS_HTTP")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
