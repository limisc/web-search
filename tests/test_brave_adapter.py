from __future__ import annotations

import pytest
import respx
from httpx import ConnectError, Request, Response

from web_search.config import clear_settings_cache
from web_search.models.requests import SearchRequest
from web_search.providers import clear_provider_cache
from web_search.providers.brave import BraveProvider
from web_search.services.search_service import clear_search_cache
from web_search.utils.errors import ProviderError


@pytest.fixture(autouse=True)
def clear_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    monkeypatch.setenv("BRAVE_API_KEY", "")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")
    clear_settings_cache()
    clear_provider_cache()
    clear_search_cache()


@pytest.mark.asyncio
@respx.mock
async def test_brave_search_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")

    respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Model Context Protocol",
                            "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                            "description": "MCP connects models to tools.",
                            "extra_snippets": ["Extra context 1", "Extra context 2"],
                            "age": "2026-03-25T12:00:00Z",
                        }
                    ]
                }
            },
        )
    )

    provider = BraveProvider()
    response = await provider.search(SearchRequest(query="What is MCP?", extraction=True))

    assert response.provider == "brave"
    assert response.intent == "general"
    assert len(response.results) == 1
    assert response.results[0].title == "Model Context Protocol"
    assert response.results[0].snippet == "MCP connects models to tools."
    assert response.results[0].content == "Extra context 1\n\nExtra context 2"
    assert response.results[0].published_at == "2026-03-25T12:00:00Z"
    assert response.results[0].raw is None


@pytest.mark.asyncio
@respx.mock
async def test_brave_search_maps_supported_params(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")

    captured: dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["method"] = request.method
        captured["country"] = request.url.params.get("country")
        captured["search_lang"] = request.url.params.get("search_lang")
        captured["ui_lang"] = request.url.params.get("ui_lang")
        captured["safesearch"] = request.url.params.get("safesearch")
        captured["spellcheck"] = request.url.params.get("spellcheck")
        captured["freshness"] = request.url.params.get("freshness")
        return Response(200, json={"web": {"results": []}})

    respx.get("https://api.search.brave.com/res/v1/web/search").mock(side_effect=handler)

    provider = BraveProvider()
    await provider.search(
        SearchRequest(
            query="python asyncio",
            preferences={
                "country": "us",
                "search_lang": "en",
                "ui_lang": "en-US",
                "safesearch": "strict",
                "spellcheck": False,
            },
            freshness="week",
        )
    )

    assert captured["method"] == "GET"
    assert captured["country"] == "US"
    assert captured["search_lang"] == "en"
    assert captured["ui_lang"] == "en-US"
    assert captured["safesearch"] == "strict"
    assert captured["spellcheck"] == "false"
    assert captured["freshness"] == "pw"


@pytest.mark.asyncio
@respx.mock
async def test_brave_search_passes_multiple_goggles_via_post(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")

    captured: dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["method"] = request.method
        captured["body"] = request.content.decode("utf-8")
        return Response(200, json={"web": {"results": []}})

    respx.post("https://api.search.brave.com/res/v1/web/search").mock(side_effect=handler)

    provider = BraveProvider()
    await provider.search(
        SearchRequest(
            query="python asyncio",
            provider="brave",
            provider_options={
                "brave": {
                    "goggles": [
                        "https://example.com/dev-docs.goggle",
                        "$boost=3,site=docs.python.org",
                    ]
                }
            },
        )
    )

    assert captured["method"] == "POST"
    assert '"goggles":["https://example.com/dev-docs.goggle","$boost=3,site=docs.python.org"]' in str(captured["body"])


@pytest.mark.asyncio
@respx.mock
async def test_brave_search_uses_post_for_long_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")

    captured: dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["method"] = request.method
        captured["body"] = request.content.decode("utf-8")
        return Response(200, json={"web": {"results": []}})

    respx.post("https://api.search.brave.com/res/v1/web/search").mock(side_effect=handler)

    provider = BraveProvider()
    await provider.search(SearchRequest(query="x" * 401))

    assert captured["method"] == "POST"
    assert '"q":"' in str(captured["body"])


@pytest.mark.asyncio
@respx.mock
async def test_brave_search_combines_query_with_domain_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")

    captured: dict[str, str] = {}

    def handler(request: Request) -> Response:
        captured.update(dict(request.url.params))
        return Response(200, json={"web": {"results": []}})

    respx.get("https://api.search.brave.com/res/v1/web/search").mock(side_effect=handler)

    provider = BraveProvider()
    await provider.search(
        SearchRequest(
            query="MCP authorization",
            include_domains=["modelcontextprotocol.io", "docs.python.org"],
            exclude_domains=["reddit.com"],
        )
    )

    assert captured["q"] == (
        "MCP authorization site:modelcontextprotocol.io OR site:docs.python.org NOT site:reddit.com"
    )


@pytest.mark.asyncio
@respx.mock
async def test_brave_search_debug_includes_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")

    respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Model Context Protocol",
                            "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                            "description": "MCP connects models to tools.",
                        }
                    ]
                }
            },
        )
    )

    provider = BraveProvider()
    response = await provider.search(SearchRequest(query="What is MCP?", debug=True))

    assert response.results[0].raw is not None


@pytest.mark.asyncio
@respx.mock
async def test_brave_search_retries_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")
    monkeypatch.setenv("RETRY_MAX_ATTEMPTS", "2")

    route = respx.get("https://api.search.brave.com/res/v1/web/search")
    route.side_effect = [
        ConnectError("boom", request=Request("GET", "https://api.search.brave.com/res/v1/web/search")),
        Response(200, json={"web": {"results": []}}),
    ]

    provider = BraveProvider()
    response = await provider.search(SearchRequest(query="retry me"))

    assert response.results == []


@pytest.mark.asyncio
@respx.mock
async def test_brave_search_maps_rate_limit_to_budget_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")

    respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=Response(429, headers={"X-RateLimit-Reset": "1"}, json={"error": "rate limited"})
    )

    provider = BraveProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.search(SearchRequest(query="hello"))

    assert exc_info.value.error_type == "budget_exceeded"
    assert exc_info.value.details["retry_after_seconds"] == "1"


@pytest.mark.asyncio
async def test_brave_search_raises_not_configured_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    monkeypatch.setenv("BRAVE_API_KEY", "")

    provider = BraveProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.search(SearchRequest(query="hello"))

    assert exc_info.value.error_type == "provider_not_configured"
