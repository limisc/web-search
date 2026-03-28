from __future__ import annotations

from typing import Literal

from web_search.models.requests import SearchRequest

ExecutionMode = Literal["low_cost", "balanced", "high_reliability"]


class Planner:
    def mode_for(self, request: SearchRequest) -> ExecutionMode:
        if request.verification_level == "high":
            return "high_reliability"
        if request.verification_level in {"medium", "light"} or request.extraction:
            return "balanced"
        return "low_cost"
