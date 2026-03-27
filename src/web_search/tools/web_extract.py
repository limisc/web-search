from __future__ import annotations

from fastmcp.exceptions import ToolError, ValidationError as MCPValidationError
from pydantic import ValidationError

from web_search.models.requests import ExtractRequest
from web_search.server import mcp
from web_search.services.extract_service import ExtractService
from web_search.utils.errors import ProviderError


@mcp.tool
async def web_extract(
    urls: list[str],
    provider: str = "tavily",
    extract_depth: str = "basic",
    query: str | None = None,
    max_chunks: int | None = None,
    format: str = "markdown",
    debug: bool = False,
) -> dict:
    """Extract content from one or more known URLs.

    Args:
        urls: One or more absolute HTTP(S) URLs.
        provider: Extraction provider name. Only `tavily` is supported right now.
        extract_depth: `basic` or `advanced` extraction mode.
        query: Optional relevance query used by provider-side chunk ranking.
        max_chunks: Optional number of chunks to request when query is set.
        format: Output format, `markdown` or `text`.
        debug: Include provider-specific raw payloads in pages.
    """
    try:
        request = ExtractRequest(
            urls=urls,
            provider=provider,
            extract_depth=extract_depth,
            query=query,
            max_chunks=max_chunks,
            format=format,
            debug=debug,
        )
        response = await ExtractService().run(request)
        return response.model_dump(mode="json")
    except ValidationError as exc:
        raise MCPValidationError(str(exc)) from exc
    except ProviderError as exc:
        raise ToolError(f"[{exc.error_type}] {exc}") from exc
