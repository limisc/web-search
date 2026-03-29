from __future__ import annotations

from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

SearchIntent = Literal["docs", "fresh", "general", "social"]
Freshness = Literal["day", "week", "month", "year", "any"]
VerificationLevel = Literal["none", "light", "medium", "high"]
ExtractMode = Literal["content", "structured"]
OutputFormat = Literal["markdown", "text"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    intent: SearchIntent = "general"
    freshness: Freshness | None = None
    domains: list[str] = Field(default_factory=list)
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    max_results: int = Field(default=5, ge=1, le=10)
    verification_level: VerificationLevel = "none"
    extraction: bool = False
    debug: bool = False
    provider: str | None = None

    @classmethod
    def from_tool_args(
        cls,
        *,
        query: str,
        intent: str = "general",
        freshness: str | None = None,
        domains: Sequence[str] | None = None,
        include_domains: Sequence[str] | None = None,
        exclude_domains: Sequence[str] | None = None,
        max_results: int = 5,
        verification_level: str = "none",
        extraction: bool = False,
        debug: bool = False,
        provider: str | None = None,
    ) -> "SearchRequest":
        return cls.model_validate(
            {
                "query": query,
                "intent": intent,
                "freshness": freshness,
                "domains": list(domains or []),
                "include_domains": list(include_domains or []),
                "exclude_domains": list(exclude_domains or []),
                "max_results": max_results,
                "verification_level": verification_level,
                "extraction": extraction,
                "debug": debug,
                "provider": provider,
            }
        )

    @model_validator(mode="after")
    def normalize_domains(self) -> "SearchRequest":
        merged: list[str] = []
        seen: set[str] = set()
        for domain in [*self.domains, *self.include_domains]:
            normalized = domain.strip().lower()
            if normalized and normalized not in seen:
                merged.append(normalized)
                seen.add(normalized)
        self.include_domains = merged
        self.exclude_domains = [domain.strip().lower() for domain in self.exclude_domains if domain.strip()]
        if self.freshness == "any":
            self.freshness = None
        self.query = self.query.strip()
        return self


class ExtractRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    urls: list[HttpUrl] = Field(min_length=1, max_length=10)
    mode: ExtractMode = "content"
    extraction_schema: dict[str, Any] | None = Field(default=None, alias="schema")
    query: str | None = None
    max_chunks: int | None = Field(default=None, ge=1, le=5)
    format: OutputFormat = "markdown"
    debug: bool = False
    provider: str | None = None

    @classmethod
    def from_tool_args(
        cls,
        *,
        urls: Sequence[str],
        mode: str = "content",
        schema: dict[str, Any] | None = None,
        query: str | None = None,
        max_chunks: int | None = None,
        format: str = "markdown",
        debug: bool = False,
        provider: str | None = None,
    ) -> "ExtractRequest":
        return cls.model_validate(
            {
                "urls": list(urls),
                "mode": mode,
                "schema": schema,
                "query": query,
                "max_chunks": max_chunks,
                "format": format,
                "debug": debug,
                "provider": provider,
            }
        )

    @model_validator(mode="after")
    def normalize_query(self) -> "ExtractRequest":
        self.query = self.query.strip() if self.query else None
        return self
