from __future__ import annotations

from web_search.models.requests import ExtractRequest
from web_search.models.responses import ExtractResponse
from web_search.providers import get_provider, is_provider_available
from web_search.services.extract_router import ExtractRouter
from web_search.utils.errors import ProviderError


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

        last_error: ProviderError | None = None
        for provider_name in plan.providers:
            if not is_provider_available(provider_name):
                continue
            provider = get_provider(provider_name)
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
