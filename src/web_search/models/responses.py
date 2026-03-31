from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

from web_search.models.routing import ExtractCapability, SearchCapability

VerificationLevel = Literal["none", "light", "medium", "high"]
CacheState = Literal["miss", "fresh", "stale"]
Capability = SearchCapability | ExtractCapability


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
    cache_state: CacheState | None = None
    route: str | None = None
    capability: Capability | None = None
    provider_override_applied: bool = False
    providers_used: list[str] = Field(default_factory=list)
    verification_level: VerificationLevel = "none"


class SearchResponse(BaseModel):
    query: str
    intent: str
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
    mode: str
    pages: list[ExtractedPage]
    structured_data: dict[str, Any] | list[Any] | None = None
    meta: ResponseMeta
