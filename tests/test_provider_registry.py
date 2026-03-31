from __future__ import annotations

from web_search.providers import (
    provider_capabilities,
    provider_supports_extract,
    provider_supports_search,
)


def test_provider_capabilities_match_current_matrix() -> None:
    assert provider_capabilities("tavily") == frozenset({"broad_search", "content_extract"})
    assert provider_capabilities("brave") == frozenset({"broad_search"})
    assert provider_capabilities("exa") == frozenset({"authoritative_search", "broad_search", "content_extract"})
    assert provider_capabilities("newsapi") == frozenset({"fresh_search"})
    assert provider_capabilities("firecrawl") == frozenset({"content_extract"})
    assert provider_capabilities("grok") == frozenset({"fresh_search", "social_search"})


def test_provider_support_helpers_follow_matrix() -> None:
    assert provider_supports_search("brave") is True
    assert provider_supports_search("firecrawl") is False
    assert provider_supports_extract("firecrawl") is True
    assert provider_supports_extract("newsapi") is False
