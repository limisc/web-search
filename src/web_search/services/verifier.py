from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from web_search.models.responses import SearchHit, SearchResponse
from pydantic import HttpUrl, TypeAdapter

_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)

_TRACKING_QUERY_PREFIXES = ("utm_", "ga_", "gs_", "mc_", "ref_")
_TRACKING_QUERY_KEYS = {
    "ref",
    "ref_src",
    "ref_url",
    "source",
    "src",
    "fbclid",
    "gclid",
    "igshid",
    "si",
}


@dataclass(frozen=True)
class VerificationSummary:
    canonicalized_urls: int
    duplicates_removed: int


def apply_light_verification(response: SearchResponse) -> SearchResponse:
    deduped_results: list[SearchHit] = []
    seen_urls: set[str] = set()
    canonicalized_urls = 0
    duplicates_removed = 0

    for result in response.results:
        canonical_url = canonicalize_url(str(result.url))
        if canonical_url != str(result.url):
            canonicalized_urls += 1
            result = result.model_copy(update={"url": _HTTP_URL_ADAPTER.validate_python(canonical_url)})
        if canonical_url in seen_urls:
            duplicates_removed += 1
            continue
        seen_urls.add(canonical_url)
        deduped_results.append(result)

    deduped_citations = []
    seen_citation_urls: set[str] = set()
    for citation in response.citations:
        canonical_url = canonicalize_url(str(citation.url))
        if canonical_url in seen_citation_urls:
            continue
        seen_citation_urls.add(canonical_url)
        deduped_citations.append(citation.model_copy(update={"url": _HTTP_URL_ADAPTER.validate_python(canonical_url)}))

    return response.model_copy(
        update={
            "results": deduped_results,
            "citations": deduped_citations,
            "meta": response.meta.model_copy(
                update={
                    "verification_summary": {
                        "canonicalized_urls": canonicalized_urls,
                        "duplicates_removed": duplicates_removed,
                    }
                }
            ),
        }
    )


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    port = parts.port
    netloc = hostname
    if port is not None and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"

    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/") or "/"

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _should_drop_query_param(key)
    ]
    query_pairs.sort()
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def _should_drop_query_param(key: str) -> bool:
    lowered = key.lower()
    return lowered.startswith(_TRACKING_QUERY_PREFIXES) or lowered in _TRACKING_QUERY_KEYS
