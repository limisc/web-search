from __future__ import annotations

import time
from typing import Any

import httpx

from mcp_search.config import get_settings
from mcp_search.models.requests import ExtractRequest, SearchRequest
from mcp_search.models.responses import (
    Citation,
    ExtractResponse,
    ExtractedPage,
    ResponseMeta,
    SearchHit,
    SearchResponse,
)
from mcp_search.utils.errors import ProviderError


class TavilyProvider:
    name = "tavily"

    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.tavily_api_key:
            raise ProviderError(
                "TAVILY_API_KEY is not configured",
                provider=self.name,
                error_type="provider_not_configured",
            )

    async def search(self, request: SearchRequest) -> SearchResponse:
        started = time.perf_counter()
        body: dict[str, Any] = {
            "query": request.query,
            "max_results": request.max_results,
            "search_depth": request.search_depth,
            "topic": request.topic,
            "include_answer": request.include_answer,
            "include_raw_content": request.include_raw_content,
        }
        if request.time_range:
            body["time_range"] = request.time_range
        if request.include_domains:
            body["include_domains"] = request.include_domains
        if request.exclude_domains:
            body["exclude_domains"] = request.exclude_domains

        data = await self._post("/search", body)
        latency_ms = int((time.perf_counter() - started) * 1000)

        results = [
            SearchHit(
                title=item.get("title") or item.get("url") or "Untitled",
                url=item["url"],
                snippet=item.get("content"),
                content=item.get("raw_content") if request.include_raw_content else None,
                score=item.get("score"),
                published_at=item.get("published_date"),
                provider=self.name,
                raw=item,
            )
            for item in data.get("results", [])
            if item.get("url")
        ]
        citations = [Citation(title=result.title, url=result.url, provider=self.name) for result in results]

        return SearchResponse(
            query=request.query,
            provider=self.name,
            answer=data.get("answer"),
            results=results,
            citations=citations,
            meta=ResponseMeta(latency_ms=latency_ms),
        )

    async def extract(self, request: ExtractRequest) -> ExtractResponse:
        started = time.perf_counter()
        body: dict[str, Any] = {
            "urls": [str(url) for url in request.urls],
            "extract_depth": request.extract_depth,
            "format": request.format,
        }
        if request.query:
            body["query"] = request.query
        if request.max_chunks:
            body["chunks_per_source"] = request.max_chunks

        data = await self._post("/extract", body)
        latency_ms = int((time.perf_counter() - started) * 1000)

        pages = [
            ExtractedPage(
                url=item["url"],
                title=item.get("title"),
                content=item.get("raw_content"),
                excerpt=(item.get("raw_content") or "")[:280] or None,
                chunks=item.get("chunks") or [],
                provider=self.name,
                raw=item,
            )
            for item in data.get("results", [])
            if item.get("url")
        ]

        return ExtractResponse(
            provider=self.name,
            pages=pages,
            meta=ResponseMeta(latency_ms=latency_ms),
        )

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        timeout = httpx.Timeout(self.settings.request_timeout_seconds)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.tavily_api_key}",
        }
        base_url = self.settings.tavily_base_url.rstrip("/")
        last_error: Exception | None = None

        for _attempt in range(1, self.settings.retry_max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(f"{base_url}{path}", json=body, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in {502, 503, 504}:
                    last_error = exc
                    continue
                raise ProviderError(
                    f"Tavily returned HTTP {status}",
                    provider=self.name,
                    error_type="provider_http_error",
                ) from exc
            except httpx.HTTPError as exc:
                last_error = exc

        raise ProviderError(
            f"Tavily request failed: {last_error}",
            provider=self.name,
            error_type="provider_timeout",
        ) from last_error
