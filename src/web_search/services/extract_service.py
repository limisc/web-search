from __future__ import annotations

from web_search.models.requests import ExtractRequest
from web_search.models.responses import ExtractResponse
from web_search.providers import get_provider


class ExtractService:
    async def run(self, request: ExtractRequest) -> ExtractResponse:
        provider = get_provider(request.provider)
        return await provider.extract(request)
