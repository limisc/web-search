from __future__ import annotations

from functools import lru_cache

from mcp_search.providers.base import SearchProvider
from mcp_search.providers.tavily import TavilyProvider
from mcp_search.utils.errors import ProviderError

_PROVIDER_FACTORIES = {
    "tavily": TavilyProvider,
}


@lru_cache(maxsize=None)
def get_provider(name: str) -> SearchProvider:
    try:
        provider_factory = _PROVIDER_FACTORIES[name]
    except KeyError as exc:
        raise ProviderError(
            f"Unsupported provider: {name}",
            provider=name,
            error_type="provider_not_supported",
        ) from exc
    return provider_factory()


def clear_provider_cache() -> None:
    get_provider.cache_clear()
