from __future__ import annotations

from web_search.models.requests import ExtractRequest
from web_search.models.responses import CacheState, ExtractResponse, ExtractedPage, ResponseMeta, apply_route_metadata
from web_search.models.routing import ExtractRouteDecision
from web_search.providers import get_extract_provider, is_extract_provider_available
from web_search.services.extract_router import ExtractRouter
from web_search.utils.content_cache import ContentCache, cacheable_extract_request, derive_page_for_request
from web_search.utils.errors import ProviderError

_CONTENT_CACHE: ContentCache | None = None


def _get_content_cache() -> ContentCache:
    global _CONTENT_CACHE
    if _CONTENT_CACHE is None:
        _CONTENT_CACHE = ContentCache()
    return _CONTENT_CACHE


def _cached_response_meta(
    *,
    decision: ExtractRouteDecision,
    provider_name: str,
    cache_state: CacheState,
) -> ResponseMeta:
    meta = ResponseMeta(
        latency_ms=0,
        cached=cache_state in {"fresh", "stale"},
        cache_state=cache_state,
    )
    apply_route_metadata(
        meta,
        route=decision.route,
        capability=decision.capability,
        provider_override_applied=decision.provider_override_applied,
        provider_name=provider_name,
    )
    return meta


class ExtractService:
    def __init__(self) -> None:
        self.router = ExtractRouter()

    async def run(self, request: ExtractRequest) -> ExtractResponse:
        decision = self.router.plan(request)
        decision_details = decision.details()

        if request.mode == "structured" and not decision.providers:
            raise ProviderError(
                "Structured extract is not implemented yet",
                provider="router",
                error_type="provider_not_implemented",
                details={"mode": request.mode, **decision_details},
            )

        if cacheable_extract_request(request) and len(request.urls) == 1:
            cached_response = await self._run_with_content_cache(request, decision)
            if cached_response is not None:
                return cached_response

        last_error: ProviderError | None = None
        for provider_name in decision.providers:
            if not is_extract_provider_available(provider_name):
                if request.provider == provider_name:
                    get_extract_provider(provider_name)
                continue
            provider = get_extract_provider(provider_name)
            try:
                response = await provider.extract(request)
                apply_route_metadata(
                    response.meta,
                    route=decision.route,
                    capability=decision.capability,
                    provider_override_applied=decision.provider_override_applied,
                    provider_name=provider_name,
                )
                return response
            except ProviderError as exc:
                last_error = exc.with_details(**decision_details, attempted_provider=provider_name)
                if not decision.allows_fallback:
                    raise last_error

        if last_error is not None:
            raise last_error

        raise ProviderError(
            "No available providers for extract request",
            provider="router",
            error_type="provider_not_available",
            details={"mode": request.mode, **decision_details},
        )

    async def _run_with_content_cache(
        self,
        request: ExtractRequest,
        decision: ExtractRouteDecision,
    ) -> ExtractResponse | None:
        last_error: ProviderError | None = None
        url = str(request.urls[0])
        decision_details = decision.details()

        for provider_name in decision.providers:
            if not is_extract_provider_available(provider_name):
                if request.provider == provider_name:
                    get_extract_provider(provider_name)
                continue
            provider = get_extract_provider(provider_name)

            async def load_page() -> ExtractedPage:
                provider_request = request.model_copy(
                    update={
                        "provider": provider_name,
                        "query": None,
                        "max_chunks": None,
                        "format": "markdown",
                    }
                )
                provider_response = await provider.extract(provider_request)
                if not provider_response.pages:
                    raise ProviderError(
                        "Provider returned no pages for extract request",
                        provider=provider_name,
                        error_type="provider_unavailable",
                    )
                return provider_response.pages[0]

            try:
                lookup = await _get_content_cache().get_or_create(
                    provider=provider_name,
                    url=url,
                    loader=load_page,
                )
                if lookup.page is None:
                    continue
                page = derive_page_for_request(lookup.page, request)
                return ExtractResponse(
                    provider=provider_name,
                    mode=request.mode,
                    pages=[page],
                    meta=_cached_response_meta(
                        decision=decision,
                        provider_name=provider_name,
                        cache_state=lookup.state,
                    ),
                )
            except ProviderError as exc:
                last_error = exc.with_details(**decision_details, attempted_provider=provider_name)
                if not decision.allows_fallback:
                    raise last_error

        if last_error is not None:
            raise last_error
        return None


def clear_extract_cache() -> None:
    global _CONTENT_CACHE
    if _CONTENT_CACHE is not None:
        _CONTENT_CACHE.clear()
    _CONTENT_CACHE = None
