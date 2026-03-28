from __future__ import annotations

import pytest
import respx
from httpx import ConnectError, Request, Response

from web_search.config import clear_settings_cache
from web_search.models.requests import SearchRequest
from web_search.providers import clear_provider_cache
from web_search.providers.tavily import TavilyProvider
from web_search.services.search_service import clear_search_cache
from web_search.utils.errors import ProviderError


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    clear_settings_cache()
    clear_provider_cache()
    clear_search_cache()


@pytest.mark.asyncio
@respx.mock
async def test_tavily_search_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.post("https://api.tavily.com/search").mock(
        return_value=Response(
            200,
            json={
                "answer": "MCP is a protocol for tools and context.",
                "results": [
                    {
                        "title": "MCP Intro",
                        "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                        "content": "MCP connects AI apps to tools.",
                        "raw_content": "Long page body",
                        "score": 0.95,
                        "published_date": "2026-03-25T12:00:00Z",
                    }
                ],
            },
        )
    )

    provider = TavilyProvider()
    response = await provider.search(
        SearchRequest(query="What is MCP?", extraction=True)
    )

    assert response.provider == "tavily"
    assert response.intent == "general"
    assert response.answer is not None
    assert len(response.results) == 1
    assert response.results[0].title == "MCP Intro"
    assert response.results[0].content == "Long page body"
    assert response.results[0].published_at == "2026-03-25T12:00:00Z"
    assert response.results[0].raw is None


@pytest.mark.asyncio
@respx.mock
async def test_tavily_search_debug_includes_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.post("https://api.tavily.com/search").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "MCP Intro",
                        "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                        "content": "MCP connects AI apps to tools.",
                    }
                ]
            },
        )
    )

    provider = TavilyProvider()
    response = await provider.search(SearchRequest(query="What is MCP?", debug=True))

    assert response.results[0].raw is not None


@pytest.mark.asyncio
@respx.mock
async def test_tavily_search_retries_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")
    monkeypatch.setenv("RETRY_MAX_ATTEMPTS", "2")

    route = respx.post("https://api.tavily.com/search")
    route.side_effect = [
        ConnectError("boom", request=Request("POST", "https://api.tavily.com/search")),
        Response(200, json={"results": []}),
    ]

    provider = TavilyProvider()
    response = await provider.search(SearchRequest(query="retry me"))

    assert response.results == []


@pytest.mark.asyncio
@respx.mock
async def test_tavily_search_raises_not_configured_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    provider = TavilyProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.search(SearchRequest(query="hello"))

    assert exc_info.value.error_type == "provider_not_configured"
