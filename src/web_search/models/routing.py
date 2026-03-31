from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RouteKind = Literal["single", "fallback_candidate", "provider_override"]
SearchCapability = Literal[
    "authoritative_search",
    "fresh_search",
    "broad_search",
    "social_search",
]
ExtractCapability = Literal["content_extract", "structured_extract"]


@dataclass(frozen=True)
class RouteDecision:
    route: RouteKind
    providers: tuple[str, ...]
    provider_override_applied: bool = False
    reason: str | None = None

    @property
    def primary_provider(self) -> str | None:
        if not self.providers:
            return None
        return self.providers[0]

    @property
    def fallback_providers(self) -> tuple[str, ...]:
        if len(self.providers) < 2:
            return ()
        return self.providers[1:]

    @property
    def allows_fallback(self) -> bool:
        return self.route == "fallback_candidate"


@dataclass(frozen=True)
class SearchRouteDecision(RouteDecision):
    capability: SearchCapability = "broad_search"


@dataclass(frozen=True)
class ExtractRouteDecision(RouteDecision):
    capability: ExtractCapability = "content_extract"
