from __future__ import annotations

from web_search.models.requests import ExtractRequest
from web_search.models.responses import ExtractResponse, ExtractedPage, ResponseMeta
from web_search.providers import get_extract_provider, is_extract_provider_available
from web_search.services.extract_router import ExtractProviderPlan, ExtractRouter
from web_search.utils.content_cache import ContentCache, cacheable_extract_request, derive_page_for_request
from web_search.utils.errors import ProviderError

_CONTENT_CACHE = ContentCache()


class ExtractService:
    def __init__(self) -> None:
        self.router = ExtractRouter()

    async def run(self, request: ExtractRequest) -> ExtractResponse:
        plan = self.router.plan(request)

        if request.mode == "structured" and not plan.providers:
            raise ProviderError(
                "Structured extract is not implemented yet",
                provider="router",
                error_type="provider_not_implemented",
                details={"mode": request.mode},
            )

        if cacheable_extract_request(request) and len(request.urls) == 1:
            cached_response = await self._run_with_content_cache(request, plan)
            if cached_response is not None:
                return cached_response

        last_error: ProviderError | None = None
        for provider_name in plan.providers:
            if not is_extract_provider_available(provider_name):
                if request.provider == provider_name:
                    get_extract_provider(provider_name)
                continue
            provider = get_extract_provider(provider_name)
            try:
                response = await provider.extract(request)
                response.meta.route = plan.route
                response.meta.providers_used = [provider_name]
                return response
            except ProviderError as exc:
                last_error = exc
                if plan.route != "fallback_candidate":
                    raise

        if last_error is not None:
            raise last_error

        raise ProviderError(
            "No available providers for extract request",
            provider="router",
            error_type="provider_not_available",
            details={"mode": request.mode, "providers": list(plan.providers)},
        )

    async def _run_with_content_cache(
        self,
        request: ExtractRequest,
        plan: ExtractProviderPlan,
    ) -> ExtractResponse | None:
        last_error: ProviderError | None = None
        url = str(request.urls[0])

        for provider_name in plan.providers:
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
                lookup = await _CONTENT_CACHE.get_or_create(
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
                    meta=ResponseMeta(
                        latency_ms=0,
                        cached=lookup.state in {"fresh", "stale"},
                        cache_state=lookup.state,
                        route=plan.route,
                        providers_used=[provider_name],
                    ),
                )
            except ProviderError as exc:
                last_error = exc
                if plan.route != "fallback_candidate":
                    raise

        if last_error is not None:
            raise last_error
        return None


def clear_extract_cache() -> None:
    _CONTENT_CACHE.clear()
