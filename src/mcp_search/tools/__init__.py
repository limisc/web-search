from __future__ import annotations

import importlib


REGISTER_MODULES = (
    "mcp_search.tools.web_search",
    "mcp_search.tools.web_extract",
)


def register_tools() -> None:
    for module_name in REGISTER_MODULES:
        importlib.import_module(module_name)
