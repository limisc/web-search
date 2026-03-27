from __future__ import annotations

import importlib


REGISTER_MODULES = (
    "web_search.tools.web_search",
    "web_search.tools.web_extract",
)


def register_tools() -> None:
    for module_name in REGISTER_MODULES:
        importlib.import_module(module_name)
