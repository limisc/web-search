from __future__ import annotations

from typing import Protocol

from mcp_search.models.requests import ExtractRequest, SearchRequest
from mcp_search.models.responses import ExtractResponse, SearchResponse


class SearchProvider(Protocol):
    async def search(self, request: SearchRequest) -> SearchResponse: ...

    async def extract(self, request: ExtractRequest) -> ExtractResponse: ...
