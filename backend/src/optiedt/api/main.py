"""The FastAPI application.

Everything is served under `/api`, which is what `frontend/vite.config.ts`
proxies to this process in development. The generated OpenAPI page at
`/api/docs` IS the API reference — there is no hand-written copy to fall out of
date with it.

**Authenticated since Phase 5 M4 (FR-11).** Every endpoint but `/health` and
`/auth/token` requires a bearer token, and the rights are
`docs/domain-model.md`'s table, which SRS Table 2 governs (C-8):

- launching a run is the **person in charge**;
- a **teacher** reaches only their own availability, and which teacher they
  are comes from the TOKEN rather than the path — the line Phase 4 explicitly
  left for this milestone;
- reading the instance, runs and candidates needs only a valid account.

⚠️ **Accounts come from a seed command**, not a registration screen — C-18.
Account management through the interface is NOT delivered by Phase 5; the
administrator's right to it from SRS Table 2 stays unimplemented.

⚠️ **`secret_key` still defaults to `change-me-in-env`**, deliberately, so the
suite and a local demonstration need no configuration at all. A deployment that
does not set `OPTIEDT_SECRET_KEY` would sign its tokens with a value published
in this repository, so anyone could mint one.

✅ **Since 2026-08-07 that can no longer reach a deployment silently.** Setting
`OPTIEDT_ENVIRONMENT=production` makes start-up REFUSE the published default
(`Settings.require_deployable`, called in the lifespan below). The application
is still *safe to demonstrate rather than safe to expose* — the guard removes
the silent failure, it does not make the default acceptable.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from optiedt.api.routers import (
    assistant,
    auth,
    availability,
    candidates,
    instance,
    publications,
    runs,
)
from optiedt.core.config import Settings

API_PREFIX = "/api"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Refuse to start a PRODUCTION deployment on the published secret key.

    ⚠️ Deliberately at start-up rather than per request. A configuration fault
    that only surfaces when someone signs in is a fault that reaches users; this
    one stops the process before it serves anything.

    `Settings()` is constructed here rather than taken from `deps.get_settings`
    so the guard does not depend on the dependency cache being warm - the check
    has to run even if no request ever arrives.
    """
    Settings().require_deployable()
    yield


app = FastAPI(
    title="OptiEDT",
    version="0.1.0",
    summary="Generates, ranks and explains weekly university timetables",
    docs_url=f"{API_PREFIX}/docs",
    openapi_url=f"{API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Vite proxies /api, so same-origin holds in development and CORS is not
# strictly needed. It is enabled for the dev origin only, so that running the
# frontend against a differently-hosted API does not fail in a way that looks
# like a routing bug.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_api = APIRouter(prefix=API_PREFIX)
_api.include_router(auth.router)
_api.include_router(instance.router)
_api.include_router(availability.router)
_api.include_router(runs.router)
_api.include_router(candidates.router)
_api.include_router(publications.router)
# ⚠️ Registered unconditionally, even though the service is off by default.
# Gating the routes on `assistant_enabled` would make the interface 404 rather
# than fall back, and the fallback IS the specified behaviour: only text
# disappears (invariant 5). The routes answer 200 with the computed form.
_api.include_router(assistant.router)
app.include_router(_api)


@app.get(f"{API_PREFIX}/health", tags=["meta"], summary="Liveness")
def health() -> dict[str, str]:
    return {"status": "ok"}
