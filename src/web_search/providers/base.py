from __future__ import annotations

from typing import Protocol

from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.models.responses import ExtractResponse, SearchResponse


class WebSearchProvider(Protocol):
    async def search(self, request: SearchRequest) -> SearchResponse: ...


class WebExtractProvider(Protocol):
    async def extract(self, request: ExtractRequest) -> ExtractResponse: ...


class SearchProvider(WebSearchProvider, WebExtractProvider, Protocol):
    """Combined provider protocol for providers that support both search and extract."""
