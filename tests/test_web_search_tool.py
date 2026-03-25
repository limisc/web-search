from __future__ import annotations

import pytest

from mcp_search.tools.web_search import web_search


@pytest.mark.asyncio
async def test_web_search_returns_validation_error_for_unsupported_provider() -> None:
    result = await web_search(query="hello", provider="exa")

    assert "error" in result
    assert result["error"]["type"] == "validation_error"
