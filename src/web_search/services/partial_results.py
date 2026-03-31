from __future__ import annotations

from typing import Any

from web_search.models.responses import SearchResponse
from web_search.utils.errors import ProviderError


def attach_partial_results_metadata(
    response: SearchResponse,
    *,
    failed_attempts: list[ProviderError],
) -> SearchResponse:
    if not failed_attempts:
        return response

    partial_failures: list[dict[str, Any]] = []
    for failure in failed_attempts:
        partial_failures.append(
            {
                "provider": failure.provider,
                "error_type": failure.error_type,
                "message": str(failure),
            }
        )

    summary = dict(response.meta.verification_summary or {})
    summary["partial_failures"] = len(partial_failures)

    return response.model_copy(
        update={
            "meta": response.meta.model_copy(
                update={
                    "verification_summary": summary,
                    "partial_failures": partial_failures,
                }
            )
        }
    )
