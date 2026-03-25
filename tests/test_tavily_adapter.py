from __future__ import annotations

import pytest
import respx
from httpx import Response

from mcp_search.models.requests import SearchRequest
from mcp_search.providers.tavily import TavilyProvider


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
                    }
                ],
            },
        )
    )

    provider = TavilyProvider()
    response = await provider.search(
        SearchRequest(query="What is MCP?", include_raw_content=True)
    )

    assert response.provider == "tavily"
    assert response.answer is not None
    assert len(response.results) == 1
    assert response.results[0].title == "MCP Intro"
    assert response.results[0].content == "Long page body"
