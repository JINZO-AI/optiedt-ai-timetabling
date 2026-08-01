"""The FastAPI application.

Everything is served under `/api`, which is what `frontend/vite.config.ts`
proxies to this process in development. The generated OpenAPI page at
`/api/docs` IS the API reference — there is no hand-written copy to fall out of
date with it.

⚠️ **No authentication yet.** Authentication, roles and rights are FR-11 and
belong to Phase 5 (`docs/dashboard.md`). Until they land, every endpoint here
is open, so this application must not be exposed beyond a development machine.
The teacher id is taken from the path rather than from a token for the same
reason, and that is exactly the line Phase 5 moves.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from optiedt.api.routers import availability, instance

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
_api.include_router(instance.router)
_api.include_router(availability.router)
app.include_router(_api)


@app.get(f"{API_PREFIX}/health", tags=["meta"], summary="Liveness")
def health() -> dict[str, str]:
    return {"status": "ok"}
