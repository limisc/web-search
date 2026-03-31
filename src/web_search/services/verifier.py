from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import HttpUrl, TypeAdapter

from web_search.models.responses import SearchHit, SearchResponse, VerificationSummary

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


def apply_light_verification(response: SearchResponse) -> SearchResponse:
    deduped_results: list[SearchHit] = []
    seen_urls: set[str] = set()
    canonicalized_urls = 0
    duplicates_removed = 0
    source_domains: list[str] = []
    seen_domains: set[str] = set()

    for result in response.results:
        canonical_url = canonicalize_url(str(result.url))
        if canonical_url != str(result.url):
            canonicalized_urls += 1
            result = result.model_copy(update={"url": _HTTP_URL_ADAPTER.validate_python(canonical_url)})
        if canonical_url in seen_urls:
            duplicates_removed += 1
            continue
        seen_urls.add(canonical_url)
        domain = _domain_for(canonical_url)
        if domain and domain not in seen_domains:
            seen_domains.add(domain)
            source_domains.append(domain)
        deduped_results.append(result)

    deduped_citations = []
    seen_citation_urls: set[str] = set()
    for citation in response.citations:
        canonical_url = canonicalize_url(str(citation.url))
        if canonical_url in seen_citation_urls:
            continue
        seen_citation_urls.add(canonical_url)
        deduped_citations.append(citation.model_copy(update={"url": _HTTP_URL_ADAPTER.validate_python(canonical_url)}))

    verification_summary = _light_verification_summary(
        results=deduped_results,
        source_domains=source_domains,
        canonicalized_urls=canonicalized_urls,
        duplicates_removed=duplicates_removed,
    )

    return response.model_copy(
        update={
            "results": deduped_results,
            "citations": deduped_citations,
            "meta": response.meta.model_copy(update={"verification_summary": verification_summary}),
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


def _light_verification_summary(
    *,
    results: list[SearchHit],
    source_domains: list[str],
    canonicalized_urls: int,
    duplicates_removed: int,
) -> VerificationSummary:
    summary: VerificationSummary = {
        "canonicalized_urls": canonicalized_urls,
        "duplicates_removed": duplicates_removed,
        "source_domains": source_domains,
        "unique_domain_count": len(source_domains),
        "multi_source": len(source_domains) > 1,
    }
    agreement_hints = _agreement_hints_for(results)
    if agreement_hints:
        summary["agreement_hints"] = agreement_hints
    return summary


def _agreement_hints_for(results: list[SearchHit]) -> list[str]:
    title_domains: dict[str, set[str]] = {}
    for result in results:
        normalized_title = _normalize_title(result.title)
        if not normalized_title:
            continue
        domain = _domain_for(str(result.url))
        if not domain:
            continue
        title_domains.setdefault(normalized_title, set()).add(domain)

    max_matching_domains = max((len(domains) for domains in title_domains.values()), default=0)
    if max_matching_domains <= 1:
        return []
    return [f"Matching titles appeared across {max_matching_domains} domains"]


def _normalize_title(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower())
    return " ".join(normalized.split())


def _should_drop_query_param(key: str) -> bool:
    lowered = key.lower()
    return lowered.startswith(_TRACKING_QUERY_PREFIXES) or lowered in _TRACKING_QUERY_KEYS


def _domain_for(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()
