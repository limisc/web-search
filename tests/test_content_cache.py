from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from web_search.config import clear_settings_cache
from web_search.models.requests import ExtractRequest
from web_search.models.responses import ExtractResponse, ExtractedPage, ResponseMeta
from web_search.services.extract_service import ExtractService, clear_extract_cache
from web_search.utils.content_cache import ContentCache, derive_page_for_request, normalize_url_for_cache


@pytest.fixture(autouse=True)
def clear_content_cache() -> None:
    clear_settings_cache()
    clear_extract_cache()


def test_normalize_url_for_cache_drops_tracking_and_sorts_query() -> None:
    normalized = normalize_url_for_cache(
        "https://Example.com/docs/?b=2&utm_source=test&a=1#section"
    )

    assert normalized == "https://example.com/docs?a=1&b=2"


def test_derive_page_for_request_reuses_cached_markdown_for_text_query_and_chunks() -> None:
    page = ExtractedPage.model_validate(
        {
            "url": "https://example.com/page",
            "title": "Example",
            "content": "# Title\n\nalpha\n\nneedle chunk\n\nomega",
            "excerpt": "alpha",
            "chunks": [],
            "provider": "exa",
        }
    )

    derived = derive_page_for_request(
        page,
        ExtractRequest.from_tool_args(
            urls=["https://example.com/page"],
            format="text",
            query="needle",
            max_chunks=1,
        ),
    )

    assert derived.content == "Title\n\nalpha\n\nneedle chunk\n\nomega"
    assert derived.chunks == ["needle chunk"]
    assert derived.excerpt == "needle chunk"


@pytest.mark.asyncio
async def test_content_cache_returns_stale_and_refreshes_in_background(tmp_path) -> None:
    cache = ContentCache(db_path=tmp_path / "content-cache.sqlite")
    calls: list[str] = []

    async def first_loader() -> ExtractedPage:
        calls.append("first")
        return ExtractedPage.model_validate(
            {
                "url": "https://example.com/page",
                "title": "Example",
                "content": "old body",
                "excerpt": "old body",
                "chunks": [],
                "provider": "exa",
            }
        )

    first = await cache.get_or_create(provider="exa", url="https://example.com/page", loader=first_loader)
    assert first.state == "miss"
    assert first.page is not None
    assert calls == ["first"]

    with sqlite3.connect(cache.db_path) as conn:
        conn.execute("UPDATE content_cache SET fresh_until = ?, stale_until = ?", (0, 4102444800))
        conn.commit()

    async def second_loader() -> ExtractedPage:
        calls.append("second")
        return ExtractedPage.model_validate(
            {
                "url": "https://example.com/page",
                "title": "Example",
                "content": "new body",
                "excerpt": "new body",
                "chunks": [],
                "provider": "exa",
            }
        )

    stale = await cache.get_or_create(provider="exa", url="https://example.com/page", loader=second_loader)
    assert stale.state == "stale"
    assert stale.page is not None
    assert stale.page.content == "old body"
    assert stale.refresh_task is not None
    await stale.refresh_task

    fresh = await cache.get_or_create(provider="exa", url="https://example.com/page", loader=second_loader)
    assert fresh.page is not None
    assert fresh.page.content == "new body"
    assert fresh.state == "fresh"
    assert calls == ["first", "second"]


@pytest.mark.asyncio
async def test_content_cache_evicts_least_recently_used_rows_when_capacity_is_exceeded(tmp_path) -> None:
    cache = ContentCache(db_path=tmp_path / "content-cache.sqlite", max_entries=1)

    async def first_loader() -> ExtractedPage:
        return ExtractedPage.model_validate(
            {
                "url": "https://example.com/one",
                "title": "One",
                "content": "one",
                "excerpt": "one",
                "chunks": [],
                "provider": "exa",
            }
        )

    async def second_loader() -> ExtractedPage:
        return ExtractedPage.model_validate(
            {
                "url": "https://example.com/two",
                "title": "Two",
                "content": "two",
                "excerpt": "two",
                "chunks": [],
                "provider": "exa",
            }
        )

    await cache.get_or_create(provider="exa", url="https://example.com/one", loader=first_loader)
    await cache.get_or_create(provider="exa", url="https://example.com/two", loader=second_loader)

    with sqlite3.connect(cache.db_path) as conn:
        rows = conn.execute("SELECT normalized_url FROM content_cache ORDER BY normalized_url").fetchall()

    assert rows == [("https://example.com/two",)]


@pytest.mark.asyncio
async def test_content_cache_prunes_expired_rows_before_capacity_trim(tmp_path) -> None:
    cache = ContentCache(db_path=tmp_path / "content-cache.sqlite", max_entries=2)

    async def loader(url: str) -> ExtractedPage:
        return ExtractedPage.model_validate(
            {
                "url": url,
                "title": url,
                "content": url,
                "excerpt": url,
                "chunks": [],
                "provider": "exa",
            }
        )

    await cache.get_or_create(provider="exa", url="https://example.com/expired", loader=lambda: loader("https://example.com/expired"))
    with sqlite3.connect(cache.db_path) as conn:
        conn.execute("UPDATE content_cache SET stale_until = ? WHERE normalized_url = ?", (0, "https://example.com/expired"))
        conn.commit()

    await cache.get_or_create(provider="exa", url="https://example.com/fresh-a", loader=lambda: loader("https://example.com/fresh-a"))
    await cache.get_or_create(provider="exa", url="https://example.com/fresh-b", loader=lambda: loader("https://example.com/fresh-b"))

    with sqlite3.connect(cache.db_path) as conn:
        rows = conn.execute("SELECT normalized_url FROM content_cache ORDER BY normalized_url").fetchall()

    assert rows == [
        ("https://example.com/fresh-a",),
        ("https://example.com/fresh-b",),
    ]


@pytest.mark.asyncio
async def test_extract_service_uses_content_cache_for_single_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CONTENT_CACHE_DB_PATH", str(tmp_path / "service-cache.sqlite"))
    monkeypatch.setenv("CONTENT_CACHE_MAX_ENTRIES", "10")
    clear_extract_cache()

    service = ExtractService()
    call_count = 0

    async def fake_extract(_request: ExtractRequest) -> ExtractResponse:
        nonlocal call_count
        call_count += 1
        return ExtractResponse(
            provider="exa",
            mode="content",
            pages=[
                ExtractedPage.model_validate(
                    {
                        "url": "https://example.com/page",
                        "title": "Example",
                        "content": "cached body",
                        "excerpt": "cached body",
                        "chunks": [],
                        "provider": "exa",
                    }
                )
            ],
            meta=ResponseMeta(latency_ms=10, providers_used=["exa"]),
        )

    class FakeProvider:
        async def extract(self, request: ExtractRequest) -> ExtractResponse:
            return await fake_extract(request)

    monkeypatch.setattr("web_search.services.extract_service.is_extract_provider_available", lambda name: name == "exa")
    monkeypatch.setattr("web_search.services.extract_service.get_extract_provider", lambda name: FakeProvider())
    monkeypatch.setattr(service.router, "plan", lambda request: type("Plan", (), {"route": "single", "providers": ("exa",)})())

    request = ExtractRequest.from_tool_args(
        urls=["https://example.com/page"],
        query="cached",
        max_chunks=1,
        format="text",
    )
    first = await service.run(request)
    second = await service.run(request)

    assert first.meta.cache_state == "miss"
    assert first.pages[0].chunks == ["cached body"]
    assert second.meta.cached is True
    assert second.meta.cache_state == "fresh"
    assert call_count == 1
