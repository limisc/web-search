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

_SUPPORTED_LANGUAGES = {"ar", "de", "en", "es", "fr", "he", "it", "nl", "no", "pt", "ru", "sv", "ud", "zh"}


class NewsApiProvider:
    name = "newsapi"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger(__name__)

    async def search(self, request: SearchRequest) -> SearchResponse:
        self._ensure_configured()
        if len(request.query) > 500:
            raise ProviderError(
                "NewsAPI query exceeds the 500 character limit",
                provider=self.name,
                error_type="invalid_request",
            )

        started = time.perf_counter()
        params = self._everything_params_for(request)

        self.logger.info("provider_search_started provider=%s query=%s", self.name, request.query)
        data = await self._get("/everything", params)
        latency_ms = int((time.perf_counter() - started) * 1000)

        results = [
            SearchHit(
                title=item.get("title") or item.get("url") or "Untitled",
                url=item["url"],
                snippet=self._snippet_for(item),
                content=item.get("content") if request.extraction else None,
                score=None,
                published_at=self._normalize_published_date(item.get("publishedAt")),
                source_type="news",
                provider=self.name,
                raw=item if request.debug else None,
            )
            for item in self._articles(data)
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
            answer=None,
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
            "Provider not implemented yet: newsapi extract",
            provider=self.name,
            error_type="provider_not_implemented",
            details={"mode": request.mode},
        )

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {"X-Api-Key": self.settings.newsapi_api_key or ""}
        base_url = self.settings.newsapi_base_url.rstrip("/")
        last_error: Exception | None = None
        last_error_type = "provider_error"
        timeout = httpx.Timeout(self.settings.request_timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, self.settings.retry_max_attempts + 1):
                try:
                    response = await client.get(f"{base_url}{path}", params=params, headers=headers)
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
                    payload = self._error_payload(exc.response)
                    status = exc.response.status_code
                    code = payload.get("code")
                    message = payload.get("message") or f"NewsAPI returned HTTP {status}"
                    if status == 429 or code in {"rateLimited", "apiKeyExhausted"}:
                        raise ProviderError(
                            f"NewsAPI rate limit exceeded: {message}",
                            provider=self.name,
                            error_type="budget_exceeded",
                            details={"status_code": status, "attempt": attempt, "code": code},
                        ) from exc
                    if status == 401 or code in {"apiKeyDisabled", "apiKeyInvalid", "apiKeyMissing"}:
                        raise ProviderError(
                            message,
                            provider=self.name,
                            error_type="provider_not_configured",
                            details={"status_code": status, "attempt": attempt, "code": code},
                        ) from exc
                    if status == 400 or code in {"parameterInvalid", "parametersMissing", "sourcesTooMany", "sourceDoesNotExist"}:
                        raise ProviderError(
                            message,
                            provider=self.name,
                            error_type="invalid_request",
                            details={"status_code": status, "attempt": attempt, "code": code},
                        ) from exc
                    if status in {500, 502, 503, 504} or code == "unexpectedError":
                        last_error = exc
                        last_error_type = "provider_unavailable"
                    else:
                        raise ProviderError(
                            message,
                            provider=self.name,
                            error_type="provider_http_error",
                            details={"status_code": status, "attempt": attempt, "code": code},
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
            f"NewsAPI request failed: {last_error}",
            provider=self.name,
            error_type=last_error_type,
            details={"path": path, "attempts": self.settings.retry_max_attempts},
        ) from last_error

    def _ensure_configured(self) -> None:
        if not self.settings.newsapi_api_key:
            self.logger.error("provider_not_configured provider=%s missing_env=NEWSAPI_API_KEY", self.name)
            raise ProviderError(
                "NEWSAPI_API_KEY is not configured",
                provider=self.name,
                error_type="provider_not_configured",
            )

    def _everything_params_for(self, request: SearchRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "q": request.query,
            "pageSize": request.max_results,
            "page": 1,
            "sortBy": "publishedAt" if request.intent == "fresh" or request.freshness else "relevancy",
        }
        language = self._language_for(request)
        if language:
            params["language"] = language
        if request.include_domains:
            params["domains"] = ",".join(request.include_domains)
        if request.exclude_domains:
            params["excludeDomains"] = ",".join(request.exclude_domains)
        start_published_at = self._start_published_at_for(request)
        if start_published_at:
            params["from"] = start_published_at
        return params

    @staticmethod
    def _language_for(request: SearchRequest) -> str | None:
        search_lang = request.preferences.search_lang
        if not search_lang:
            return None
        primary = search_lang.split("-", 1)[0].lower()
        if primary in _SUPPORTED_LANGUAGES:
            return primary
        return None

    @staticmethod
    def _start_published_at_for(request: SearchRequest) -> str | None:
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
    def _articles(data: dict[str, Any]) -> list[dict[str, Any]]:
        articles = data.get("articles")
        if isinstance(articles, list):
            return [item for item in articles if isinstance(item, dict)]
        return []

    @staticmethod
    def _snippet_for(item: dict[str, Any]) -> str | None:
        description = item.get("description")
        if isinstance(description, str) and description.strip():
            return description.strip()
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
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

    @staticmethod
    def _error_payload(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        if isinstance(payload, dict):
            return payload
        return {}
