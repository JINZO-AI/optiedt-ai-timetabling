"""The FastAPI application."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from optiedt import __version__
from optiedt.api.middleware import RequestContextMiddleware
from optiedt.api.problems import install_problem_handlers
from optiedt.api.routers import (
    audit,
    auth,
    health,
    imports,
    publications,
    reference,
    scheduling,
    solutions,
    terms,
    users,
)
from optiedt.config import Settings, get_settings
from optiedt.logging_setup import configure_logging

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)

    app = FastAPI(
        title="OptiEDT",
        version=__version__,
        summary="Academic scheduling and optimization platform",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    install_problem_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(health.router)
    api.include_router(auth.router)
    for router in _domain_routers():
        api.include_router(router)
    app.include_router(api)

    app.add_middleware(RequestContextMiddleware, max_body_bytes=settings.max_upload_bytes)
    return app


def _domain_routers() -> list[APIRouter]:
    return [
        users.router,
        audit.router,
        *reference.routers,
        terms.router,
        terms.catalog_router,
        scheduling.router,
        solutions.router,
        publications.router,
        imports.router,
    ]
