from __future__ import annotations

import pytest
import respx
from fastmcp.exceptions import ToolError, ValidationError as MCPValidationError
from httpx import ConnectError, Request, Response

from web_search.config import clear_settings_cache
from web_search.providers import clear_provider_cache
from web_search.services.search_service import clear_search_cache
from web_search.tools.web_extract import web_extract
from web_search.tools.web_search import web_search


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    clear_settings_cache()
    clear_provider_cache()
    clear_search_cache()


@pytest.mark.asyncio
async def test_web_search_returns_tool_error_for_unavailable_provider() -> None:
    with pytest.raises(ToolError):
        await web_search(query="hello", intent="docs", provider="unknown")


@pytest.mark.asyncio
@respx.mock
async def test_web_extract_returns_normalized_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.post("https://api.tavily.com/extract").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://modelcontextprotocol.io/docs/getting-started/intro",
                        "title": "Model Context Protocol",
                        "raw_content": "Page body",
                        "chunks": ["chunk-1", "chunk-2"],
                    }
                ]
            },
        )
    )

    result = await web_extract(
        urls=["https://modelcontextprotocol.io/docs/getting-started/intro"],
        format="text",
    )

    assert "pages" in result
    assert len(result["pages"]) == 1
    assert result["pages"][0]["title"] == "Model Context Protocol"
    assert result["pages"][0]["chunks"] == ["chunk-1", "chunk-2"]
    assert result["mode"] == "content"


@pytest.mark.asyncio
async def test_web_extract_raises_validation_error_for_invalid_url() -> None:
    with pytest.raises(MCPValidationError):
        await web_extract(urls=["not-a-url"])


@pytest.mark.asyncio
async def test_web_extract_raises_validation_error_for_invalid_max_chunks() -> None:
    with pytest.raises(MCPValidationError):
        await web_extract(
            urls=["https://modelcontextprotocol.io/docs/getting-started/intro"],
            max_chunks=99,
        )


@pytest.mark.asyncio
@respx.mock
async def test_web_extract_raises_provider_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.post("https://api.tavily.com/extract").mock(return_value=Response(401, json={"error": "unauthorized"}))

    with pytest.raises(ToolError):
        await web_extract(
            urls=["https://modelcontextprotocol.io/docs/getting-started/intro"],
        )


@pytest.mark.asyncio
@respx.mock
async def test_web_search_raises_provider_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    respx.post("https://api.tavily.com/search").mock(return_value=Response(401, json={"error": "unauthorized"}))

    with pytest.raises(ToolError):
        await web_search(query="hello")


@pytest.mark.asyncio
@respx.mock
async def test_web_search_raises_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    route = respx.post("https://api.tavily.com/search")
    route.mock(side_effect=ConnectError("boom", request=Request("POST", "https://api.tavily.com/search")))

    with pytest.raises(ToolError):
        await web_search(query="hello")


@pytest.mark.asyncio
@respx.mock
async def test_web_search_raises_provider_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    with pytest.raises(ToolError):
        await web_search(query="hello")


@pytest.mark.asyncio
@respx.mock
async def test_web_extract_raises_provider_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("TAVILY_BASE_URL", "https://api.tavily.com")

    with pytest.raises(ToolError):
        await web_extract(
            urls=["https://modelcontextprotocol.io/docs/getting-started/intro"],
        )
