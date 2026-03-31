from __future__ import annotations

from web_search.config import get_settings
from web_search.models.requests import SearchRequest
from web_search.models.routing import RouteKind, SearchCapability, SearchRouteDecision


class Router:
    def __init__(self) -> None:
        self.settings = get_settings()

    def plan(self, request: SearchRequest) -> SearchRouteDecision:
        capability = self._capability_for(request)
        if request.provider:
            return SearchRouteDecision(
                route="provider_override",
                providers=(request.provider,),
                provider_override_applied=True,
                reason="explicit provider override",
                capability=capability,
            )

        general_providers = self._general_search_providers()
        general_route: RouteKind = "fallback_candidate" if len(general_providers) > 1 else "single"

        if request.intent == "fresh":
            return SearchRouteDecision(
                route="fallback_candidate",
                providers=self._fresh_search_providers(general_providers),
                reason="fresh intent prefers fresh-search providers",
                capability=capability,
            )

        if request.intent == "docs":
            return SearchRouteDecision(
                route="fallback_candidate",
                providers=self._docs_search_providers(general_providers),
                reason="docs intent prefers authoritative-search providers",
                capability=capability,
            )

        if request.intent == "social":
            return SearchRouteDecision(
                route="fallback_candidate",
                providers=general_providers,
                reason="social lane currently falls back to general providers",
                capability=capability,
            )

        if request.verification_level == "light":
            return SearchRouteDecision(
                route="fallback_candidate",
                providers=general_providers,
                reason="light verification keeps a fallback candidate list",
                capability=capability,
            )

        return SearchRouteDecision(
            route=general_route,
            providers=general_providers,
            reason="general intent uses configured broad-search providers",
            capability=capability,
        )

    def _capability_for(self, request: SearchRequest) -> SearchCapability:
        if request.intent == "docs":
            return "authoritative_search"
        if request.intent == "fresh":
            return "fresh_search"
        if request.intent == "social":
            return "social_search"
        return "broad_search"

    def _general_search_providers(self) -> tuple[str, ...]:
        providers: list[str] = []
        if self.settings.brave_search_api_key:
            providers.append("brave")
        if self.settings.tavily_api_key:
            providers.append("tavily")
        if providers:
            return tuple(providers)
        return ("tavily",)

    def _docs_search_providers(self, general_providers: tuple[str, ...]) -> tuple[str, ...]:
        providers: list[str] = []
        if self.settings.exa_api_key:
            providers.append("exa")
        for provider in general_providers:
            if provider not in providers:
                providers.append(provider)
        return tuple(providers)

    def _fresh_search_providers(self, general_providers: tuple[str, ...]) -> tuple[str, ...]:
        providers: list[str] = []
        if self.settings.newsapi_api_key:
            providers.append("newsapi")
        for provider in general_providers:
            if provider not in providers:
                providers.append(provider)
        return tuple(providers)
