from __future__ import annotations

from pydantic import ValidationError

from mcp_search.models.requests import ExtractRequest
from mcp_search.server import mcp
from mcp_search.services.extract_service import ExtractService
from mcp_search.utils.errors import ProviderError


@mcp.tool
async def web_extract(
    urls: list[str],
    provider: str = "tavily",
    extract_depth: str = "basic",
    query: str | None = None,
    max_chunks: int | None = None,
    format: str = "markdown",
) -> dict:
    """Extract content from known URLs and return normalized page payloads."""
    try:
        request = ExtractRequest(
            urls=urls,
            provider=provider,
            extract_depth=extract_depth,
            query=query,
            max_chunks=max_chunks,
            format=format,
        )
        response = await ExtractService().run(request)
        return response.model_dump(mode="json")
    except ValidationError as exc:
        return {
            "error": {
                "type": "validation_error",
                "message": str(exc),
                "provider": provider,
            }
        }
    except ProviderError as exc:
        return {
            "error": {
                "type": exc.error_type,
                "message": str(exc),
                "provider": exc.provider,
            }
        }
