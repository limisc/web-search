from __future__ import annotations

import pytest

from web_search.models.requests import ExtractRequest, SearchRequest


def test_search_request_rejects_blank_query() -> None:
    with pytest.raises(ValueError, match="query must not be blank"):
        SearchRequest(query="   ")


def test_search_request_normalizes_domain_shorthand_into_include_domains() -> None:
    request = SearchRequest(
        query="hello",
        domains=["Example.com", "example.com"],
        include_domains=["Docs.Python.org"],
        exclude_domains=["Bad.com", "bad.com", "  "],
    )

    assert request.domains == []
    assert request.include_domains == ["example.com", "docs.python.org"]
    assert request.exclude_domains == ["bad.com"]


def test_extract_request_normalizes_blank_query_to_none() -> None:
    request = ExtractRequest(urls=["https://example.com/page"], query="   ")

    assert request.query is None
