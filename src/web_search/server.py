from __future__ import annotations

from json import JSONDecodeError
from typing import Any, cast

from fastmcp import FastMCP
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import ExceptionHandler

from web_search.models.requests import ExtractRequest, SearchRequest
from web_search.services.extract_service import ExtractService
from web_search.services.search_service import SearchService
from web_search.utils.errors import ProviderError

mcp = FastMCP(name="web-search")

_ERROR_STATUS_CODES = {
    "invalid_request": 400,
    "provider_not_supported": 400,
    "provider_not_implemented": 501,
    "provider_not_configured": 503,
    "provider_timeout": 504,
    "provider_unavailable": 503,
    "budget_exceeded": 429,
    "partial_results": 502,
}


def _error_response(
    *,
    error_type: str,
    message: str,
    status_code: int,
    provider: str | None = None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"type": error_type, "message": message}
    if provider and provider != "router":
        error["provider"] = provider
    if details:
        error["details"] = details
    return JSONResponse({"error": error}, status_code=status_code)


def _validation_error_message(exc: ValidationError) -> str:
    errors = exc.errors(include_url=False)
    if not errors:
        return "Invalid request"

    first_error = errors[0]
    loc = ".".join(str(part) for part in first_error.get("loc", ()) if part is not None)
    message = first_error.get("msg") or "Invalid request"
    if message.startswith("Value error, "):
        message = message.removeprefix("Value error, ")
    if loc:
        return f"Field '{loc}' {message}"
    return message


def _normalize_provider_error(exc: ProviderError) -> tuple[str, int]:
    error_type = exc.error_type

    if error_type in {"provider_connection_error", "provider_not_available", "provider_error"}:
        error_type = "provider_unavailable"
    elif error_type == "provider_http_error":
        status = exc.details.get("status_code")
        error_type = "provider_not_configured" if status in {401, 403} else "provider_unavailable"

    return error_type, _ERROR_STATUS_CODES.get(error_type, 502)


async def handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    validation_exc = cast(ValidationError, exc)
    return _error_response(
        error_type="invalid_request",
        message=_validation_error_message(validation_exc),
        status_code=_ERROR_STATUS_CODES["invalid_request"],
    )


async def handle_json_decode_error(_request: Request, _exc: Exception) -> JSONResponse:
    return _error_response(
        error_type="invalid_request",
        message="Request body must be valid JSON",
        status_code=_ERROR_STATUS_CODES["invalid_request"],
    )


async def handle_provider_error(_request: Request, exc: Exception) -> JSONResponse:
    provider_exc = cast(ProviderError, exc)
    error_type, status_code = _normalize_provider_error(provider_exc)
    return _error_response(
        error_type=error_type,
        message=str(provider_exc),
        provider=provider_exc.provider,
        details=provider_exc.details,
        status_code=status_code,
    )


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
    exception_handlers: dict[Any, ExceptionHandler] = {
        ValidationError: handle_validation_error,
        JSONDecodeError: handle_json_decode_error,
        ProviderError: handle_provider_error,
    }
    app = Starlette(routes=routes, exception_handlers=exception_handlers)
    app.mount("/", mcp_app)
    return app
