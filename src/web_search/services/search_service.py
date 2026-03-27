from __future__ import annotations

from web_search.models.requests import SearchRequest
from web_search.models.responses import SearchResponse
from web_search.providers import get_provider


class SearchService:
    async def run(self, request: SearchRequest) -> SearchResponse:
        provider = get_provider(request.provider)
        return await provider.search(request)
