from __future__ import annotations

from typing import Any


class ProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        error_type: str = "provider_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.error_type = error_type
        self.details = details or {}
