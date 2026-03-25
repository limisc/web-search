from __future__ import annotations

from mcp_search.models.requests import SearchRequest
from mcp_search.models.responses import SearchResponse
from mcp_search.providers.tavily import TavilyProvider


class SearchService:
    def __init__(self) -> None:
        self.provider = TavilyProvider()

    async def run(self, request: SearchRequest) -> SearchResponse:
        return await self.provider.search(request)
