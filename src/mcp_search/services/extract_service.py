from __future__ import annotations

from mcp_search.models.requests import ExtractRequest
from mcp_search.models.responses import ExtractResponse
from mcp_search.providers.tavily import TavilyProvider


class ExtractService:
    def __init__(self) -> None:
        self.provider = TavilyProvider()

    async def run(self, request: ExtractRequest) -> ExtractResponse:
        return await self.provider.extract(request)
