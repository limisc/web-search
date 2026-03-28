from __future__ import annotations

from web_search.models.requests import ExtractRequest
from web_search.models.responses import ExtractResponse
from web_search.providers import get_provider


class ExtractService:
    async def run(self, request: ExtractRequest) -> ExtractResponse:
        provider_name = request.provider or "tavily"
        provider = get_provider(provider_name)
        return await provider.extract(request)
