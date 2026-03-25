from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    provider: Literal["tavily"] = "tavily"
    max_results: int = Field(default=5, ge=1, le=10)
    topic: Literal["general", "news"] = "general"
    time_range: Literal["day", "week", "month", "year"] | None = None
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    search_depth: Literal["basic", "advanced"] = "basic"
    include_answer: bool = True
    include_raw_content: bool = False


class ExtractRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=10)
    provider: Literal["tavily"] = "tavily"
    extract_depth: Literal["basic", "advanced"] = "basic"
    query: str | None = None
    max_chunks: int | None = Field(default=None, ge=1, le=5)
    format: Literal["markdown", "text"] = "markdown"
