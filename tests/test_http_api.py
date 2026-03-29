from __future__ import annotations

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from web_search.config import clear_settings_cache
from web_search.providers import clear_provider_cache
from web_search.server import build_http_app
from web_search.services.search_service import clear_search_cache


@pytest.fixture(autouse=True)
def clear_caches() -> None:
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
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
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
