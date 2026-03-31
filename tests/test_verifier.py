from __future__ import annotations

from web_search.models.responses import SearchResponse
from web_search.services.verifier import apply_light_verification, canonicalize_url


def test_canonicalize_url_drops_tracking_and_normalizes_shape() -> None:
    assert canonicalize_url("https://Example.com/docs/?b=2&utm_source=test&a=1#frag") == "https://example.com/docs?a=1&b=2"


def test_apply_light_verification_dedupes_results_and_citations() -> None:
    response = SearchResponse.model_validate(
        {
            "query": "mcp",
            "intent": "general",
            "provider": "tavily",
            "results": [
                {
                    "title": "A",
                    "url": "https://example.com/docs/?utm_source=test",
                    "provider": "tavily",
                },
                {
                    "title": "B",
                    "url": "https://example.com/docs",
                    "provider": "tavily",
                },
            ],
            "citations": [
                {"title": "A", "url": "https://example.com/docs/?ref=abc", "provider": "tavily"},
                {"title": "B", "url": "https://example.com/docs", "provider": "tavily"},
            ],
            "meta": {"latency_ms": 10, "verification_level": "light"},
        }
    )

    verified = apply_light_verification(response)

    assert len(verified.results) == 1
    assert str(verified.results[0].url) == "https://example.com/docs"
    assert len(verified.citations) == 1
    assert str(verified.citations[0].url) == "https://example.com/docs"
    assert verified.meta.verification_summary == {
        "canonicalized_urls": 1,
        "duplicates_removed": 1,
    }
