from __future__ import annotations

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from web_search.config import clear_settings_cache
from web_search.providers import clear_provider_cache
from web_search.server import build_http_app
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
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")
    clear_settings_cache()
    clear_provider_cache()
    clear_search_cache()


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
        }
    }


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
            "message": "Provider not implemented yet: firecrawl structured extract",
            "provider": "firecrawl",
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
        }
    }
