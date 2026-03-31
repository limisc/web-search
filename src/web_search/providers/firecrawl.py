from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import httpx

from web_search.config import get_settings
from web_search.logging import get_logger
from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.models.responses import ExtractResponse, ExtractedPage, ResponseMeta, SearchResponse
from web_search.utils.errors import ProviderError


class FirecrawlProvider:
    name = "firecrawl"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger(__name__)

    async def search(self, request: SearchRequest) -> SearchResponse:
        raise ProviderError(
            "Provider not implemented yet: firecrawl search",
            provider=self.name,
            error_type="provider_not_implemented",
            details={"intent": request.intent},
        )

    async def extract(self, request: ExtractRequest) -> ExtractResponse:
        if request.mode != "content":
            raise ProviderError(
                "Provider not implemented yet: firecrawl structured extract",
                provider=self.name,
                error_type="provider_not_implemented",
                details={"mode": request.mode},
            )
        self._ensure_configured()
        return await self._extract_content(request)

    async def _extract_content(self, request: ExtractRequest) -> ExtractResponse:
        started = time.perf_counter()
        pages: list[ExtractedPage] = []
        for url in request.urls:
            url_str = str(url)
            data = await self._request("POST", "/scrape", json_body=self._scrape_body_for(url_str, request))
            item = self._extract_page(data)
            if item is None:
                continue
            pages.append(
                ExtractedPage(
                    url=self._page_url_for(item, url_str),
                    title=self._title_for(item),
                    content=self._content_for(item, request),
                    excerpt=self._excerpt_for(item, request),
                    chunks=self._chunks_for(item, request),
                    provider=self.name,
                    raw=item if request.debug else None,
                )
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
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

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.firecrawl_api_key or ''}",
        }
        base_url = self.settings.firecrawl_base_url.rstrip("/")
        last_error: Exception | None = None
        last_error_type = "provider_error"
        timeout = httpx.Timeout(self.settings.request_timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, self.settings.retry_max_attempts + 1):
                try:
                    response = await client.request(method, f"{base_url}{path}", json=json_body, headers=headers)
                    response.raise_for_status()
                    self.logger.info(
                        "provider_request_succeeded provider=%s method=%s path=%s status_code=%s attempt=%s",
                        self.name,
                        method,
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
                    if status == 429:
                        raise ProviderError(
                            "Firecrawl rate limit exceeded",
                            provider=self.name,
                            error_type="budget_exceeded",
                            details={"status_code": status, "attempt": attempt},
                        ) from exc
                    if status in {502, 503, 504}:
                        last_error = exc
                        last_error_type = "provider_unavailable"
                    else:
                        raise ProviderError(
                            f"Firecrawl returned HTTP {status}",
                            provider=self.name,
                            error_type="provider_http_error",
                            details={"status_code": status, "attempt": attempt},
                        ) from exc
                except httpx.HTTPError as exc:
                    last_error = exc
                    last_error_type = "provider_connection_error"

                self.logger.warning(
                    "provider_request_retry provider=%s method=%s path=%s attempt=%s error_type=%s error=%s",
                    self.name,
                    method,
                    path,
                    attempt,
                    last_error_type,
                    last_error,
                )
                if attempt < self.settings.retry_max_attempts:
                    await asyncio.sleep(0.25 * attempt)

        self.logger.error(
            "provider_request_failed provider=%s method=%s path=%s error_type=%s attempts=%s error=%s",
            self.name,
            method,
            path,
            last_error_type,
            self.settings.retry_max_attempts,
            last_error,
        )
        raise ProviderError(
            f"Firecrawl request failed: {last_error}",
            provider=self.name,
            error_type=last_error_type,
            details={"path": path, "method": method, "attempts": self.settings.retry_max_attempts},
        ) from last_error

    def _ensure_configured(self) -> None:
        if not self.settings.firecrawl_api_key:
            self.logger.error("provider_not_configured provider=%s missing_env=FIRECRAWL_API_KEY", self.name)
            raise ProviderError(
                "FIRECRAWL_API_KEY is not configured",
                provider=self.name,
                error_type="provider_not_configured",
            )

    @staticmethod
    def _scrape_body_for(url: str, request: ExtractRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
        }
        return body

    @staticmethod
    def _extract_page(data: dict[str, Any]) -> dict[str, Any] | None:
        payload = data.get("data")
        if isinstance(payload, dict):
            return payload
        return None

    @staticmethod
    def _page_url_for(item: dict[str, Any], fallback_url: str) -> str:
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            for key in ("sourceURL", "url"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        value = item.get("url")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return fallback_url

    @staticmethod
    def _title_for(item: dict[str, Any]) -> str | None:
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            title = metadata.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
        return None

    @staticmethod
    def _content_for(item: dict[str, Any], request: ExtractRequest) -> str | None:
        markdown = item.get("markdown")
        if isinstance(markdown, str) and markdown.strip():
            content = markdown.strip()
            if request.format == "text":
                return FirecrawlProvider._plain_text_from_markdown(content)
            return content
        summary = item.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        return None

    @staticmethod
    def _excerpt_for(item: dict[str, Any], request: ExtractRequest) -> str | None:
        chunks = FirecrawlProvider._chunks_for(item, request)
        if chunks:
            return chunks[0][:280]
        content = FirecrawlProvider._content_for(item, request)
        if content:
            return content[:280]
        return None

    @staticmethod
    def _chunks_for(item: dict[str, Any], request: ExtractRequest) -> list[str]:
        markdown = item.get("markdown")
        if not isinstance(markdown, str) or not markdown.strip():
            return []

        paragraphs = [segment.strip() for segment in markdown.split("\n\n") if segment.strip()]
        if not paragraphs:
            return []
        normalized_paragraphs = [FirecrawlProvider._segment_for_format(segment, request) for segment in paragraphs]
        if request.query:
            ranked = sorted(
                normalized_paragraphs,
                key=lambda segment: FirecrawlProvider._query_score(segment, request.query or ""),
                reverse=True,
            )
        else:
            ranked = normalized_paragraphs

        if request.max_chunks:
            return ranked[: request.max_chunks]
        return []

    @staticmethod
    def _segment_for_format(segment: str, request: ExtractRequest) -> str:
        if request.format == "text":
            return FirecrawlProvider._plain_text_from_markdown(segment)
        return segment.strip()

    @staticmethod
    def _plain_text_from_markdown(markdown: str) -> str:
        text = markdown.strip()
        text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"^\s{0,3}(#{1,6}|>|[-*+])\s?", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
        text = text.replace("```", "")
        text = text.replace("`", "")
        text = re.sub(r"[*_~]", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _query_score(segment: str, query: str) -> tuple[int, int]:
        query_terms = [term for term in query.lower().split() if term]
        lowered = segment.lower()
        hits = sum(lowered.count(term) for term in query_terms)
        return (hits, -len(segment))
