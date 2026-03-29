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
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.delenv("EXA_BASE_URL", raising=False)
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
            provider="exa",
            preferences={"country": "us", "safesearch": "strict"},
            include_domains=["docs.python.org"],
            exclude_domains=["reddit.com"],
            freshness="week",
            extraction=True,
        )
    )

    body = str(captured["body"])
    assert '"userLocation":"US"' in body
    assert '"moderation":true' in body
    assert '"includeDomains":["docs.python.org"]' in body
    assert '"excludeDomains":["reddit.com"]' in body
    assert '"contents":{' in body
    assert '"text":{"maxCharacters":12000}' in body
    assert '"startPublishedDate":' in body


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
    monkeypatch.delenv("EXA_API_KEY", raising=False)

    provider = ExaProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.search(SearchRequest(query="hello", provider="exa"))

    assert exc_info.value.error_type == "provider_not_configured"


@pytest.mark.asyncio
async def test_exa_extract_is_reserved_but_not_implemented_yet() -> None:
    provider = ExaProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.extract(
            ExtractRequest(urls=["https://example.com"], provider="exa")
        )

    assert exc_info.value.error_type == "provider_not_implemented"
    assert exc_info.value.provider == "exa"
