from __future__ import annotations

from mcp_search.models.requests import ExtractRequest
from mcp_search.models.responses import ExtractResponse
from mcp_search.providers import get_provider


class ExtractService:
    async def run(self, request: ExtractRequest) -> ExtractResponse:
        provider = get_provider(request.provider)
        return await provider.extract(request)
