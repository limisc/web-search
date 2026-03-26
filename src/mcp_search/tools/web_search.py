from __future__ import annotations

from fastmcp.exceptions import ToolError, ValidationError as MCPValidationError
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
    debug: bool = False,
) -> dict:
    """Search the web using the selected provider.

    Args:
        query: Search query text.
        provider: Search provider name. Only `tavily` is supported right now.
        max_results: Number of results to return, between 1 and 10.
        topic: Search topic. Use `general` for broad web search or `news` for fresh news.
        time_range: Optional freshness filter: `day`, `week`, `month`, or `year`.
        include_domains: Optional allowlist of domains.
        exclude_domains: Optional denylist of domains.
        search_depth: `basic` or `advanced` Tavily search mode.
        include_answer: Whether provider summary answer should be requested.
        include_raw_content: Whether full page content should be included when available.
        debug: Include provider-specific raw payloads in results.
    """
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
            debug=debug,
        )
        response = await SearchService().run(request)
        return response.model_dump(mode="json")
    except ValidationError as exc:
        raise MCPValidationError(str(exc)) from exc
    except ProviderError as exc:
        raise ToolError(f"[{exc.error_type}] {exc}") from exc
