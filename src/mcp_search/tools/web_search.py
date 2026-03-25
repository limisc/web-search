from __future__ import annotations

from pydantic import ValidationError

from mcp_search.models.requests import SearchRequest
from mcp_search.server import mcp
from mcp_search.services.search_service import SearchService
from mcp_search.utils.errors import ProviderError


@mcp.tool
async def web_search(
    query: str,
    provider: str = "tavily",
    max_results: int = 5,
    topic: str = "general",
    time_range: str | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    search_depth: str = "basic",
    include_answer: bool = True,
    include_raw_content: bool = False,
) -> dict:
    """Search the web and return normalized results with citations."""
    try:
        request = SearchRequest(
            query=query,
            provider=provider,
            max_results=max_results,
            topic=topic,
            time_range=time_range,
            include_domains=include_domains or [],
            exclude_domains=exclude_domains or [],
            search_depth=search_depth,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
        )
        response = await SearchService().run(request)
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
