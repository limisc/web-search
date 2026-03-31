from __future__ import annotations

from functools import lru_cache
from typing import Literal

from web_search.providers.base import WebExtractProvider, WebSearchProvider
from web_search.providers.brave import BraveProvider
from web_search.providers.exa import ExaProvider
from web_search.providers.firecrawl import FirecrawlProvider
from web_search.providers.newsapi import NewsApiProvider
from web_search.providers.tavily import TavilyProvider
from web_search.utils.errors import ProviderError

ProviderCapability = Literal[
    "authoritative_search",
    "fresh_search",
    "broad_search",
    "social_search",
    "content_extract",
    "structured_extract",
]

_PROVIDER_FACTORIES = {
    "tavily": TavilyProvider,
    "brave": BraveProvider,
    "exa": ExaProvider,
    "newsapi": NewsApiProvider,
    "firecrawl": FirecrawlProvider,
}
_PROVIDER_CAPABILITIES: dict[str, frozenset[ProviderCapability]] = {
    "tavily": frozenset({"broad_search", "content_extract"}),
    "brave": frozenset({"broad_search"}),
    "exa": frozenset({"authoritative_search", "broad_search", "content_extract"}),
    "newsapi": frozenset({"fresh_search"}),
    "firecrawl": frozenset({"content_extract"}),
}
_OPTIONAL_PROVIDER_CAPABILITIES: dict[str, frozenset[ProviderCapability]] = {
    "grok": frozenset({"fresh_search", "social_search"}),
}
_SEARCH_CAPABILITIES: frozenset[ProviderCapability] = frozenset(
    {"authoritative_search", "fresh_search", "broad_search", "social_search"}
)
_EXTRACT_CAPABILITIES: frozenset[ProviderCapability] = frozenset({"content_extract", "structured_extract"})


@lru_cache(maxsize=None)
def get_search_provider(name: str) -> WebSearchProvider:
    if name in _OPTIONAL_PROVIDER_CAPABILITIES:
        raise ProviderError(
            f"Provider not implemented yet: {name}",
            provider=name,
            error_type="provider_not_implemented",
        )
    if not provider_supports_search(name):
        raise ProviderError(
            f"Unsupported search provider: {name}",
            provider=name,
            error_type="provider_not_supported",
            details={"capability": "search", "supported_capabilities": sorted(provider_capabilities(name))},
        )
    return _provider_factory(name)()


@lru_cache(maxsize=None)
def get_extract_provider(name: str) -> WebExtractProvider:
    if not provider_supports_extract(name):
        raise ProviderError(
            f"Unsupported extract provider: {name}",
            provider=name,
            error_type="provider_not_supported",
            details={"capability": "extract", "supported_capabilities": sorted(provider_capabilities(name))},
        )
    return _provider_factory(name)()


def provider_capabilities(name: str) -> frozenset[ProviderCapability]:
    if name in _PROVIDER_CAPABILITIES:
        return _PROVIDER_CAPABILITIES[name]
    if name in _OPTIONAL_PROVIDER_CAPABILITIES:
        return _OPTIONAL_PROVIDER_CAPABILITIES[name]
    return frozenset()


def provider_supports_search(name: str) -> bool:
    return bool(provider_capabilities(name) & _SEARCH_CAPABILITIES)


def provider_supports_extract(name: str) -> bool:
    return bool(provider_capabilities(name) & _EXTRACT_CAPABILITIES)


def is_search_provider_available(name: str) -> bool:
    return name in _PROVIDER_FACTORIES and provider_supports_search(name)


def is_extract_provider_available(name: str) -> bool:
    return name in _PROVIDER_FACTORIES and provider_supports_extract(name)


def _provider_factory(name: str):
    try:
        return _PROVIDER_FACTORIES[name]
    except KeyError as exc:
        raise ProviderError(
            f"Unsupported provider: {name}",
            provider=name,
            error_type="provider_not_supported",
        ) from exc


def clear_provider_cache() -> None:
    get_search_provider.cache_clear()
    get_extract_provider.cache_clear()
