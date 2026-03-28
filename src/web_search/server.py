from __future__ import annotations

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.services.extract_service import ExtractService
from web_search.services.search_service import SearchService

mcp = FastMCP(name="web-search")


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "web-search"})


async def api_web_search(request: Request) -> JSONResponse:
    payload = await request.json()
    req = SearchRequest.model_validate(payload)
    result = await SearchService().run(req)
    return JSONResponse(result.model_dump(mode="json"))


async def api_web_extract(request: Request) -> JSONResponse:
    payload = await request.json()
    req = ExtractRequest.model_validate(payload)
    result = await ExtractService().run(req)
    return JSONResponse(result.model_dump(mode="json"))


def build_http_app(path: str = "/mcp", stateless_http: bool = True) -> Starlette:
    mcp_app = mcp.http_app(path=path, stateless_http=stateless_http)
    routes = [
        Route("/api/web_search", endpoint=api_web_search, methods=["POST"]),
        Route("/api/web_extract", endpoint=api_web_extract, methods=["POST"]),
    ]
    app = Starlette(routes=routes)
    app.mount("/", mcp_app)
    return app
