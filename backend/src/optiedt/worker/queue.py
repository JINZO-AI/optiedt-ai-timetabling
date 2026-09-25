"""Run-queue operations on the database, each in its own short transaction (ADR 0003)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from optiedt import __version__
from optiedt.models import IdempotencyRecord, SolverRun, SolverRunEvent, WorkerHeartbeat

LeaseState = Literal["ok", "cancel", "lost"]


def _now() -> datetime:
    return datetime.now(UTC)


def claim(db: Session, worker_id: str, lease_seconds: int) -> uuid.UUID | None:
    """Takes the oldest queued run, if any, and marks it running under this worker."""
    run = db.scalar(
        select(SolverRun)
        .where(SolverRun.status == "queued")
        .order_by(SolverRun.requested_at, SolverRun.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if run is None:
        db.rollback()
        return None
    now = _now()
    run.status = "running"
    run.phase = "starting"
    run.started_at = run.started_at or now
    run.worker_id = worker_id
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    run.attempts += 1
    db.add(
        SolverRunEvent(
            run_id=run.id, kind="started", payload={"worker": worker_id, "attempt": run.attempts}
        )
    )
    db.commit()
    return run.id


def renew(db: Session, run_id: uuid.UUID, worker_id: str, lease_seconds: int) -> LeaseState:
    """Extends the lease; says whether cancellation was requested or the run was taken away."""
    run = db.get(SolverRun, run_id, with_for_update=True)
    if run is None or run.status != "running" or run.worker_id != worker_id:
        db.rollback()
        return "lost"
    now = _now()
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=lease_seconds)
    state: LeaseState = "cancel" if run.cancel_requested else "ok"
    db.commit()
    return state


def record_progress(db: Session, run_id: uuid.UUID, worker_id: str, event: dict[str, Any]) -> None:
    run = db.get(SolverRun, run_id)
    if run is None or run.worker_id != worker_id or run.status != "running":
        db.rollback()
        return
    run.phase = str(event.get("phase") or run.phase)
    run.progress = event
    db.add(SolverRunEvent(run_id=run_id, kind="progress", payload=event))
    db.commit()


def requeue(db: Session, run_id: uuid.UUID, worker_id: str, reason: str) -> None:
    """Puts a run this worker holds back in the queue without counting the attempt."""
    run = db.get(SolverRun, run_id, with_for_update=True)
    if run is None or run.worker_id != worker_id or run.status != "running":
        db.rollback()
        return
    run.status = "queued"
    run.phase = None
    run.worker_id = None
    run.lease_expires_at = None
    run.attempts = max(0, run.attempts - 1)
    db.add(SolverRunEvent(run_id=run_id, kind="requeued", payload={"reason": reason}))
    db.commit()


def fail(
    db: Session,
    run_id: uuid.UUID,
    worker_id: str,
    code: str,
    message: str,
    log: str | None = None,
) -> None:
    run = db.get(SolverRun, run_id, with_for_update=True)
    if run is None or run.worker_id != worker_id or run.status != "running":
        db.rollback()
        return
    run.status = "failed"
    run.error_code = code
    run.error_message = message
    run.finished_at = _now()
    run.lease_expires_at = None
    if log:
        run.log = log
    db.add(SolverRunEvent(run_id=run_id, kind="failed", payload={"code": code}))
    db.commit()


def recover_expired(db: Session, max_attempts: int) -> int:
    """Requeues runs whose worker stopped renewing its lease, or fails them after
    ``max_attempts`` claims."""
    now = _now()
    runs = db.scalars(
        select(SolverRun)
        .where(SolverRun.status == "running", SolverRun.lease_expires_at < now)
        .with_for_update(skip_locked=True)
    ).all()
    for run in runs:
        if run.attempts < max_attempts:
            run.status = "queued"
            run.phase = None
            run.worker_id = None
            run.lease_expires_at = None
            db.add(
                SolverRunEvent(
                    run_id=run.id,
                    kind="requeued",
                    payload={"reason": "The worker running it stopped responding."},
                )
            )
        else:
            run.status = "failed"
            run.error_code = "worker_lost"
            run.error_message = (
                f"The worker running this job stopped responding {run.attempts} times."
            )
            run.finished_at = now
            run.lease_expires_at = None
            db.add(SolverRunEvent(run_id=run.id, kind="failed", payload={"code": "worker_lost"}))
    db.commit()
    return len(runs)


def heartbeat(db: Session, worker_id: str, hostname: str, run_id: uuid.UUID | None) -> None:
    now = _now()
    statement = insert(WorkerHeartbeat).values(
        worker_id=worker_id,
        hostname=hostname,
        started_at=now,
        last_seen_at=now,
        current_run_id=run_id,
        version=__version__,
    )
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[WorkerHeartbeat.worker_id],
            set_={"last_seen_at": now, "current_run_id": run_id},
        )
    )
    db.commit()


def forget_worker(db: Session, worker_id: str) -> None:
    db.execute(delete(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == worker_id))
    db.commit()


def purge(db: Session, *, idempotency_hours: int = 24, heartbeat_hours: int = 24) -> None:
    """Housekeeping: forgets old idempotency records and workers long gone."""
    now = _now()
    db.execute(
        delete(IdempotencyRecord).where(
            IdempotencyRecord.created_at < now - timedelta(hours=idempotency_hours)
        )
    )
    db.execute(
        delete(WorkerHeartbeat).where(
            WorkerHeartbeat.last_seen_at < now - timedelta(hours=heartbeat_hours)
        )
    )
    db.commit()
