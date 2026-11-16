"""
Global error handling.

Do kaam:
    1. Custom APIError class — jab hum explicitly error dena chahein
    2. Exception handlers — FastAPI ke through register, consistent
       JSON response deta hai

Response format (har error ke liye same):
    {
      "error": "short_code",
      "message": "human readable",
      "detail": "optional extra info"
    }
"""

import logging
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger("app.errors")


class APIError(Exception):
    """Custom API error — consistent format ke liye."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "api_error",
        detail: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.detail = detail


def _error_response(
    status_code: int,
    code: str,
    message: str,
    detail: Any = None,
) -> JSONResponse:
    body = {"error": code, "message": message}
    if detail is not None:
        body["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(app: FastAPI) -> None:
    """Saare error handlers register karo."""

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        logger.warning(
            "APIError | %s %s | %s | %s",
            request.method, request.url.path, exc.code, exc.message,
        )
        return _error_response(
            exc.status_code, exc.code, exc.message, exc.detail,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        # FastAPI/Starlette ke default HTTPException (404, 405, waghera)
        msg = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        logger.warning(
            "HTTPException | %s %s | %s | %s",
            request.method, request.url.path, exc.status_code, msg,
        )
        return _error_response(
            exc.status_code, "http_error", msg,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ):
        # Pydantic validation errors (422)
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(p) for p in first.get("loc", []))
        msg = first.get("msg", "Validation error")
        logger.warning(
            "ValidationError | %s %s | %s | %s",
            request.method, request.url.path, loc, msg,
        )
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            f"Invalid field: {loc}",
            detail=errors[:3],   # pehle 3 errors
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        # Aakhri safety — unexpected exceptions
        logger.exception(
            "Unhandled exception | %s %s",
            request.method, request.url.path,
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred. Please try again.",
        )