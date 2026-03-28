from __future__ import annotations

from fastmcp.exceptions import ToolError, ValidationError as MCPValidationError
from pydantic import ValidationError

from web_search.models.requests import SearchRequest
from web_search.server import mcp
from web_search.services.search_service import SearchService
from web_search.utils.errors import ProviderError


@mcp.tool
async def web_search(
    query: str,
    intent: str = "general",
    freshness: str | None = None,
    domains: list[str] | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    max_results: int = 5,
    verification_level: str = "none",
    extraction: bool = False,
    debug: bool = False,
    provider: str | None = None,
) -> dict:
    """Search the web using the orchestrated provider router.

    Args:
        query: Search query text.
        intent: Search intent: `docs`, `fresh`, `general`, or `social`.
        freshness: Optional freshness filter: `day`, `week`, `month`, `year`, or `any`.
        domains: Optional shorthand domain allowlist.
        include_domains: Optional allowlist of domains.
        exclude_domains: Optional denylist of domains.
        max_results: Number of results to return, between 1 and 10.
        verification_level: `none`, `light`, `medium`, or `high`.
        extraction: Whether content extraction should be requested as part of search.
        debug: Include provider-specific raw payloads in results.
        provider: Optional provider override for testing or forced routing.
    """
    try:
        request = SearchRequest(
            query=query,
            intent=intent,
            freshness=freshness,
            domains=domains or [],
            include_domains=include_domains or [],
            exclude_domains=exclude_domains or [],
            max_results=max_results,
            verification_level=verification_level,
            extraction=extraction,
            debug=debug,
            provider=provider,
        )
        response = await SearchService().run(request)
        return response.model_dump(mode="json")
    except ValidationError as exc:
        raise MCPValidationError(str(exc)) from exc
    except ProviderError as exc:
        raise ToolError(f"[{exc.error_type}] {exc}") from exc
