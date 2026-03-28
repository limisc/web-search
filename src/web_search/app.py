from __future__ import annotations

import argparse

import uvicorn

from web_search.config import get_settings
from web_search.logging import configure_logging
from web_search.server import build_http_app, mcp
from web_search.tools import register_tools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the web-search MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--path", default=None)
    return parser


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    register_tools()

    args = build_parser().parse_args()
    transport = args.transport
    host = args.host or settings.mcp_host
    port = args.port or settings.mcp_port
    path = args.path or settings.mcp_path

    if transport == "stdio":
        mcp.run()
        return

    app = build_http_app(path=path, stateless_http=settings.fastmcp_stateless_http)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
