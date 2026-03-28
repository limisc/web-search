from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        self._entries[key] = CacheEntry(value=value, expires_at=time.time() + self.ttl_seconds)

    def clear(self) -> None:
        self._entries.clear()


def make_cache_key(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"
