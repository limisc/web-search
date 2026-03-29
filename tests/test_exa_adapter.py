from __future__ import annotations

import pytest
import respx
from httpx import ConnectError, Request, Response

from web_search.config import clear_settings_cache
from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.providers import clear_provider_cache
from web_search.providers.exa import ExaProvider
from web_search.services.search_service import clear_search_cache
from web_search.utils.errors import ProviderError


@pytest.fixture(autouse=True)
def clear_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")
    clear_settings_cache()
    clear_provider_cache()
    clear_search_cache()


@pytest.mark.asyncio
@respx.mock
async def test_exa_search_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    respx.post("https://api.exa.ai/search").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "Model Context Protocol",
                        "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                        "publishedDate": "2026-03-25T12:00:00Z",
                        "highlights": ["MCP connects models to tools."],
                        "text": "Long page body",
                        "summary": "Summary text",
                    }
                ]
            },
        )
    )

    provider = ExaProvider()
    response = await provider.search(SearchRequest(query="What is MCP?", extraction=True, provider="exa"))

    assert response.provider == "exa"
    assert response.intent == "general"
    assert len(response.results) == 1
    assert response.results[0].title == "Model Context Protocol"
    assert response.results[0].snippet == "MCP connects models to tools."
    assert response.results[0].content == "Long page body"
    assert response.results[0].published_at == "2026-03-25T12:00:00Z"
    assert response.results[0].raw is None


@pytest.mark.asyncio
@respx.mock
async def test_exa_search_maps_supported_params(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    captured: dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["body"] = request.content.decode("utf-8")
        return Response(200, json={"results": []})

    respx.post("https://api.exa.ai/search").mock(side_effect=handler)

    provider = ExaProvider()
    await provider.search(
        SearchRequest(
            query="python asyncio",
            intent="docs",
            provider="exa",
            preferences={"country": "us", "safesearch": "strict"},
            include_domains=["docs.python.org"],
            exclude_domains=["reddit.com"],
            freshness="week",
            extraction=True,
        )
    )

    body = str(captured["body"])
    assert '"query":"python asyncio official documentation"' in body
    assert '"userLocation":"US"' in body
    assert '"moderation":true' in body
    assert '"includeDomains":["docs.python.org"]' in body
    assert '"excludeDomains":["reddit.com"]' in body
    assert '"contents":{' in body
    assert '"text":{"maxCharacters":12000}' in body
    assert '"startPublishedDate":' in body


@pytest.mark.asyncio
async def test_exa_search_adds_docs_hint_only_for_docs_intent() -> None:
    provider = ExaProvider()

    docs_query = provider._query_for(SearchRequest(query="Model Context Protocol", intent="docs", provider="exa"))
    general_query = provider._query_for(SearchRequest(query="Model Context Protocol", intent="general", provider="exa"))
    explicit_query = provider._query_for(
        SearchRequest(query="Model Context Protocol official documentation", intent="docs", provider="exa")
    )

    assert docs_query == "Model Context Protocol official documentation"
    assert general_query == "Model Context Protocol"
    assert explicit_query == "Model Context Protocol official documentation"


@pytest.mark.asyncio
@respx.mock
async def test_exa_search_debug_includes_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    respx.post("https://api.exa.ai/search").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "Model Context Protocol",
                        "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                        "highlights": ["MCP connects models to tools."],
                    }
                ]
            },
        )
    )

    provider = ExaProvider()
    response = await provider.search(SearchRequest(query="What is MCP?", debug=True, provider="exa"))

    assert response.results[0].raw is not None


@pytest.mark.asyncio
@respx.mock
async def test_exa_search_retries_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")
    monkeypatch.setenv("RETRY_MAX_ATTEMPTS", "2")

    route = respx.post("https://api.exa.ai/search")
    route.side_effect = [
        ConnectError("boom", request=Request("POST", "https://api.exa.ai/search")),
        Response(200, json={"results": []}),
    ]

    provider = ExaProvider()
    response = await provider.search(SearchRequest(query="retry me", provider="exa"))

    assert response.results == []


@pytest.mark.asyncio
@respx.mock
async def test_exa_search_maps_rate_limit_to_budget_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    respx.post("https://api.exa.ai/search").mock(return_value=Response(429, json={"error": "rate limited"}))

    provider = ExaProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.search(SearchRequest(query="hello", provider="exa"))

    assert exc_info.value.error_type == "budget_exceeded"


@pytest.mark.asyncio
async def test_exa_search_raises_not_configured_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "")

    provider = ExaProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.search(SearchRequest(query="hello", provider="exa"))

    assert exc_info.value.error_type == "provider_not_configured"


@pytest.mark.asyncio
@respx.mock
async def test_exa_extract_normalizes_content_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    respx.post("https://api.exa.ai/contents").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "Model Context Protocol",
                        "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                        "text": "Page body",
                        "highlights": ["chunk-1", "chunk-2"],
                        "summary": "Summary text",
                    }
                ]
            },
        )
    )

    provider = ExaProvider()
    response = await provider.extract(
        ExtractRequest(
            urls=["https://modelcontextprotocol.io/docs/getting-started/intro"],
            provider="exa",
            query="intro",
            max_chunks=2,
        )
    )

    assert response.provider == "exa"
    assert response.mode == "content"
    assert len(response.pages) == 1
    assert response.pages[0].title == "Model Context Protocol"
    assert response.pages[0].content == "Page body"
    assert response.pages[0].excerpt == "chunk-1"
    assert response.pages[0].chunks == ["chunk-1", "chunk-2"]
    assert response.pages[0].raw is None


@pytest.mark.asyncio
@respx.mock
async def test_exa_extract_maps_supported_params(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    captured: dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["body"] = request.content.decode("utf-8")
        return Response(200, json={"results": []})

    respx.post("https://api.exa.ai/contents").mock(side_effect=handler)

    provider = ExaProvider()
    await provider.extract(
        ExtractRequest(
            urls=["https://example.com/page"],
            provider="exa",
            query="key findings",
            max_chunks=3,
        )
    )

    body = str(captured["body"])
    assert '"urls":["https://example.com/page"]' in body
    assert '"text":{"maxCharacters":6000}' in body
    assert '"highlights":{"query":"key findings","maxCharacters":2400}' in body


@pytest.mark.asyncio
async def test_exa_extract_rejects_structured_mode_for_now(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    provider = ExaProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.extract(
            ExtractRequest(urls=["https://example.com"], provider="exa", mode="structured")
        )

    assert exc_info.value.error_type == "provider_not_implemented"
    assert exc_info.value.provider == "exa"
