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

⚠️ **`secret_key` still defaults to `change-me-in-env`.** A deployment that
does not set `OPTIEDT_SECRET_KEY` signs its tokens with a value published in
this repository, so anyone can mint one. Authentication makes the application
safe to demonstrate, not safe to expose.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from optiedt.api.routers import auth, availability, candidates, instance, runs

API_PREFIX = "/api"

app = FastAPI(
    title="OptiEDT",
    version="0.1.0",
    summary="Generates, ranks and explains weekly university timetables",
    docs_url=f"{API_PREFIX}/docs",
    openapi_url=f"{API_PREFIX}/openapi.json",
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
app.include_router(_api)


@app.get(f"{API_PREFIX}/health", tags=["meta"], summary="Liveness")
def health() -> dict[str, str]:
    return {"status": "ok"}
