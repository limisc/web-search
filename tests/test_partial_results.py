from __future__ import annotations

from web_search.models.responses import SearchResponse
from web_search.services.partial_results import attach_partial_results_metadata
from web_search.utils.errors import ProviderError


def test_attach_partial_results_metadata_keeps_clean_success_when_no_failures() -> None:
    response = SearchResponse.model_validate(
        {
            "query": "mcp",
            "intent": "general",
            "provider": "tavily",
            "results": [],
            "citations": [],
            "meta": {"latency_ms": 10},
        }
    )

    updated = attach_partial_results_metadata(response, failed_attempts=[])

    assert updated.meta.partial_failures == []


def test_attach_partial_results_metadata_records_failed_attempts() -> None:
    response = SearchResponse.model_validate(
        {
            "query": "mcp",
            "intent": "general",
            "provider": "tavily",
            "results": [],
            "citations": [],
            "meta": {"latency_ms": 10, "verification_summary": {"canonicalized_urls": 0, "duplicates_removed": 0}},
        }
    )
    failure = ProviderError("boom", provider="brave", error_type="provider_timeout")

    updated = attach_partial_results_metadata(response, failed_attempts=[failure])

    assert updated.meta.partial_failures == [
        {"provider": "brave", "error_type": "provider_timeout", "message": "boom"}
    ]
    assert updated.meta.verification_summary == {
        "canonicalized_urls": 0,
        "duplicates_removed": 0,
        "partial_failures": 1,
    }
