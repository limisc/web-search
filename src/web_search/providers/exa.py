from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from web_search.config import get_settings
from web_search.logging import get_logger
from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.models.responses import Citation, ExtractResponse, ResponseMeta, SearchHit, SearchResponse
from web_search.utils.errors import ProviderError


class ExaProvider:
    name = "exa"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger(__name__)

    async def search(self, request: SearchRequest) -> SearchResponse:
        self._ensure_configured()
        started = time.perf_counter()
        body = self._search_body_for(request)

        self.logger.info("provider_search_started provider=%s query=%s", self.name, request.query)
        data = await self._post("/search", body)
        latency_ms = int((time.perf_counter() - started) * 1000)

        results = [
            SearchHit(
                title=item.get("title") or item.get("url") or "Untitled",
                url=item["url"],
                snippet=self._snippet_for(item),
                content=self._content_for(item, request),
                score=None,
                published_at=self._normalize_published_date(item.get("publishedDate")),
                source_type="web",
                provider=self.name,
                raw=item if request.debug else None,
            )
            for item in self._results(data)
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
            answer=self._answer_for(data),
            results=results,
            citations=citations,
            meta=ResponseMeta(
                latency_ms=latency_ms,
                providers_used=[self.name],
                verification_level=request.verification_level,
            ),
        )

    async def extract(self, request: ExtractRequest) -> ExtractResponse:
        raise ProviderError(
            "Provider not implemented yet: exa extract",
            provider=self.name,
            error_type="provider_not_implemented",
            details={"mode": request.mode},
        )

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.settings.exa_api_key or "",
        }
        base_url = self.settings.exa_base_url.rstrip("/")
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
                    if status == 429:
                        raise ProviderError(
                            "Exa rate limit exceeded",
                            provider=self.name,
                            error_type="budget_exceeded",
                            details={"status_code": status, "attempt": attempt},
                        ) from exc
                    if status in {502, 503, 504}:
                        last_error = exc
                        last_error_type = "provider_unavailable"
                    else:
                        raise ProviderError(
                            f"Exa returned HTTP {status}",
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
            f"Exa request failed: {last_error}",
            provider=self.name,
            error_type=last_error_type,
            details={"path": path, "attempts": self.settings.retry_max_attempts},
        ) from last_error

    def _ensure_configured(self) -> None:
        if not self.settings.exa_api_key:
            self.logger.error("provider_not_configured provider=%s missing_env=EXA_API_KEY", self.name)
            raise ProviderError(
                "EXA_API_KEY is not configured",
                provider=self.name,
                error_type="provider_not_configured",
            )

    def _search_body_for(self, request: SearchRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "query": self._query_for(request),
            "type": "auto",
            "numResults": request.max_results,
            "contents": self._contents_for(request),
        }
        preferences = request.preferences

        if preferences.country:
            body["userLocation"] = preferences.country
        moderation = self._moderation_for(request)
        if moderation is not None:
            body["moderation"] = moderation
        if request.include_domains:
            body["includeDomains"] = request.include_domains
        if request.exclude_domains:
            body["excludeDomains"] = request.exclude_domains
        start_published_date = self._start_published_date_for(request)
        if start_published_date:
            body["startPublishedDate"] = start_published_date
        return body

    @staticmethod
    def _query_for(request: SearchRequest) -> str:
        if request.intent != "docs":
            return request.query

        normalized_query = request.query.lower()
        if any(marker in normalized_query for marker in ("official documentation", "official docs")):
            return request.query

        return f"{request.query} official documentation".strip()

    @staticmethod
    def _contents_for(request: SearchRequest) -> dict[str, Any]:
        contents: dict[str, Any] = {
            "highlights": {
                "maxCharacters": 2000,
                "query": request.query,
            }
        }
        if request.extraction:
            contents["text"] = {"maxCharacters": 12000}
        return contents

    @staticmethod
    def _moderation_for(request: SearchRequest) -> bool | None:
        if request.preferences.safesearch is None:
            return None
        return request.preferences.safesearch != "off"

    @staticmethod
    def _start_published_date_for(request: SearchRequest) -> str | None:
        freshness_days = {
            "day": 1,
            "week": 7,
            "month": 30,
            "year": 365,
        }
        days = freshness_days.get(request.freshness or "")
        if days is None:
            return None
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return cutoff.isoformat().replace("+00:00", "Z")

    @staticmethod
    def _results(data: dict[str, Any]) -> list[dict[str, Any]]:
        results = data.get("results")
        if isinstance(results, list):
            return [item for item in results if isinstance(item, dict)]
        return []

    @staticmethod
    def _answer_for(data: dict[str, Any]) -> str | None:
        output = data.get("output")
        if isinstance(output, dict):
            content = output.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
        return None

    @staticmethod
    def _snippet_for(item: dict[str, Any]) -> str | None:
        highlights = item.get("highlights")
        if isinstance(highlights, list):
            for highlight in highlights:
                if isinstance(highlight, str) and highlight.strip():
                    return highlight.strip()
        summary = item.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()[:400]
        return None

    @staticmethod
    def _content_for(item: dict[str, Any], request: SearchRequest) -> str | None:
        if not request.extraction:
            return None
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        highlights = item.get("highlights")
        if isinstance(highlights, list):
            normalized = [value.strip() for value in highlights if isinstance(value, str) and value.strip()]
            if normalized:
                return "\n\n".join(normalized)
        summary = item.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        return None

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
