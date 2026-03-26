from __future__ import annotations

from mcp_search.models.requests import SearchRequest
from mcp_search.models.responses import SearchResponse
from mcp_search.providers import get_provider


class SearchService:
    async def run(self, request: SearchRequest) -> SearchResponse:
        provider = get_provider(request.provider)
        return await provider.search(request)
