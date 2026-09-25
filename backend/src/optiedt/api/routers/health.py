"""Liveness, readiness and Prometheus metrics."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select, text

from optiedt.api.deps import DbSession
from optiedt.api.metrics import SOLVER_RUNS, WORKERS_ALIVE
from optiedt.db.migrate import current_revision, head_revision
from optiedt.models import SolverRun, WorkerHeartbeat

router = APIRouter(tags=["operations"])
logger = logging.getLogger(__name__)


@router.get("/health/live", summary="The process is running")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="The database is reachable and at the expected schema")
def ready(db: DbSession, response: Response) -> dict[str, object]:
    checks: dict[str, object] = {}
    ok = True
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
        revision = current_revision(db.connection())
        expected = head_revision()
        checks["schema"] = "ok" if revision == expected else f"at {revision}, expected {expected}"
        ok = revision == expected
    except Exception:
        logger.exception("readiness check failed")
        checks["database"] = "unreachable"
        ok = False
    if not ok:
        response.status_code = 503
    return {"status": "ok" if ok else "unavailable", "checks": checks}


def refresh_gauges(db: DbSession) -> None:
    counts: dict[str, int] = {
        status: count
        for status, count in db.execute(
            select(SolverRun.status, func.count()).group_by(SolverRun.status)
        )
    }
    for status in ("queued", "running", "succeeded", "failed", "cancelled"):
        SOLVER_RUNS.labels(status).set(counts.get(status, 0))
    threshold = datetime.now(UTC) - timedelta(minutes=1)
    alive = db.scalar(
        select(func.count()).select_from(WorkerHeartbeat).where(
            WorkerHeartbeat.last_seen_at > threshold
        )
    )
    WORKERS_ALIVE.set(alive or 0)


@router.get("/metrics", include_in_schema=False)
def metrics(db: DbSession) -> Response:
    try:
        refresh_gauges(db)
    except Exception:
        logger.exception("could not refresh metric gauges")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
