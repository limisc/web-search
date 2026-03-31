from __future__ import annotations

import pytest
import respx
from httpx import ConnectError, Request, Response

from web_search.config import clear_settings_cache
from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.providers import clear_provider_cache
from web_search.providers.newsapi import NewsApiProvider
from web_search.services.search_service import clear_search_cache
from web_search.utils.errors import ProviderError


@pytest.fixture(autouse=True)
def clear_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSAPI_API_KEY", "")
    monkeypatch.setenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")
    clear_settings_cache()
    clear_provider_cache()
    clear_search_cache()


@pytest.mark.asyncio
@respx.mock
async def test_newsapi_search_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSAPI_API_KEY", "test-key")
    monkeypatch.setenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")

    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=Response(
            200,
            json={
                "status": "ok",
                "totalResults": 1,
                "articles": [
                    {
                        "source": {"id": "techcrunch", "name": "TechCrunch"},
                        "author": "TC",
                        "title": "Fresh headline",
                        "description": "Latest product update",
                        "url": "https://example.com/fresh-headline",
                        "publishedAt": "2026-03-30T12:00:00Z",
                        "content": "Longer article body",
                    }
                ],
            },
        )
    )

    provider = NewsApiProvider()
    response = await provider.search(SearchRequest(query="latest startup funding", intent="fresh", extraction=True))

    assert response.provider == "newsapi"
    assert response.results[0].title == "Fresh headline"
    assert response.results[0].snippet == "Latest product update"
    assert response.results[0].content == "Longer article body"
    assert response.results[0].source_type == "news"
    assert response.results[0].published_at == "2026-03-30T12:00:00Z"


@pytest.mark.asyncio
@respx.mock
async def test_newsapi_search_maps_supported_params(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSAPI_API_KEY", "test-key")
    monkeypatch.setenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")

    captured: dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["header"] = request.headers.get("X-Api-Key")
        captured["q"] = request.url.params.get("q")
        captured["domains"] = request.url.params.get("domains")
        captured["excludeDomains"] = request.url.params.get("excludeDomains")
        captured["language"] = request.url.params.get("language")
        captured["sortBy"] = request.url.params.get("sortBy")
        captured["from"] = request.url.params.get("from")
        captured["pageSize"] = request.url.params.get("pageSize")
        return Response(200, json={"status": "ok", "totalResults": 0, "articles": []})

    respx.get("https://newsapi.org/v2/everything").mock(side_effect=handler)

    provider = NewsApiProvider()
    await provider.search(
        SearchRequest(
            query="latest startup funding",
            intent="fresh",
            freshness="week",
            preferences={"search_lang": "en-US"},
            include_domains=["techcrunch.com", "theverge.com"],
            exclude_domains=["example.com"],
            max_results=3,
        )
    )

    assert captured["header"] == "test-key"
    assert captured["q"] == "latest startup funding"
    assert captured["domains"] == "techcrunch.com,theverge.com"
    assert captured["excludeDomains"] == "example.com"
    assert captured["language"] == "en"
    assert captured["sortBy"] == "publishedAt"
    assert captured["pageSize"] == "3"
    assert isinstance(captured["from"], str)


@pytest.mark.asyncio
@respx.mock
async def test_newsapi_search_maps_api_key_exhausted_to_budget_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSAPI_API_KEY", "test-key")
    monkeypatch.setenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")

    respx.get("https://newsapi.org/v2/everything").mock(
        return_value=Response(429, json={"status": "error", "code": "apiKeyExhausted", "message": "No more requests available"})
    )

    provider = NewsApiProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.search(SearchRequest(query="latest startup funding", intent="fresh"))

    assert exc_info.value.error_type == "budget_exceeded"
    assert exc_info.value.provider == "newsapi"


@pytest.mark.asyncio
async def test_newsapi_search_raises_not_configured_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSAPI_API_KEY", "")

    provider = NewsApiProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.search(SearchRequest(query="latest startup funding", intent="fresh"))

    assert exc_info.value.error_type == "provider_not_configured"


@pytest.mark.asyncio
async def test_newsapi_extract_is_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSAPI_API_KEY", "test-key")
    monkeypatch.setenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")

    provider = NewsApiProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.extract(ExtractRequest(urls=["https://example.com/article"], provider="newsapi"))

    assert exc_info.value.error_type == "provider_not_implemented"
    assert exc_info.value.provider == "newsapi"


@pytest.mark.asyncio
@respx.mock
async def test_newsapi_search_retries_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSAPI_API_KEY", "test-key")
    monkeypatch.setenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")
    monkeypatch.setenv("RETRY_MAX_ATTEMPTS", "2")

    route = respx.get("https://newsapi.org/v2/everything")
    route.side_effect = [
        ConnectError("boom", request=Request("GET", "https://newsapi.org/v2/everything")),
        Response(200, json={"status": "ok", "totalResults": 0, "articles": []}),
    ]

    provider = NewsApiProvider()
    response = await provider.search(SearchRequest(query="latest startup funding", intent="fresh"))

    assert response.results == []
