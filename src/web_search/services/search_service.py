from __future__ import annotations

import time

from web_search.models.requests import SearchRequest
from web_search.models.responses import SearchResponse
from web_search.providers import get_search_provider, is_search_provider_available
from web_search.services.planner import Planner
from web_search.services.router import Router
from web_search.utils.cache import TTLCache, make_cache_key
from web_search.utils.errors import ProviderError

_SEARCH_CACHE = TTLCache(ttl_seconds=300)


class SearchService:
    def __init__(self) -> None:
        self.router = Router()
        self.planner = Planner()

    async def run(self, request: SearchRequest) -> SearchResponse:
        cache_key = make_cache_key("search", request.model_dump(mode="json"))
        cached = _SEARCH_CACHE.get(cache_key)
        if cached is not None:
            cached_copy = cached.model_copy(deep=True)
            cached_copy.meta.cached = True
            return cached_copy

        started = time.perf_counter()
        plan = self.router.plan(request)
        mode = self.planner.mode_for(request)

        chosen_provider_name: str | None = None
        last_error: ProviderError | None = None
        for provider_name in plan.search_providers:
            if not is_search_provider_available(provider_name):
                if request.provider == provider_name:
                    get_search_provider(provider_name)
                continue
            chosen_provider_name = provider_name
            provider = get_search_provider(provider_name)
            try:
                response = await provider.search(request)
                response.meta.cached = False
                response.meta.route = f"{plan.route}:{mode}"
                response.meta.providers_used = [provider_name]
                response.meta.verification_level = request.verification_level
                response.meta.latency_ms = int((time.perf_counter() - started) * 1000)
                _SEARCH_CACHE.set(cache_key, response.model_copy(deep=True))
                return response
            except ProviderError as exc:
                last_error = exc
                if plan.route != "fallback_candidate":
                    raise

        if last_error is not None:
            raise last_error

        raise ProviderError(
            f"No available providers for intent {request.intent}",
            provider=chosen_provider_name or "router",
            error_type="provider_not_available",
            details={"intent": request.intent, "providers": list(plan.search_providers)},
        )


def clear_search_cache() -> None:
    _SEARCH_CACHE.clear()
