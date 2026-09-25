"""RFC 9457 problem responses for every error the API can return."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import errors as pg_errors
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

from optiedt.context import request_id_var
from optiedt.errors import AppError

logger = logging.getLogger(__name__)

PROBLEM_TYPE_BASE = "https://docs.optiedt.app/problems/"


def problem_response(
    status: int,
    title: str,
    detail: str,
    code: str,
    errors: list[dict[str, str]] | None = None,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": PROBLEM_TYPE_BASE + code,
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "request_id": request_id_var.get(),
    }
    if errors:
        body["errors"] = errors
    if extra:
        body.update(extra)
    return JSONResponse(
        body, status_code=status, media_type="application/problem+json", headers=headers
    )


_TITLES = {
    400: "Bad request",
    401: "Not signed in",
    403: "Forbidden",
    404: "Not found",
    405: "Method not allowed",
    409: "Conflict",
    413: "Payload too large",
    415: "Unsupported media type",
    422: "Invalid input",
    429: "Too many requests",
    500: "Internal error",
}


def _integrity_detail(exc: IntegrityError) -> tuple[str, str]:
    orig = exc.orig
    if isinstance(orig, pg_errors.UniqueViolation):
        return "duplicate", "A record with the same identifying values already exists."
    if isinstance(orig, pg_errors.ForeignKeyViolation):
        return (
            "in_use",
            "This record is referenced by other records, or refers to a record that does not "
            "exist.",
        )
    if isinstance(orig, pg_errors.CheckViolation):
        return "invalid_value", "A value is outside its allowed range."
    return "conflict", "The change conflicts with existing data."


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = None
        if exc.status == 429 and "retry_after_seconds" in exc.details:
            headers = {"Retry-After": str(exc.details["retry_after_seconds"])}
        return problem_response(
            exc.status,
            _TITLES.get(exc.status, "Error"),
            exc.message,
            exc.code,
            errors=[{"field": e.field, "message": e.message} for e in exc.errors] or None,
            extra={"details": exc.details} if exc.details else None,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for error in exc.errors():
            location = [str(part) for part in error.get("loc", ()) if part not in ("body",)]
            errors.append({"field": ".".join(location), "message": str(error.get("msg", ""))})
        return problem_response(
            422, _TITLES[422], "Some fields are missing or invalid.", "invalid_input", errors
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else _TITLES.get(exc.status_code, "")
        return problem_response(
            exc.status_code,
            _TITLES.get(exc.status_code, "Error"),
            detail,
            f"http_{exc.status_code}",
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(StaleDataError)
    async def _stale(_: Request, __: StaleDataError) -> JSONResponse:
        return problem_response(
            409,
            _TITLES[409],
            "This record was changed by someone else. Reload it and apply your change again.",
            "stale_version",
        )

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        code, detail = _integrity_detail(exc)
        logger.info("integrity error mapped to 409: %s", code)
        return problem_response(409, _TITLES[409], detail, code)

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", exc_info=exc)
        return problem_response(
            500,
            _TITLES[500],
            "Something went wrong on the server. The error has been logged with the request "
            "identifier below.",
            "internal_error",
        )
