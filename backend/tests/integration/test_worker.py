"""The solver worker end to end: queue, child process, progress, cancellation, recovery and
stored candidates, against the real database."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.config import Settings
from optiedt.models import Activity, Solution, SolutionAssignment, SolverRun, SolverRunEvent
from optiedt.problem.snapshot import session_id
from optiedt.services import runs, scenarios
from optiedt.services.run_results import solution_ids
from optiedt.worker import queue
from optiedt.worker.main import Worker
from tests import factories

pytestmark = pytest.mark.solver


def _scenario_run(db: Session, **values: object) -> SolverRun:
    _, term = factories.populated_term(db)
    admin = factories.admin_principal(db)
    scenario = scenarios.create_scenario(
        db,
        admin,
        term.id,
        {"name": "First draft", "profile_codes": ["balanced", "student_centred"], **values},
    )
    run = runs.request_scenario_run(db, admin, scenario.id)
    db.commit()
    return run


def _reload(db: Session, run_id: uuid.UUID) -> SolverRun:
    db.expire_all()
    run = db.get(SolverRun, run_id)
    assert run is not None
    return run


def _events(db: Session, run: SolverRun) -> list[str]:
    return list(
        db.scalars(
            select(SolverRunEvent.kind)
            .where(SolverRunEvent.run_id == run.id)
            .order_by(SolverRunEvent.id)
        )
    )


def test_a_run_is_solved_in_a_child_process_and_its_candidates_stored(
    db: Session, worker_sessions: Callable[[], Session], worker_settings: Settings
) -> None:
    run = _scenario_run(db, time_limit_seconds=5)
    worker = Worker(worker_settings, worker_sessions, worker_id="worker-1")
    assert worker.run_once()
    run = _reload(db, run.id)
    assert run.status == "succeeded", (run.error_code, run.error_message)
    assert run.finished_at is not None
    assert run.result["warnings"] == []
    assert run.log
    events = _events(db, run)
    assert events[:2] == ["queued", "started"]
    assert events[-1] == "succeeded"

    ids = solution_ids(run)
    assert len(ids) == 2
    for solution_id in ids:
        solution = db.get(Solution, solution_id)
        assert solution is not None
        assert solution.is_valid
        assert solution.origin == "solver"
        assert solution.status == "draft"
        assert solution.evaluation["solver_agrees"]
        assert solution.evaluation["violations"] == []
        placed = db.scalars(
            select(SolutionAssignment).where(SolutionAssignment.solution_id == solution_id)
        ).all()
        assert len(placed) == 3  # two lectures and one tutorial
    assert not worker.run_once()  # the queue is empty


def test_cancelling_a_running_run_keeps_the_best_timetable_found(
    db: Session,
    worker_sessions: Callable[[], Session],
    worker_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _scenario_run(db, time_limit_seconds=120)
    monkeypatch.setattr(queue, "renew", lambda *args, **kwargs: "cancel")
    Worker(worker_settings, worker_sessions, worker_id="worker-1").run_once()
    run = _reload(db, run.id)
    assert run.status == "cancelled", (run.error_code, run.error_message)
    for solution_id in solution_ids(run):
        solution = db.get(Solution, solution_id)
        assert solution is not None
        assert solution.hard_violation_count == 0


def test_a_worker_shutting_down_puts_its_run_back_in_the_queue(
    db: Session, worker_sessions: Callable[[], Session], worker_settings: Settings
) -> None:
    run = _scenario_run(db, time_limit_seconds=60)
    worker = Worker(worker_settings, worker_sessions, worker_id="worker-1")
    worker.stopping.set()
    worker.run_once()
    run = _reload(db, run.id)
    assert run.status == "queued"
    assert run.attempts == 0
    assert run.worker_id is None
    assert _events(db, run)[-1] == "requeued"


def test_expired_leases_are_requeued_then_failed(db: Session) -> None:
    run = _scenario_run(db)
    for attempt in (1, 2):
        claimed = queue.claim(db, f"worker-{attempt}", lease_seconds=60)
        assert claimed == run.id
        stored = _reload(db, run.id)
        stored.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        queue.recover_expired(db, max_attempts=2)
        db.refresh(stored)
        expected = "queued" if attempt == 1 else "failed"
        assert stored.status == expected
    assert stored.error_code == "worker_lost"


def test_a_locked_session_that_can_no_longer_stay_fails_the_run_with_the_reason(
    db: Session, worker_sessions: Callable[[], Session], worker_settings: Settings
) -> None:
    run = _scenario_run(db, time_limit_seconds=5)
    worker = Worker(worker_settings, worker_sessions, worker_id="worker-1")
    worker.run_once()
    db.expire_all()
    first = db.get(SolverRun, run.id)
    assert first is not None
    base_id = solution_ids(first)[0]
    activity = db.scalars(
        select(Activity).where(Activity.term_id == first.term_id, Activity.sessions_per_week == 2)
    ).one()
    lecture = db.get(SolutionAssignment, (base_id, session_id(activity.id, 1)))
    assert lecture is not None
    lecture.locked = True
    lecture.period = 0
    lecture.day = 0  # T100 is unavailable on Monday P1
    admin = factories.admin_principal(db)
    scenario = scenarios.create_scenario(
        db,
        admin,
        first.term_id,
        {"name": "From the draft", "profile_codes": ["balanced"], "base_solution_id": base_id},
    )
    second = runs.request_scenario_run(db, admin, scenario.id)
    db.commit()
    worker.run_once()
    db.expire_all()
    failed = db.get(SolverRun, second.id)
    assert failed is not None
    assert failed.status == "failed"
    assert failed.error_code == "invalid_pin"
    assert "cannot stay at Mon P1" in (failed.error_message or "")


def test_a_diagnosis_run_reports_changes(
    db: Session, worker_sessions: Callable[[], Session], worker_settings: Settings
) -> None:
    run = _scenario_run(db, time_limit_seconds=5)
    worker = Worker(worker_settings, worker_sessions, worker_id="worker-1")
    worker.run_once()
    db.expire_all()
    solved = db.get(SolverRun, run.id)
    assert solved is not None
    admin = factories.admin_principal(db)
    diagnosis = runs.request_solution_run(
        db, admin, solution_ids(solved)[0], kind="relaxation", time_limit_seconds=5
    )
    db.commit()
    worker.run_once()
    db.expire_all()
    done = db.get(SolverRun, diagnosis.id)
    assert done is not None
    assert done.status == "succeeded", (done.error_code, done.error_message)
    assert done.result["complete"]
    assert done.result["changes"] == []  # the timetable needs no relaxation
