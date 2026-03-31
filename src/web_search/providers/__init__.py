from __future__ import annotations

from functools import lru_cache

from web_search.providers.base import WebExtractProvider, WebSearchProvider
from web_search.providers.brave import BraveProvider
from web_search.providers.exa import ExaProvider
from web_search.providers.firecrawl import FirecrawlProvider
from web_search.providers.newsapi import NewsApiProvider
from web_search.providers.tavily import TavilyProvider
from web_search.utils.errors import ProviderError

_SEARCH_PROVIDER_FACTORIES = {
    "tavily": TavilyProvider,
    "brave": BraveProvider,
    "exa": ExaProvider,
    "newsapi": NewsApiProvider,
}
_EXTRACT_PROVIDER_FACTORIES = {
    "tavily": TavilyProvider,
    "exa": ExaProvider,
    "firecrawl": FirecrawlProvider,
}
_OPTIONAL_SEARCH_PROVIDER_NAMES = {"grok"}


@lru_cache(maxsize=None)
def get_search_provider(name: str) -> WebSearchProvider:
    if name in _OPTIONAL_SEARCH_PROVIDER_NAMES:
        raise ProviderError(
            f"Provider not implemented yet: {name}",
            provider=name,
            error_type="provider_not_implemented",
        )
    try:
        provider_factory = _SEARCH_PROVIDER_FACTORIES[name]
    except KeyError as exc:
        raise ProviderError(
            f"Unsupported search provider: {name}",
            provider=name,
            error_type="provider_not_supported",
            details={"capability": "search"},
        ) from exc
    return provider_factory()


@lru_cache(maxsize=None)
def get_extract_provider(name: str) -> WebExtractProvider:
    try:
        provider_factory = _EXTRACT_PROVIDER_FACTORIES[name]
    except KeyError as exc:
        raise ProviderError(
            f"Unsupported extract provider: {name}",
            provider=name,
            error_type="provider_not_supported",
            details={"capability": "extract"},
        ) from exc
    return provider_factory()


def is_search_provider_available(name: str) -> bool:
    return name in _SEARCH_PROVIDER_FACTORIES


def is_extract_provider_available(name: str) -> bool:
    return name in _EXTRACT_PROVIDER_FACTORIES


def clear_provider_cache() -> None:
    get_search_provider.cache_clear()
    get_extract_provider.cache_clear()
