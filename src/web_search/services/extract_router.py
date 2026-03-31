from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from web_search.config import get_settings
from web_search.models.requests import ExtractRequest

RouteKind = Literal["single", "fallback_candidate", "provider_override"]


@dataclass(frozen=True)
class ExtractProviderPlan:
    route: RouteKind
    providers: tuple[str, ...]


class ExtractRouter:
    def __init__(self) -> None:
        self.settings = get_settings()

    def plan(self, request: ExtractRequest) -> ExtractProviderPlan:
        if request.provider:
            return ExtractProviderPlan(route="provider_override", providers=(request.provider,))

        if request.mode == "structured":
            return ExtractProviderPlan(route="single", providers=())

        providers = self._content_extract_providers(request)
        route: RouteKind = "fallback_candidate" if len(providers) > 1 else "single"
        return ExtractProviderPlan(route=route, providers=providers)

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
