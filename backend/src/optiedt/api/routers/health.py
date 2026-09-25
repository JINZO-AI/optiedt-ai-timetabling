"""Liveness, readiness and Prometheus metrics."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func, select, text

from optiedt import __version__
from optiedt.api.deps import DbSession, PrincipalDep
from optiedt.api.metrics import QUEUE_OLDEST, SOLVER_RUNS, WORKERS_ALIVE
from optiedt.db.migrate import current_revision, head_revision
from optiedt.models import SolverRun, WorkerHeartbeat
from optiedt.security.permissions import Permission
from optiedt.services.runs import SOLVER_VERSION

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
    counts: dict[str, int] = dict(
        db.execute(select(SolverRun.status, func.count()).group_by(SolverRun.status)).all()
    )
    for status in ("queued", "running", "succeeded", "failed", "cancelled"):
        SOLVER_RUNS.labels(status).set(counts.get(status, 0))
    threshold = datetime.now(UTC) - timedelta(minutes=1)
    alive = db.scalar(
        select(func.count())
        .select_from(WorkerHeartbeat)
        .where(WorkerHeartbeat.last_seen_at > threshold)
    )
    WORKERS_ALIVE.set(alive or 0)
    oldest = db.scalar(select(func.min(SolverRun.requested_at)).where(SolverRun.status == "queued"))
    QUEUE_OLDEST.set((datetime.now(UTC) - oldest).total_seconds() if oldest else 0)


@router.get("/metrics", include_in_schema=False)
def metrics(db: DbSession) -> Response:
    try:
        refresh_gauges(db)
    except Exception:
        logger.exception("could not refresh metric gauges")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/system/status", summary="Versions, database schema, workers and the run queue")
def system_status(db: DbSession, principal: PrincipalDep) -> dict[str, object]:
    principal.require(Permission.SYSTEM_READ)
    now = datetime.now(UTC)
    workers = [
        {
            "worker_id": w.worker_id,
            "hostname": w.hostname,
            "version": w.version,
            "started_at": w.started_at.isoformat(),
            "last_seen_at": w.last_seen_at.isoformat(),
            "alive": w.last_seen_at > now - timedelta(minutes=1),
            "current_run_id": str(w.current_run_id) if w.current_run_id else None,
        }
        for w in db.scalars(select(WorkerHeartbeat).order_by(WorkerHeartbeat.worker_id))
    ]
    counts = dict(
        db.execute(
            select(SolverRun.status, func.count())
            .where(SolverRun.status.in_(("queued", "running")))
            .group_by(SolverRun.status)
        ).all()
    )
    oldest = db.scalar(select(func.min(SolverRun.requested_at)).where(SolverRun.status == "queued"))
    failed = db.scalar(
        select(func.count())
        .select_from(SolverRun)
        .where(SolverRun.status == "failed", SolverRun.finished_at > now - timedelta(days=1))
    )
    revision = current_revision(db.connection())
    return {
        "version": __version__,
        "solver_version": SOLVER_VERSION,
        "schema": {"revision": revision, "expected": head_revision()},
        "workers": workers,
        "queue": {
            "queued": counts.get("queued", 0),
            "running": counts.get("running", 0),
            "oldest_queued_seconds": round((now - oldest).total_seconds()) if oldest else 0,
            "failed_last_day": failed or 0,
        },
    }
