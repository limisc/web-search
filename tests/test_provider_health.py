from __future__ import annotations

import pytest

from web_search.config import clear_settings_cache
from web_search.services.provider_health import get_provider_health


@pytest.fixture(autouse=True)
def clear_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    monkeypatch.setenv("BRAVE_API_KEY", "")
    monkeypatch.setenv("EXA_API_KEY", "")
    monkeypatch.setenv("NEWSAPI_API_KEY", "")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")
    clear_settings_cache()


def test_provider_health_marks_missing_config_by_default() -> None:
    health = get_provider_health("tavily")
    assert health.status == "missing_config"
    assert health.is_healthy is False


def test_provider_health_marks_configured_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    clear_settings_cache()

    health = get_provider_health("exa")
    assert health.status == "configured"
    assert health.is_healthy is True
