from __future__ import annotations

from functools import lru_cache

from web_search.providers.base import SearchProvider
from web_search.providers.brave import BraveProvider
from web_search.providers.exa import ExaProvider
from web_search.providers.firecrawl import FirecrawlProvider
from web_search.providers.tavily import TavilyProvider
from web_search.utils.errors import ProviderError

_PROVIDER_FACTORIES = {
    "tavily": TavilyProvider,
    "brave": BraveProvider,
    "exa": ExaProvider,
    "firecrawl": FirecrawlProvider,
}
_OPTIONAL_PROVIDER_NAMES = {"grok"}


@lru_cache(maxsize=None)
def get_provider(name: str) -> SearchProvider:
    if name in _OPTIONAL_PROVIDER_NAMES:
        raise ProviderError(
            f"Provider not implemented yet: {name}",
            provider=name,
            error_type="provider_not_implemented",
        )
    try:
        provider_factory = _PROVIDER_FACTORIES[name]
    except KeyError as exc:
        raise ProviderError(
            f"Unsupported provider: {name}",
            provider=name,
            error_type="provider_not_supported",
        ) from exc
    return provider_factory()


def is_provider_available(name: str) -> bool:
    return name in _PROVIDER_FACTORIES


def clear_provider_cache() -> None:
    get_provider.cache_clear()
