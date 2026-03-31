from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from web_search.models.requests import ExtractRequest
from web_search.models.responses import ExtractedPage

CacheState = Literal["fresh", "stale", "miss"]

_TRACKING_QUERY_PREFIXES = ("utm_",)
_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "ref", "source"}
_DOC_HOST_MARKERS = ("docs.", "developer.", "developers.", "api.", "help.")
_DOC_PATH_MARKERS = ("/docs", "/documentation", "/developer", "/developers", "/reference", "/api")
_NEWS_HOST_MARKERS = ("news.",)
_NEWS_PATH_MARKERS = ("/news", "/blog", "/article", "/press")
Loader = Callable[[], Awaitable[ExtractedPage]]


@dataclass(frozen=True)
class ContentCacheEntry:
    page: ExtractedPage
    fetched_at: float
    fresh_until: float
    stale_until: float


@dataclass(frozen=True)
class CachedExtractLookup:
    state: CacheState
    page: ExtractedPage | None
    refresh_task: asyncio.Task[None] | None = None


class ContentCache:
    def __init__(self, db_path: str | Path = ".runtime/content_cache.sqlite") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}
        self._initialize_db()

    async def get_or_create(
        self,
        *,
        provider: str,
        url: str,
        loader: Loader,
    ) -> CachedExtractLookup:
        normalized_url = normalize_url_for_cache(url)
        cache_key = make_content_cache_key(provider, normalized_url)
        cached = self._read(cache_key)
        now = time.time()

        if cached is None:
            page = await self._refresh(cache_key=cache_key, provider=provider, url=url, loader=loader)
            return CachedExtractLookup(state="miss", page=page)

        if cached.fresh_until > now:
            return CachedExtractLookup(state="fresh", page=cached.page)

        if cached.stale_until > now:
            refresh_task = asyncio.create_task(self._refresh_if_needed(cache_key=cache_key, provider=provider, url=url, loader=loader))
            return CachedExtractLookup(state="stale", page=cached.page, refresh_task=refresh_task)

        page = await self._refresh(cache_key=cache_key, provider=provider, url=url, loader=loader)
        return CachedExtractLookup(state="miss", page=page)

    async def refresh_now(self, *, provider: str, url: str, loader: Loader) -> ExtractedPage:
        normalized_url = normalize_url_for_cache(url)
        cache_key = make_content_cache_key(provider, normalized_url)
        return await self._refresh(cache_key=cache_key, provider=provider, url=url, loader=loader)

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM content_cache")
            conn.commit()

    def _initialize_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS content_cache (
                    cache_key TEXT PRIMARY KEY,
                    normalized_url TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    page_json TEXT NOT NULL,
                    fetched_at REAL NOT NULL,
                    fresh_until REAL NOT NULL,
                    stale_until REAL NOT NULL,
                    last_accessed_at REAL NOT NULL,
                    hit_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_content_cache_last_accessed ON content_cache(last_accessed_at)"
            )
            conn.commit()

    def _read(self, cache_key: str) -> ContentCacheEntry | None:
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT page_json, fetched_at, fresh_until, stale_until, hit_count FROM content_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE content_cache SET last_accessed_at = ?, hit_count = hit_count + 1 WHERE cache_key = ?",
                (now, cache_key),
            )
            conn.commit()

        page_json, fetched_at, fresh_until, stale_until, _hit_count = row
        return ContentCacheEntry(
            page=ExtractedPage.model_validate(json.loads(page_json)),
            fetched_at=float(fetched_at),
            fresh_until=float(fresh_until),
            stale_until=float(stale_until),
        )

    async def _refresh_if_needed(self, *, cache_key: str, provider: str, url: str, loader: Loader) -> None:
        try:
            await self._refresh(cache_key=cache_key, provider=provider, url=url, loader=loader)
        except Exception:
            return

    async def _refresh(self, *, cache_key: str, provider: str, url: str, loader: Loader) -> ExtractedPage:
        lock = self._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached = self._read(cache_key)
            if cached is not None and cached.fresh_until > time.time():
                return cached.page

            page = await loader()
            self._write(cache_key=cache_key, provider=provider, url=url, page=page)
            return page

    def _write(self, *, cache_key: str, provider: str, url: str, page: ExtractedPage) -> None:
        now = time.time()
        ttl = _ttl_for(url=url, provider=provider)
        page_json = json.dumps(page.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        normalized_url = normalize_url_for_cache(url)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO content_cache (
                    cache_key,
                    normalized_url,
                    provider,
                    page_json,
                    fetched_at,
                    fresh_until,
                    stale_until,
                    last_accessed_at,
                    hit_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(cache_key) DO UPDATE SET
                    normalized_url = excluded.normalized_url,
                    provider = excluded.provider,
                    page_json = excluded.page_json,
                    fetched_at = excluded.fetched_at,
                    fresh_until = excluded.fresh_until,
                    stale_until = excluded.stale_until,
                    last_accessed_at = excluded.last_accessed_at
                """,
                (
                    cache_key,
                    normalized_url,
                    provider,
                    page_json,
                    now,
                    now + ttl.fresh_seconds,
                    now + ttl.stale_seconds,
                    now,
                ),
            )
            conn.commit()


@dataclass(frozen=True)
class CacheTtl:
    fresh_seconds: int
    stale_seconds: int


def normalize_url_for_cache(url: str) -> str:
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


def make_content_cache_key(provider: str, normalized_url: str) -> str:
    digest = hashlib.sha256(f"{provider}:{normalized_url}".encode("utf-8")).hexdigest()
    return f"content:{digest}"


def cacheable_extract_request(request: ExtractRequest) -> bool:
    return request.mode == "content" and not request.debug


def derive_page_for_request(page: ExtractedPage, request: ExtractRequest) -> ExtractedPage:
    content = page.content or ""
    if request.format == "text":
        content = _plain_text_from_markdown(content)
    chunks = _chunks_for_request(content, request)
    if not chunks:
        chunks = list(page.chunks)
        if request.max_chunks:
            chunks = chunks[: request.max_chunks]
    excerpt = chunks[0][:280] if chunks else (content[:280] or None)
    return page.model_copy(update={"content": content or None, "chunks": chunks, "excerpt": excerpt})


def _ttl_for(*, url: str, provider: str) -> CacheTtl:
    normalized = normalize_url_for_cache(url)
    lower = normalized.lower()
    if provider == "firecrawl":
        return CacheTtl(fresh_seconds=12 * 3600, stale_seconds=48 * 3600)
    if any(marker in lower for marker in _DOC_HOST_MARKERS + _DOC_PATH_MARKERS):
        return CacheTtl(fresh_seconds=24 * 3600, stale_seconds=7 * 24 * 3600)
    if any(marker in lower for marker in _NEWS_HOST_MARKERS + _NEWS_PATH_MARKERS):
        return CacheTtl(fresh_seconds=30 * 60, stale_seconds=6 * 3600)
    return CacheTtl(fresh_seconds=6 * 3600, stale_seconds=24 * 3600)


def _should_drop_query_param(key: str) -> bool:
    lowered = key.lower()
    return lowered.startswith(_TRACKING_QUERY_PREFIXES) or lowered in _TRACKING_QUERY_KEYS


def _plain_text_from_markdown(markdown: str) -> str:
    text = markdown
    replacements = [
        ("\r\n", "\n"),
        ("\r", "\n"),
        ("# ", ""),
        ("## ", ""),
        ("### ", ""),
        ("- ", ""),
        ("* ", ""),
        ("`", ""),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return "\n\n".join(part.strip() for part in text.split("\n\n") if part.strip())


def _chunks_for_request(content: str, request: ExtractRequest) -> list[str]:
    if not content:
        return []
    if request.query:
        paragraphs = [part.strip() for part in content.split("\n\n") if part.strip()]
        lowered_query = request.query.lower()
        matching = [part for part in paragraphs if lowered_query in part.lower()]
        if request.max_chunks:
            return matching[: request.max_chunks]
        if matching:
            return matching
    if request.max_chunks:
        max_chars = max(1, len(content) // request.max_chunks)
        return [segment.strip() for segment in (content[i : i + max_chars] for i in range(0, len(content), max_chars)) if segment.strip()][
            : request.max_chunks
        ]
    return []
