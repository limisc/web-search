from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from web_search.config import get_settings
from web_search.logging import get_logger
from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.models.responses import Citation, ExtractResponse, ResponseMeta, SearchHit, SearchResponse
from web_search.utils.errors import ProviderError


class BraveProvider:
    name = "brave"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger(__name__)

    async def search(self, request: SearchRequest) -> SearchResponse:
        self._ensure_configured()
        started = time.perf_counter()
        payload = self._search_payload_for(request)

        self.logger.info("provider_search_started provider=%s query=%s", self.name, request.query)
        data = await self._request_search(payload)
        latency_ms = int((time.perf_counter() - started) * 1000)

        results = [
            SearchHit(
                title=item.get("title") or item.get("url") or "Untitled",
                url=item["url"],
                snippet=self._snippet_for(item),
                content=self._content_for(item, request),
                score=None,
                published_at=self._normalize_published_date(item.get("age") or item.get("page_age")),
                source_type=item.get("type") or "web",
                provider=self.name,
                raw=item if request.debug else None,
            )
            for item in self._web_results(data)
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
            "Provider not implemented yet: brave extract",
            provider=self.name,
            error_type="provider_not_implemented",
            details={"mode": request.mode},
        )

    async def _request_search(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._should_use_post(payload):
            return await self._request("POST", "/web/search", json_body=payload)
        return await self._request("GET", "/web/search", params=payload)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.settings.brave_search_api_key or "",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        base_url = self.settings.brave_base_url.rstrip("/")
        last_error: Exception | None = None
        last_error_type = "provider_error"
        timeout = httpx.Timeout(self.settings.request_timeout_seconds)

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, self.settings.retry_max_attempts + 1):
                try:
                    response = await client.request(
                        method,
                        f"{base_url}{path}",
                        params=params,
                        json=json_body,
                        headers=headers,
                    )
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
                            "Brave Search rate limit exceeded",
                            provider=self.name,
                            error_type="budget_exceeded",
                            details={
                                "status_code": status,
                                "attempt": attempt,
                                "retry_after_seconds": exc.response.headers.get("X-RateLimit-Reset"),
                            },
                        ) from exc
                    if status in {502, 503, 504}:
                        last_error = exc
                        last_error_type = "provider_unavailable"
                    else:
                        raise ProviderError(
                            f"Brave Search returned HTTP {status}",
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
            f"Brave Search request failed: {last_error}",
            provider=self.name,
            error_type=last_error_type,
            details={"path": path, "method": method, "attempts": self.settings.retry_max_attempts},
        ) from last_error

    def _ensure_configured(self) -> None:
        if not self.settings.brave_search_api_key:
            self.logger.error("provider_not_configured provider=%s missing_env=BRAVE_SEARCH_API_KEY", self.name)
            raise ProviderError(
                "BRAVE_SEARCH_API_KEY is not configured",
                provider=self.name,
                error_type="provider_not_configured",
            )

    def _search_payload_for(self, request: SearchRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "q": self._query_for(request),
            "count": request.max_results,
            "result_filter": "web",
        }
        preferences = request.preferences
        brave_options = request.provider_options.brave

        if preferences.country:
            payload["country"] = preferences.country
        if preferences.search_lang:
            payload["search_lang"] = preferences.search_lang
        if preferences.ui_lang:
            payload["ui_lang"] = preferences.ui_lang
        if preferences.safesearch:
            payload["safesearch"] = preferences.safesearch
        if preferences.spellcheck is not None:
            payload["spellcheck"] = preferences.spellcheck
        if brave_options and brave_options.goggles:
            payload["goggles"] = brave_options.goggles
        freshness = self._freshness_for(request)
        if freshness:
            payload["freshness"] = freshness
        if request.extraction or request.verification_level in {"medium", "high"}:
            payload["extra_snippets"] = True
        return payload

    @staticmethod
    def _should_use_post(payload: dict[str, Any]) -> bool:
        goggles = payload.get("goggles")
        if isinstance(goggles, list) and len(goggles) > 1:
            return True
        query = payload.get("q")
        if isinstance(query, str) and len(query) > 400:
            return True
        if isinstance(goggles, list):
            total_goggles_length = sum(len(item) for item in goggles if isinstance(item, str))
            if total_goggles_length > 400:
                return True
        return False

    @staticmethod
    def _query_for(request: SearchRequest) -> str:
        query = request.query
        if request.include_domains:
            include_clause = " OR ".join(f"site:{domain}" for domain in request.include_domains)
            query = f"{query} {include_clause}"
        if request.exclude_domains:
            exclude_clause = " ".join(f"NOT site:{domain}" for domain in request.exclude_domains)
            query = f"{query} {exclude_clause}"
        return query.strip()

    @staticmethod
    def _freshness_for(request: SearchRequest) -> str | None:
        freshness_map = {
            "day": "pd",
            "week": "pw",
            "month": "pm",
            "year": "py",
        }
        return freshness_map.get(request.freshness or "")

    @staticmethod
    def _web_results(data: dict[str, Any]) -> list[dict[str, Any]]:
        web = data.get("web")
        if isinstance(web, dict):
            results = web.get("results")
            if isinstance(results, list):
                return [item for item in results if isinstance(item, dict)]
        results = data.get("results")
        if isinstance(results, list):
            return [item for item in results if isinstance(item, dict)]
        return []

    @staticmethod
    def _answer_for(data: dict[str, Any]) -> str | None:
        summarizer = data.get("summarizer")
        if isinstance(summarizer, dict):
            for key in ("text", "summary"):
                value = summarizer.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    @staticmethod
    def _snippet_for(item: dict[str, Any]) -> str | None:
        description = item.get("description")
        if isinstance(description, str) and description.strip():
            return description.strip()
        extra_snippets = BraveProvider._extra_snippets_for(item)
        if extra_snippets:
            return extra_snippets[0]
        return None

    @staticmethod
    def _content_for(item: dict[str, Any], request: SearchRequest) -> str | None:
        if not request.extraction:
            return None
        extra_snippets = BraveProvider._extra_snippets_for(item)
        if not extra_snippets:
            return None
        return "\n\n".join(extra_snippets)

    @staticmethod
    def _extra_snippets_for(item: dict[str, Any]) -> list[str]:
        extra_snippets = item.get("extra_snippets")
        if not isinstance(extra_snippets, list):
            return []
        seen: set[str] = set()
        normalized: list[str] = []
        for snippet in extra_snippets:
            if not isinstance(snippet, str):
                continue
            cleaned = snippet.strip()
            if cleaned and cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)
        return normalized

    @staticmethod
    def _normalize_published_date(value: Any) -> str | None:
        candidate: str | None = None
        if isinstance(value, str):
            candidate = value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    candidate = item
                    if "T" in item or "-" in item:
                        break
        if not candidate:
            return None

        try:
            if candidate.endswith("Z"):
                dt = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            return candidate
