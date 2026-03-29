from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

SearchIntent = Literal["docs", "fresh", "general", "social"]
Freshness = Literal["day", "week", "month", "year", "any"]
SafeSearch = Literal["off", "moderate", "strict"]
VerificationLevel = Literal["none", "light", "medium", "high"]
ExtractMode = Literal["content", "structured"]
OutputFormat = Literal["markdown", "text"]


class SearchPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    search_lang: str | None = Field(default=None, min_length=2, max_length=16, pattern=r"^[A-Za-z-]+$")
    ui_lang: str | None = Field(default=None, min_length=2, max_length=16, pattern=r"^[A-Za-z-]+$")
    safesearch: SafeSearch | None = None
    spellcheck: bool | None = None

    @model_validator(mode="after")
    def normalize_preferences(self) -> "SearchPreferences":
        self.country = self.country.strip().upper() if self.country else None
        self.search_lang = self.search_lang.strip().lower() if self.search_lang else None
        self.ui_lang = self.ui_lang.strip() if self.ui_lang else None
        return self


class BraveSearchOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goggles: list[str] = Field(default_factory=list)

    @field_validator("goggles", mode="before")
    @classmethod
    def coerce_goggles(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value

    @model_validator(mode="after")
    def normalize_goggles(self) -> "BraveSearchOptions":
        normalized_goggles: list[str] = []
        seen_goggles: set[str] = set()
        for goggle in self.goggles:
            cleaned = goggle.strip()
            if cleaned and cleaned not in seen_goggles:
                normalized_goggles.append(cleaned)
                seen_goggles.add(cleaned)
        self.goggles = normalized_goggles
        return self


class SearchProviderOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brave: BraveSearchOptions | None = None


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    intent: SearchIntent = "general"
    freshness: Freshness | None = None
    preferences: SearchPreferences = Field(default_factory=SearchPreferences)
    provider_options: SearchProviderOptions = Field(default_factory=SearchProviderOptions)
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
        preferences: dict[str, object] | None = None,
        provider_options: dict[str, object] | None = None,
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
                "preferences": dict(preferences or {}),
                "provider_options": dict(provider_options or {}),
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
    def normalize_search_request(self) -> "SearchRequest":
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

        if self.provider_options.brave and self.provider_options.brave.goggles and self.provider != "brave":
            raise ValueError("provider_options.brave requires provider='brave'")

        return self


class ExtractRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

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
