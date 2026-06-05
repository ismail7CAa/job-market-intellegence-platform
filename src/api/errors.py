"""Standard API error response helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_payload(error: str, message: str, details: dict[str, Any] | None = None) -> dict:
    """Build the stable API error contract."""
    return {
        "error": error,
        "message": message,
        "details": details or {},
    }


def api_error(
    status_code: int,
    error: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    """Raiseable HTTPException carrying the standard error contract."""
    return HTTPException(
        status_code=status_code,
        detail=error_payload(error, message, details),
    )


def error_response(
    status_code: int,
    error: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Return the standard error contract as a JSON response."""
    return JSONResponse(
        status_code=status_code,
        content=error_payload(error, message, details),
        headers=headers,
    )


def _normalize_http_detail(exc: StarletteHTTPException) -> dict:
    """Normalize legacy HTTPException details into the API error contract."""
    if isinstance(exc.detail, dict) and {"error", "message", "details"}.issubset(exc.detail):
        return exc.detail

    message = str(exc.detail or "Request failed.")
    error = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        429: "rate_limit_exceeded",
        500: "internal_error",
        503: "service_unavailable",
    }.get(exc.status_code, "http_error")
    return error_payload(error, message)


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """FastAPI/Starlette HTTP error handler using the standard contract."""
    return JSONResponse(
        status_code=exc.status_code,
        content=_normalize_http_detail(exc),
        headers=getattr(exc, "headers", None),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Request validation handler using the standard contract."""
    return error_response(
        status_code=422,
        error="validation_failed",
        message="Request validation failed.",
        details={"errors": exc.errors()},
    )
