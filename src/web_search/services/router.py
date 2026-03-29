from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from web_search.config import get_settings
from web_search.models.requests import SearchRequest

RouteKind = Literal["single", "fallback_candidate", "provider_override"]


@dataclass(frozen=True)
class ProviderPlan:
    route: RouteKind
    search_providers: tuple[str, ...]
    extract_requested: bool = False


class Router:
    def __init__(self) -> None:
        self.settings = get_settings()

    def plan(self, request: SearchRequest) -> ProviderPlan:
        if request.provider:
            return ProviderPlan(
                route="provider_override",
                search_providers=(request.provider,),
                extract_requested=request.extraction,
            )

        general_providers = self._general_search_providers()
        general_route: RouteKind = "fallback_candidate" if len(general_providers) > 1 else "single"

        if request.intent == "fresh":
            return ProviderPlan(
                route="fallback_candidate",
                search_providers=general_providers,
                extract_requested=request.extraction,
            )

        if request.intent in {"docs", "social"}:
            # These lanes are part of the public contract but are not natively implemented yet.
            # Keep the current runtime honest by falling back to currently available providers.
            return ProviderPlan(
                route="fallback_candidate",
                search_providers=general_providers,
                extract_requested=request.extraction,
            )

        if request.verification_level == "light":
            return ProviderPlan(
                route="fallback_candidate",
                search_providers=general_providers,
                extract_requested=request.extraction,
            )

        return ProviderPlan(
            route=general_route,
            search_providers=general_providers,
            extract_requested=request.extraction,
        )

    def _general_search_providers(self) -> tuple[str, ...]:
        providers: list[str] = []
        if self.settings.brave_search_api_key:
            providers.append("brave")
        if self.settings.tavily_api_key:
            providers.append("tavily")
        if providers:
            return tuple(providers)
        return ("tavily",)
