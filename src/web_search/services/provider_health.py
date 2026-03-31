from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from web_search.config import get_settings

ProviderHealthStatus = Literal["configured", "missing_config"]


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    status: ProviderHealthStatus

    @property
    def is_healthy(self) -> bool:
        return self.status == "configured"


def get_provider_health(provider: str) -> ProviderHealth:
    settings = get_settings()
    env_key_by_provider = {
        "tavily": settings.tavily_api_key,
        "brave": settings.brave_search_api_key,
        "exa": settings.exa_api_key,
        "newsapi": settings.newsapi_api_key,
        "firecrawl": settings.firecrawl_api_key,
    }
    configured = bool(env_key_by_provider.get(provider))
    return ProviderHealth(provider=provider, status="configured" if configured else "missing_config")
