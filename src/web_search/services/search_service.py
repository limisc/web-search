from __future__ import annotations

import time

from web_search.models.requests import SearchRequest
from web_search.models.responses import SearchResponse, apply_route_metadata
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
        decision = self.router.plan(request)
        mode = self.planner.mode_for(request)
        decision_details = {**decision.details(), "mode": mode}

        chosen_provider_name: str | None = None
        last_error: ProviderError | None = None
        for provider_name in decision.providers:
            if not is_search_provider_available(provider_name):
                if request.provider == provider_name:
                    get_search_provider(provider_name)
                continue
            chosen_provider_name = provider_name
            provider = get_search_provider(provider_name)
            try:
                response = await provider.search(request)
                response.meta.cached = False
                apply_route_metadata(
                    response.meta,
                    route=f"{decision.route}:{mode}",
                    capability=decision.capability,
                    provider_override_applied=decision.provider_override_applied,
                    provider_name=provider_name,
                )
                response.meta.verification_level = request.verification_level
                response.meta.latency_ms = int((time.perf_counter() - started) * 1000)
                _SEARCH_CACHE.set(cache_key, response.model_copy(deep=True))
                return response
            except ProviderError as exc:
                last_error = exc.with_details(**decision_details, attempted_provider=provider_name)
                if not decision.allows_fallback:
                    raise last_error

        if last_error is not None:
            raise last_error

        raise ProviderError(
            f"No available providers for intent {request.intent}",
            provider=chosen_provider_name or "router",
            error_type="provider_not_available",
            details={"intent": request.intent, **decision_details},
        )


def clear_search_cache() -> None:
    _SEARCH_CACHE.clear()
