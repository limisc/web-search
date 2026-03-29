from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from web_search.config import get_settings
from web_search.logging import get_logger
from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.models.responses import (
    Citation,
    ExtractResponse,
    ExtractedPage,
    ResponseMeta,
    SearchHit,
    SearchResponse,
)
from web_search.utils.errors import ProviderError


class TavilyProvider:
    name = "tavily"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger(__name__)

    async def search(self, request: SearchRequest) -> SearchResponse:
        self._ensure_configured()
        started = time.perf_counter()
        body: dict[str, Any] = {
            "query": request.query,
            "max_results": request.max_results,
            "search_depth": self._search_depth_for(request),
            "topic": self._topic_for(request),
            "include_answer": self._include_answer_for(request),
            "include_raw_content": request.extraction,
        }
        if request.freshness:
            body["time_range"] = request.freshness
        if request.include_domains:
            body["include_domains"] = request.include_domains
        if request.exclude_domains:
            body["exclude_domains"] = request.exclude_domains

        self.logger.info("provider_search_started provider=%s query=%s", self.name, request.query)
        data = await self._post("/search", body)
        latency_ms = int((time.perf_counter() - started) * 1000)

        results = [
            SearchHit(
                title=item.get("title") or item.get("url") or "Untitled",
                url=item["url"],
                snippet=item.get("content"),
                content=item.get("raw_content") if request.extraction else None,
                score=item.get("score"),
                published_at=self._normalize_published_date(item.get("published_date")),
                provider=self.name,
                raw=item if request.debug else None,
            )
            for item in data.get("results", [])
            if item.get("url")
        ]
        citations = [Citation(title=result.title, url=result.url, provider=self.name) for result in results]
        self.logger.info(
            "provider_search_finished provider=%s latency_ms=%s result_count=%s",
            self.name,
            latency_ms,
            len(results),
        )

        return SearchResponse(
            query=request.query,
            intent=request.intent,
            provider=self.name,
            answer=data.get("answer"),
            results=results,
            citations=citations,
            meta=ResponseMeta(
                latency_ms=latency_ms,
                providers_used=[self.name],
                verification_level=request.verification_level,
            ),
        )

    async def extract(self, request: ExtractRequest) -> ExtractResponse:
        self._ensure_configured()
        started = time.perf_counter()
        body: dict[str, Any] = {
            "urls": [str(url) for url in request.urls],
            "extract_depth": "advanced" if request.mode == "structured" else "basic",
            "format": request.format,
        }
        if request.query:
            body["query"] = request.query
        if request.max_chunks:
            body["chunks_per_source"] = request.max_chunks

        self.logger.info("provider_extract_started provider=%s url_count=%s", self.name, len(request.urls))
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
                raw=item if request.debug else None,
            )
            for item in data.get("results", [])
            if item.get("url")
        ]
        self.logger.info(
            "provider_extract_finished provider=%s latency_ms=%s page_count=%s",
            self.name,
            latency_ms,
            len(pages),
        )

        return ExtractResponse(
            provider=self.name,
            mode=request.mode,
            pages=pages,
            meta=ResponseMeta(latency_ms=latency_ms, providers_used=[self.name]),
        )

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.tavily_api_key}",
        }
        base_url = self.settings.tavily_base_url.rstrip("/")
        last_error: Exception | None = None
        last_error_type = "provider_error"
        timeout = httpx.Timeout(self.settings.request_timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, self.settings.retry_max_attempts + 1):
                try:
                    response = await client.post(f"{base_url}{path}", json=body, headers=headers)
                    response.raise_for_status()
                    self.logger.info(
                        "provider_request_succeeded provider=%s path=%s status_code=%s attempt=%s",
                        self.name,
                        path,
                        response.status_code,
                        attempt,
                    )
                    return response.json()
                except httpx.TimeoutException as exc:
                    last_error = exc
                    last_error_type = "provider_timeout"
                except httpx.ConnectError as exc:
                    last_error = exc
                    last_error_type = "provider_connection_error"
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    if status == 429 or status in {502, 503, 504}:
                        last_error = exc
                        last_error_type = "provider_unavailable"
                    else:
                        raise ProviderError(
                            f"Tavily returned HTTP {status}",
                            provider=self.name,
                            error_type="provider_http_error",
                            details={"status_code": status, "attempt": attempt},
                        ) from exc
                except httpx.HTTPError as exc:
                    last_error = exc
                    last_error_type = "provider_connection_error"

                self.logger.warning(
                    "provider_request_retry provider=%s path=%s attempt=%s error_type=%s error=%s",
                    self.name,
                    path,
                    attempt,
                    last_error_type,
                    last_error,
                )
                if attempt < self.settings.retry_max_attempts:
                    await asyncio.sleep(0.25 * attempt)

        self.logger.error(
            "provider_request_failed provider=%s path=%s error_type=%s attempts=%s error=%s",
            self.name,
            path,
            last_error_type,
            self.settings.retry_max_attempts,
            last_error,
        )
        raise ProviderError(
            f"Tavily request failed: {last_error}",
            provider=self.name,
            error_type=last_error_type,
            details={"path": path, "attempts": self.settings.retry_max_attempts},
        ) from last_error

    def _ensure_configured(self) -> None:
        if not self.settings.tavily_api_key:
            self.logger.error("provider_not_configured provider=%s missing_env=TAVILY_API_KEY", self.name)
            raise ProviderError(
                "TAVILY_API_KEY is not configured",
                provider=self.name,
                error_type="provider_not_configured",
            )

    @staticmethod
    def _topic_for(request: SearchRequest) -> str:
        return "news" if request.intent == "fresh" else "general"

    @staticmethod
    def _search_depth_for(request: SearchRequest) -> str:
        if request.verification_level in {"medium", "high"} or request.extraction:
            return "advanced"
        return "basic"

    @staticmethod
    def _include_answer_for(request: SearchRequest) -> bool:
        return request.intent != "social"

    @staticmethod
    def _normalize_published_date(value: str | None) -> str | None:
        if not value:
            return None
        try:
            if value.endswith("Z"):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            return value
