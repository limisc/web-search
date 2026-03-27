from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Citation(BaseModel):
    title: str
    url: HttpUrl
    provider: str


class SearchHit(BaseModel):
    title: str
    url: HttpUrl
    snippet: str | None = None
    content: str | None = None
    score: float | None = None
    published_at: str | None = None
    source_type: str = "web"
    provider: str
    raw: dict[str, Any] | None = None


class ResponseMeta(BaseModel):
    latency_ms: int
    cached: bool = False
    provider_request_id: str | None = None


class SearchResponse(BaseModel):
    query: str
    provider: str
    answer: str | None = None
    results: list[SearchHit]
    citations: list[Citation]
    meta: ResponseMeta


class ExtractedPage(BaseModel):
    url: HttpUrl
    title: str | None = None
    content: str | None = None
    excerpt: str | None = None
    chunks: list[str] = Field(default_factory=list)
    provider: str
    raw: dict[str, Any] | None = None


class ExtractResponse(BaseModel):
    provider: str
    pages: list[ExtractedPage]
    meta: ResponseMeta
