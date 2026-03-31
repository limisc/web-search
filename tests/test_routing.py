from __future__ import annotations

import pytest

from web_search.config import clear_settings_cache
from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.services.extract_router import ExtractRouter
from web_search.services.router import Router


@pytest.fixture(autouse=True)
def clear_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    monkeypatch.setenv("BRAVE_API_KEY", "")
    monkeypatch.setenv("EXA_API_KEY", "")
    monkeypatch.setenv("NEWSAPI_API_KEY", "")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")
    clear_settings_cache()


def test_search_router_returns_typed_docs_route_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "exa-key")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")
    clear_settings_cache()

    decision = Router().plan(SearchRequest(query="mcp", intent="docs"))

    assert decision.capability == "authoritative_search"
    assert decision.route == "fallback_candidate"
    assert decision.primary_provider == "exa"
    assert decision.fallback_providers == ("brave", "tavily")
    assert decision.provider_override_applied is False
    assert decision.allows_fallback is True
    assert decision.details() == {
        "route": "fallback_candidate",
        "capability": "authoritative_search",
        "provider_override_applied": False,
        "providers": ["exa", "brave", "tavily"],
    }


def test_search_router_marks_explicit_provider_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")
    clear_settings_cache()

    decision = Router().plan(SearchRequest(query="mcp", provider="tavily"))

    assert decision.capability == "broad_search"
    assert decision.route == "provider_override"
    assert decision.providers == ("tavily",)
    assert decision.provider_override_applied is True
    assert decision.allows_fallback is False


def test_extract_router_prefers_exa_for_content_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "exa-key")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")
    clear_settings_cache()

    decision = ExtractRouter().plan(
        ExtractRequest.from_tool_args(
            urls=["https://example.com/page"],
            mode="content",
            query="needle",
            max_chunks=1,
        )
    )

    assert decision.capability == "content_extract"
    assert decision.route == "fallback_candidate"
    assert decision.primary_provider == "exa"
    assert decision.fallback_providers == ("tavily",)
    assert decision.allows_fallback is True
    assert decision.details() == {
        "route": "fallback_candidate",
        "capability": "content_extract",
        "provider_override_applied": False,
        "providers": ["exa", "tavily"],
    }


def test_extract_router_returns_structured_route_without_default_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "exa-key")
    clear_settings_cache()

    decision = ExtractRouter().plan(
        ExtractRequest.from_tool_args(
            urls=["https://example.com/page"],
            mode="structured",
        )
    )

    assert decision.capability == "structured_extract"
    assert decision.route == "single"
    assert decision.providers == ()
    assert decision.primary_provider is None
    assert decision.fallback_providers == ()
    assert decision.allows_fallback is False
    assert decision.details() == {
        "route": "single",
        "capability": "structured_extract",
        "provider_override_applied": False,
        "providers": [],
    }
