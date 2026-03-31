from __future__ import annotations

from web_search.config import get_settings
from web_search.models.requests import ExtractRequest
from web_search.models.routing import ExtractRouteDecision, RouteKind


class ExtractRouter:
    def __init__(self) -> None:
        self.settings = get_settings()

    def plan(self, request: ExtractRequest) -> ExtractRouteDecision:
        if request.provider:
            return ExtractRouteDecision(
                route="provider_override",
                providers=(request.provider,),
                provider_override_applied=True,
                reason="explicit provider override",
                capability=self._capability_for(request),
            )

        if request.mode == "structured":
            return ExtractRouteDecision(
                route="single",
                providers=(),
                reason="structured extract has no default execution lane yet",
                capability="structured_extract",
            )

        providers = self._content_extract_providers(request)
        route: RouteKind = "fallback_candidate" if len(providers) > 1 else "single"
        return ExtractRouteDecision(
            route=route,
            providers=providers,
            reason="content extract uses configured provider order",
            capability="content_extract",
        )

    @staticmethod
    def _capability_for(request: ExtractRequest) -> str:
        if request.mode == "structured":
            return "structured_extract"
        return "content_extract"

    def _content_extract_providers(self, request: ExtractRequest) -> tuple[str, ...]:
        providers: list[str] = []
        prefers_exa = self.settings.exa_api_key and (request.query is not None or request.max_chunks is not None)

        if prefers_exa:
            providers.append("exa")
        if self.settings.tavily_api_key:
            providers.append("tavily")
        if self.settings.exa_api_key and "exa" not in providers:
            providers.append("exa")
        if providers:
            return tuple(providers)
        return ("tavily",)
