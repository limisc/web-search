from __future__ import annotations

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from web_search.config import clear_settings_cache
from web_search.providers import clear_provider_cache
from web_search.server import build_http_app
from web_search.services.extract_service import clear_extract_cache
from web_search.services.search_service import clear_search_cache


@pytest.fixture(autouse=True)
def clear_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    monkeypatch.setenv("BRAVE_API_KEY", "")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")
    monkeypatch.setenv("EXA_API_KEY", "")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")
    monkeypatch.setenv("NEWSAPI_API_KEY", "")
    monkeypatch.setenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")
    clear_settings_cache()
    clear_provider_cache()
    clear_search_cache()
    clear_extract_cache()


@pytest.fixture
def app():
    return build_http_app(path="/mcp", stateless_http=True)


@pytest.mark.asyncio
async def test_healthz_returns_ok(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "web-search"}


@pytest.mark.asyncio
async def test_web_search_returns_invalid_request_for_bad_intent(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "hello", "intent": "bad-intent"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["type"] == "invalid_request"
    assert "intent" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_web_search_rejects_flat_country_field(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "hello", "country": "US"},
        )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "type": "invalid_request",
            "message": "Field 'country' Extra inputs are not permitted",
        }
    }


@pytest.mark.asyncio
async def test_web_search_rejects_flat_goggles_field(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "hello", "goggles": ["$boost=3,site=docs.python.org"]},
        )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "type": "invalid_request",
            "message": "Field 'goggles' Extra inputs are not permitted",
        }
    }


@pytest.mark.asyncio
async def test_web_extract_returns_invalid_request_for_bad_url(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={"urls": ["not-a-url"]},
        )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "type": "invalid_request",
            "message": "Field 'urls.0' Input should be a valid URL, relative URL without a base",
        }
    }


@pytest.mark.asyncio
async def test_web_search_returns_invalid_request_for_bad_json(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            content="{not-json}",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "type": "invalid_request",
            "message": "Request body must be valid JSON",
        }
    }




@pytest.mark.asyncio
async def test_web_search_rejects_firecrawl_as_unsupported_search_provider(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "hello", "provider": "firecrawl"},
        )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "type": "provider_not_supported",
            "message": "Unsupported search provider: firecrawl",
            "provider": "firecrawl",
            "details": {
                "capability": "search",
                "supported_capabilities": ["content_extract"],
            },
        }
    }


@pytest.mark.asyncio
async def test_web_extract_rejects_brave_as_unsupported_extract_provider(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={"urls": ["https://example.com/page"], "provider": "brave"},
        )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "type": "provider_not_supported",
            "message": "Unsupported extract provider: brave",
            "provider": "brave",
            "details": {
                "capability": "extract",
                "supported_capabilities": ["broad_search"],
            },
        }
    }


@pytest.mark.asyncio
async def test_web_search_returns_provider_not_configured_when_key_missing(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "hello"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "type": "provider_not_configured",
            "message": "TAVILY_API_KEY is not configured",
            "provider": "tavily",
            "details": {
                "attempted_provider": "tavily",
                "capability": "broad_search",
                "mode": "low_cost",
                "provider_health": {"tavily": "missing_config"},
                "provider_override_applied": False,
                "providers": ["tavily"],
                "route": "single",
            },
        }
    }


@pytest.mark.asyncio
@respx.mock
async def test_web_search_returns_budget_exceeded_for_tavily_rate_limit(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.post("https://api.tavily.com/search").mock(return_value=Response(429, json={"error": "rate limited"}))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "hello"},
        )

    assert response.status_code == 429
    assert response.json() == {
        "error": {
            "type": "budget_exceeded",
            "message": "Tavily rate limit exceeded",
            "provider": "tavily",
            "details": {
                "attempt": 1,
                "attempted_provider": "tavily",
                "capability": "broad_search",
                "mode": "low_cost",
                "provider_health": {"tavily": "configured"},
                "provider_override_applied": False,
                "providers": ["tavily"],
                "route": "single",
                "status_code": 429,
            },
        }
    }


@pytest.mark.asyncio
@respx.mock
async def test_web_search_routes_fresh_intent_to_newsapi_when_configured(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSAPI_API_KEY", "test-key")
    monkeypatch.setenv("NEWSAPI_BASE_URL", "https://newsapi.org/v2")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")

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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "latest startup funding", "intent": "fresh", "max_results": 3},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "newsapi"
    assert body["meta"]["route"] == "fallback_candidate:low_cost"
    assert body["meta"]["capability"] == "fresh_search"
    assert body["meta"]["provider_override_applied"] is False
    assert body["meta"]["verification_summary"] is None
    assert body["meta"]["partial_failures"] == []
    assert body["results"][0]["title"] == "Fresh headline"
    assert body["results"][0]["source_type"] == "news"


@pytest.mark.asyncio
@respx.mock
async def test_web_search_light_verification_dedupes_canonical_urls(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.post("https://api.tavily.com/search").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "A",
                        "url": "https://example.com/docs?utm_source=test",
                        "content": "first",
                        "score": 0.9,
                    },
                    {
                        "title": "B",
                        "url": "https://example.com/docs",
                        "content": "second",
                        "score": 0.8,
                    },
                ],
            },
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "What is MCP?", "provider": "tavily", "verification_level": "light"},
        )

    body = response.json()
    assert response.status_code == 200
    assert len(body["results"]) == 1
    assert body["results"][0]["url"] == "https://example.com/docs"
    assert body["meta"]["verification_summary"] == {"canonicalized_urls": 1, "duplicates_removed": 1}


@pytest.mark.asyncio
@respx.mock
async def test_web_search_returns_partial_failure_metadata_when_fallback_succeeds(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.get("https://api.search.brave.com/res/v1/web/search").mock(return_value=Response(503, json={"error": "unavailable"}))
    respx.post("https://api.tavily.com/search").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "Fallback result",
                        "url": "https://example.com/fallback",
                        "content": "ok",
                        "score": 0.7,
                    }
                ]
            },
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "fallback test", "provider": None},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "tavily"
    assert body["meta"]["partial_failures"] == [
        {
            "provider": "brave",
            "error_type": "provider_unavailable",
            "message": "Brave Search request failed: Server error '503 Service Unavailable' for url 'https://api.search.brave.com/res/v1/web/search?q=fallback+test&count=5&result_filter=web'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503",
        }
    ]


@pytest.mark.asyncio
@respx.mock
async def test_web_search_returns_normalized_success(app, monkeypatch: pytest.MonkeyPatch) -> None:
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
                        "score": 0.95,
                    }
                ],
            },
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "What is MCP?", "max_results": 3},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "tavily"
    assert body["query"] == "What is MCP?"
    assert body["meta"]["route"] == "single:low_cost"
    assert body["meta"]["capability"] == "broad_search"
    assert body["meta"]["provider_override_applied"] is False
    assert body["results"][0]["title"] == "MCP Intro"


@pytest.mark.asyncio
@respx.mock
async def test_web_search_returns_brave_success_when_overridden(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")

    respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Brave Result",
                            "url": "https://example.com/brave-result",
                            "description": "Brave result snippet",
                        }
                    ]
                }
            },
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={
                "query": "What is MCP?",
                "provider": "brave",
                "preferences": {"country": "us", "safesearch": "strict"},
                "provider_options": {"brave": {"goggles": "$boost=3,site=docs.python.org"}},
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "brave"
    assert body["meta"]["route"] == "provider_override:low_cost"
    assert body["meta"]["capability"] == "broad_search"
    assert body["meta"]["provider_override_applied"] is True
    assert body["results"][0]["title"] == "Brave Result"


@pytest.mark.asyncio
async def test_web_search_rejects_brave_provider_options_without_override(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={
                "query": "What is MCP?",
                "provider_options": {"brave": {"goggles": ["$boost=3,site=docs.python.org"]}},
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "type": "invalid_request",
            "message": "provider_options.brave requires provider='brave'",
        }
    }


@pytest.mark.asyncio
@respx.mock
async def test_web_search_returns_exa_success_when_overridden(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    respx.post("https://api.exa.ai/search").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "Exa Result",
                        "url": "https://example.com/exa-result",
                        "highlights": ["Exa result snippet"],
                    }
                ]
            },
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={
                "query": "What is MCP?",
                "provider": "exa",
                "preferences": {"country": "us", "safesearch": "strict"},
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "exa"
    assert body["meta"]["route"] == "provider_override:low_cost"
    assert body["meta"]["capability"] == "broad_search"
    assert body["meta"]["provider_override_applied"] is True
    assert body["results"][0]["title"] == "Exa Result"


@pytest.mark.asyncio
@respx.mock
async def test_web_search_routes_docs_to_exa_when_configured(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key")
    monkeypatch.setenv("BRAVE_BASE_URL", "https://api.search.brave.com/res/v1")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.post("https://api.exa.ai/search").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "Official MCP docs",
                        "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                        "highlights": ["Official docs snippet"],
                    }
                ]
            },
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_search",
            json={"query": "What is MCP?", "intent": "docs", "max_results": 3},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "exa"
    assert body["meta"]["route"] == "fallback_candidate:low_cost"
    assert body["meta"]["capability"] == "authoritative_search"
    assert body["meta"]["provider_override_applied"] is False
    assert body["results"][0]["title"] == "Official MCP docs"


@pytest.mark.asyncio
@respx.mock
async def test_web_extract_returns_exa_success_when_overridden(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    respx.post("https://api.exa.ai/contents").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "Exa Page",
                        "url": "https://example.com/exa-page",
                        "text": "Page body",
                        "highlights": ["chunk-1", "chunk-2"],
                    }
                ]
            },
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={
                "urls": ["https://example.com/exa-page"],
                "provider": "exa",
                "mode": "content",
                "query": "exa",
                "max_chunks": 2,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "exa"
    assert body["meta"]["route"] == "provider_override"
    assert body["meta"]["capability"] == "content_extract"
    assert body["meta"]["provider_override_applied"] is True
    assert body["meta"]["cache_state"] == "miss"
    assert body["pages"][0]["title"] == "Exa Page"
    assert body["pages"][0]["chunks"] == ["chunk-1", "chunk-2"]


@pytest.mark.asyncio
@respx.mock
async def test_web_extract_routes_content_extract_to_exa_when_configured(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.post("https://api.exa.ai/contents").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "title": "Official MCP docs",
                        "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                        "text": "Page body",
                        "highlights": ["chunk-1", "chunk-2"],
                    }
                ]
            },
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={
                "urls": ["https://modelcontextprotocol.io/docs/getting-started/intro"],
                "mode": "content",
                "query": "MCP intro",
                "max_chunks": 2,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "exa"
    assert body["meta"]["route"] == "fallback_candidate"
    assert body["meta"]["capability"] == "content_extract"
    assert body["meta"]["provider_override_applied"] is False
    assert body["pages"][0]["title"] == "Official MCP docs"


@pytest.mark.asyncio
async def test_web_extract_rejects_exa_structured_mode_for_now(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={
                "urls": ["https://example.com/exa-page"],
                "provider": "exa",
                "mode": "structured",
            },
        )

    assert response.status_code == 501
    assert response.json() == {
        "error": {
            "type": "provider_not_implemented",
            "message": "Provider not implemented yet: exa structured extract",
            "provider": "exa",
            "details": {
                "attempted_provider": "exa",
                "capability": "structured_extract",
                "mode": "structured",
                "provider_health": {"exa": "configured"},
                "provider_override_applied": True,
                "providers": ["exa"],
                "route": "provider_override",
            },
        }
    }


@pytest.mark.asyncio
@respx.mock
async def test_web_extract_returns_firecrawl_success_when_overridden(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")

    respx.post("https://api.firecrawl.dev/v2/scrape").mock(
        return_value=Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "Paragraph one\n\nParagraph two with MCP details",
                    "metadata": {
                        "title": "Model Context Protocol",
                        "sourceURL": "https://modelcontextprotocol.io/docs/getting-started/intro",
                    },
                },
            },
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={
                "urls": ["https://modelcontextprotocol.io/docs/getting-started/intro"],
                "provider": "firecrawl",
                "mode": "content",
                "query": "MCP details",
                "max_chunks": 1,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["provider"] == "firecrawl"
    assert body["meta"]["route"] == "provider_override"
    assert body["meta"]["capability"] == "content_extract"
    assert body["meta"]["provider_override_applied"] is True
    assert body["meta"]["cache_state"] == "miss"
    assert body["pages"][0]["title"] == "Model Context Protocol"
    assert body["pages"][0]["chunks"] == ["Paragraph two with MCP details"]


@pytest.mark.asyncio
async def test_web_extract_rejects_structured_extract_by_default(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={
                "urls": ["https://firecrawl.dev"],
                "mode": "structured",
                "query": "Extract company info",
            },
        )

    assert response.status_code == 501
    assert response.json() == {
        "error": {
            "type": "provider_not_implemented",
            "message": "Structured extract is not implemented yet",
            "details": {
                "capability": "structured_extract",
                "mode": "structured",
                "provider_health": {},
                "provider_override_applied": False,
                "providers": [],
                "route": "single",
            },
        }
    }


@pytest.mark.asyncio
async def test_web_extract_rejects_firecrawl_structured_override(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={
                "urls": ["https://firecrawl.dev"],
                "provider": "firecrawl",
                "mode": "structured",
                "query": "Extract company info",
            },
        )

    assert response.status_code == 501
    assert response.json() == {
        "error": {
            "type": "provider_not_implemented",
            "message": "Provider not implemented yet: firecrawl structured extract",
            "provider": "firecrawl",
            "details": {
                "attempted_provider": "firecrawl",
                "capability": "structured_extract",
                "mode": "structured",
                "provider_health": {"firecrawl": "configured"},
                "provider_override_applied": True,
                "providers": ["firecrawl"],
                "route": "provider_override",
            },
        }
    }


@pytest.mark.asyncio
async def test_web_extract_rejects_tavily_structured_mode_when_overridden(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={
                "urls": ["https://example.com/tavily-page"],
                "provider": "tavily",
                "mode": "structured",
                "query": "Extract fields"
            },
        )

    assert response.status_code == 501
    assert response.json() == {
        "error": {
            "type": "provider_not_implemented",
            "message": "Provider not implemented yet: tavily structured extract",
            "provider": "tavily",
            "details": {
                "attempted_provider": "tavily",
                "capability": "structured_extract",
                "mode": "structured",
                "provider_health": {"tavily": "configured"},
                "provider_override_applied": True,
                "providers": ["tavily"],
                "route": "provider_override",
            },
        }
    }


@pytest.mark.asyncio
async def test_web_extract_returns_firecrawl_not_configured_when_key_missing(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/web_extract",
            json={
                "urls": ["https://example.com/firecrawl-page"],
                "provider": "firecrawl",
                "mode": "content",
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "type": "provider_not_configured",
            "message": "FIRECRAWL_API_KEY is not configured",
            "provider": "firecrawl",
            "details": {
                "attempted_provider": "firecrawl",
                "capability": "content_extract",
                "provider_health": {"firecrawl": "missing_config"},
                "provider_override_applied": True,
                "providers": ["firecrawl"],
                "route": "provider_override",
            },
        }
    }
