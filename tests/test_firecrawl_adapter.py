from __future__ import annotations

import pytest
import respx
from httpx import ConnectError, Request, Response

from web_search.config import clear_settings_cache
from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.providers import clear_provider_cache
from web_search.providers.firecrawl import FirecrawlProvider
from web_search.services.search_service import clear_search_cache
from web_search.utils.errors import ProviderError


@pytest.fixture(autouse=True)
def clear_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")
    clear_settings_cache()
    clear_provider_cache()
    clear_search_cache()


@pytest.mark.asyncio
@respx.mock
async def test_firecrawl_extract_normalizes_results(monkeypatch: pytest.MonkeyPatch) -> None:
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

    provider = FirecrawlProvider()
    response = await provider.extract(
        ExtractRequest(
            urls=["https://modelcontextprotocol.io/docs/getting-started/intro"],
            provider="firecrawl",
            query="MCP details",
            max_chunks=1,
        )
    )

    assert response.provider == "firecrawl"
    assert response.mode == "content"
    assert len(response.pages) == 1
    assert response.pages[0].title == "Model Context Protocol"
    assert response.pages[0].content == "Paragraph one\n\nParagraph two with MCP details"
    assert response.pages[0].chunks == ["Paragraph two with MCP details"]
    assert response.pages[0].raw is None


@pytest.mark.asyncio
@respx.mock
async def test_firecrawl_extract_respects_text_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")

    respx.post("https://api.firecrawl.dev/v2/scrape").mock(
        return_value=Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "# Heading\n\n- item one\n\nThis has [a link](https://example.com)",
                    "metadata": {"sourceURL": "https://example.com"},
                },
            },
        )
    )

    provider = FirecrawlProvider()
    response = await provider.extract(
        ExtractRequest(
            urls=["https://example.com/page"],
            provider="firecrawl",
            format="text",
            query="link",
            max_chunks=1,
        )
    )

    assert response.pages[0].content == "Heading\nitem one\n\nThis has a link"
    assert response.pages[0].chunks == ["This has a link"]


@pytest.mark.asyncio
@respx.mock
async def test_firecrawl_extract_maps_supported_params(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")

    captured: dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["body"] = request.content.decode("utf-8")
        captured["authorization"] = request.headers.get("Authorization")
        return Response(200, json={"success": True, "data": {"markdown": "Body", "metadata": {"sourceURL": "https://example.com"}}})

    respx.post("https://api.firecrawl.dev/v2/scrape").mock(side_effect=handler)

    provider = FirecrawlProvider()
    await provider.extract(
        ExtractRequest(
            urls=["https://example.com/page"],
            provider="firecrawl",
            query="key findings",
            max_chunks=2,
        )
    )

    body = str(captured["body"])
    assert captured["authorization"] == "Bearer test-key"
    assert '"url":"https://example.com/page"' in body
    assert '"formats":["markdown"]' in body
    assert '"onlyMainContent":true' in body


@pytest.mark.asyncio
@respx.mock
async def test_firecrawl_extract_retries_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")
    monkeypatch.setenv("RETRY_MAX_ATTEMPTS", "2")

    route = respx.post("https://api.firecrawl.dev/v2/scrape")
    route.side_effect = [
        ConnectError("boom", request=Request("POST", "https://api.firecrawl.dev/v2/scrape")),
        Response(200, json={"success": True, "data": {"markdown": "Body", "metadata": {"sourceURL": "https://example.com"}}}),
    ]

    provider = FirecrawlProvider()
    response = await provider.extract(ExtractRequest(urls=["https://example.com"], provider="firecrawl"))

    assert len(response.pages) == 1


@pytest.mark.asyncio
@respx.mock
async def test_firecrawl_extract_maps_rate_limit_to_budget_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")

    respx.post("https://api.firecrawl.dev/v2/scrape").mock(return_value=Response(429, json={"error": "rate limited"}))

    provider = FirecrawlProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.extract(ExtractRequest(urls=["https://example.com"], provider="firecrawl"))

    assert exc_info.value.error_type == "budget_exceeded"


@pytest.mark.asyncio
async def test_firecrawl_extract_raises_not_configured_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")

    provider = FirecrawlProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.extract(ExtractRequest(urls=["https://example.com"], provider="firecrawl"))

    assert exc_info.value.error_type == "provider_not_configured"


@pytest.mark.asyncio
async def test_firecrawl_search_is_reserved_but_not_implemented_yet() -> None:
    provider = FirecrawlProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.search(SearchRequest(query="hello", provider="firecrawl"))

    assert exc_info.value.error_type == "provider_not_implemented"
    assert exc_info.value.provider == "firecrawl"


@pytest.mark.asyncio
@respx.mock
async def test_firecrawl_structured_extract_normalizes_scrape_json_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")

    captured: dict[str, object] = {}

    def scrape_handler(request: Request) -> Response:
        captured["body"] = request.content.decode("utf-8")
        return Response(
            200,
            json={
                "success": True,
                "data": {
                    "json": {"company": {"name": "Firecrawl", "supports_sso": True}},
                    "metadata": {"sourceURL": "https://firecrawl.dev"},
                },
            },
        )

    respx.post("https://api.firecrawl.dev/v2/scrape").mock(side_effect=scrape_handler)

    provider = FirecrawlProvider()
    response = await provider.extract(
        ExtractRequest(
            urls=["https://firecrawl.dev"],
            provider="firecrawl",
            mode="structured",
            schema={
                "type": "object",
                "properties": {
                    "company": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "supports_sso": {"type": "boolean"},
                        },
                        "required": ["name", "supports_sso"],
                    }
                },
                "required": ["company"],
            },
            query="Extract company info",
        )
    )

    body = str(captured["body"])
    assert '"url":"https://firecrawl.dev/"' in body
    assert '"formats":[{"type":"json"' in body
    assert '"prompt":"Extract company info"' in body
    assert '"schema":{' in body
    assert response.provider == "firecrawl"
    assert response.mode == "structured"
    assert response.pages == []
    assert response.structured_data == {"company": {"name": "Firecrawl", "supports_sso": True}}


@pytest.mark.asyncio
async def test_firecrawl_structured_extract_requires_schema_or_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")

    provider = FirecrawlProvider()
    with pytest.raises(ProviderError) as exc_info:
        await provider.extract(ExtractRequest(urls=["https://example.com"], provider="firecrawl", mode="structured"))

    assert exc_info.value.error_type == "invalid_request"
    assert exc_info.value.provider == "firecrawl"
