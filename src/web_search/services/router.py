from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from web_search.models.requests import SearchRequest

RouteKind = Literal["single", "fallback_candidate", "provider_override"]


@dataclass(frozen=True)
class ProviderPlan:
    route: RouteKind
    search_providers: tuple[str, ...]
    extract_requested: bool = False


class Router:
    def plan(self, request: SearchRequest) -> ProviderPlan:
        if request.provider:
            return ProviderPlan(
                route="provider_override",
                search_providers=(request.provider,),
                extract_requested=request.extraction,
            )

        if request.intent in {"docs", "fresh", "social"}:
            # These lanes are part of the public contract but are not natively implemented yet.
            # Keep the current runtime honest by falling back to the currently available provider.
            return ProviderPlan(
                route="fallback_candidate",
                search_providers=("tavily",),
                extract_requested=request.extraction,
            )

        if request.verification_level == "light":
            return ProviderPlan(
                route="fallback_candidate",
                search_providers=("tavily",),
                extract_requested=request.extraction,
            )

        return ProviderPlan(
            route="single",
            search_providers=("tavily",),
            extract_requested=request.extraction,
        )
