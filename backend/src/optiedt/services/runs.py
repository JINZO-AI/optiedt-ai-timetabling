"""Requesting, following and cancelling solver runs.

A run row is also the job the worker claims (ADR 0003). Its configuration holds everything the
worker needs besides the snapshot (profiles, pins, reference, hint), copied at request time, so
a run is reproducible even after its base timetable is edited.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import version
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from optiedt import __version__
from optiedt.config import get_settings
from optiedt.errors import Conflict, FieldError, InvalidInput, NotFound, PermissionDenied
from optiedt.models import Scenario, SolverRun, SolverRunEvent
from optiedt.problem.data_checks import check_data
from optiedt.problem.encoding import EncodedPlacements
from optiedt.problem.model import Problem, build_problem
from optiedt.problem.snapshot import Snapshot
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import page
from optiedt.services.scenarios import get_scenario, require_scheduling
from optiedt.services.snapshots import compile_snapshot, store_snapshot
from optiedt.services.solutions import encoded_placements, get_solution
from optiedt.services.terms import get_term

ACTIVE = ("queued", "running")
SOLVER_VERSION = version("ortools")
STABILITY_TIER = 1


def require_read(principal: Principal) -> None:
    if not (principal.can(Permission.SOLUTIONS_READ) or principal.can(Permission.SCHEDULING_RUN)):
        raise PermissionDenied()


def get_run(db: Session, run_id: uuid.UUID) -> SolverRun:
    run = db.get(SolverRun, run_id)
    if run is None:
        raise NotFound("Run")
    return run


def list_runs(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    *,
    scenario_id: uuid.UUID | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[Sequence[SolverRun], int]:
    require_read(principal)
    get_term(db, term_id)
    statement: Select[SolverRun] = select(SolverRun).where(SolverRun.term_id == term_id)
    if scenario_id is not None:
        statement = statement.where(SolverRun.scenario_id == scenario_id)
    if status is not None:
        statement = statement.where(SolverRun.status == status)
    return page(db, statement.order_by(SolverRun.requested_at.desc()), offset=offset, limit=limit)


def list_events(
    db: Session, principal: Principal, run_id: uuid.UUID, *, after: int = 0, limit: int = 200
) -> list[SolverRunEvent]:
    require_read(principal)
    get_run(db, run_id)
    return list(
        db.scalars(
            select(SolverRunEvent)
            .where(SolverRunEvent.run_id == run_id, SolverRunEvent.id > after)
            .order_by(SolverRunEvent.id)
            .limit(limit)
        )
    )


# ── requesting ─────────────────────────────────────────────────────────


def _snapshot(db: Session, term_id: uuid.UUID) -> tuple[uuid.UUID, Snapshot, Problem]:
    snapshot = compile_snapshot(db, term_id)
    problem = build_problem(snapshot)
    blocking = [i for i in check_data(problem) if i.code == "too_many_atoms"]
    if blocking:
        raise InvalidInput(
            "The student groups are too finely divided to schedule: " + blocking[0].message,
            code="data_not_schedulable",
        )
    row = store_snapshot(db, term_id, snapshot)
    return row.id, snapshot, problem


def _profiles(
    snapshot: Snapshot, codes: Sequence[str], with_stability: bool
) -> list[dict[str, Any]]:
    by_code = {p.code: p for p in snapshot.profiles}
    result = []
    for code in codes:
        profile = by_code.get(code)
        if profile is None:
            raise InvalidInput(
                "An objective profile of the scenario no longer exists.",
                [FieldError("profile_codes", code)],
            )
        objectives = {
            name: [setting.tier, setting.weight]
            for name, setting in profile.objectives.items()
            if setting.enabled
        }
        if with_stability:
            objectives["stability"] = [STABILITY_TIER, 1]
        result.append({"code": profile.code, "name": profile.name, "objectives": objectives})
    return result


def _scope_pins(
    problem: Problem,
    base: EncodedPlacements,
    scope_department_ids: Sequence[uuid.UUID],
) -> tuple[EncodedPlacements, list[str]]:
    """Sessions of departments outside the scope stay as in the base timetable: placed ones
    are pinned, unplaced ones stay out."""
    if not scope_department_ids:
        return {}, []
    scope = {str(d) for d in scope_department_ids}
    pins: EncodedPlacements = {}
    absent: list[str] = []
    for session in problem.sessions:
        if problem.activities[session.activity].department_id in scope:
            continue
        if session.id in base:
            pins[session.id] = base[session.id]
        else:
            absent.append(session.id)
    return pins, absent


def _refuse_if_active(db: Session, **where: Any) -> None:
    statement = select(SolverRun.id).where(SolverRun.status.in_(ACTIVE))
    for column, value in where.items():
        statement = statement.where(getattr(SolverRun, column) == value)
    active = db.scalar(statement.limit(1))
    if active is not None:
        raise Conflict(
            "A run for this is already queued or running.", code="run_active", run_id=str(active)
        )


def _new_run(
    db: Session,
    principal: Principal,
    *,
    term_id: uuid.UUID,
    kind: str,
    snapshot_id: uuid.UUID,
    config: dict[str, Any],
    scenario_id: uuid.UUID | None,
    source_solution_id: uuid.UUID | None,
    summary: str,
    department_ids: Sequence[uuid.UUID],
) -> SolverRun:
    run = SolverRun(
        term_id=term_id,
        scenario_id=scenario_id,
        source_solution_id=source_solution_id,
        kind=kind,
        snapshot_id=snapshot_id,
        config=config,
        status="queued",
        progress={},
        requested_by_id=principal.user_id,
        app_version=__version__,
        solver_version=SOLVER_VERSION,
    )
    db.add(run)
    db.flush()
    db.add(SolverRunEvent(run_id=run.id, kind="queued", payload={}))
    audit.record(
        db,
        principal,
        action=f"run.{kind}",
        entity_type="solver_run",
        entity_id=run.id,
        summary=summary,
        term_id=term_id,
        department_ids=department_ids,
    )
    return run


def request_scenario_run(db: Session, principal: Principal, scenario_id: uuid.UUID) -> SolverRun:
    scenario: Scenario = get_scenario(db, scenario_id)
    require_scheduling(principal, scenario.scope_department_ids)
    if scenario.archived_at is not None:
        raise Conflict("This scenario is archived.", code="scenario_archived")
    _refuse_if_active(db, scenario_id=scenario.id)
    snapshot_id, snapshot, problem = _snapshot(db, scenario.term_id)
    base: EncodedPlacements = {}
    locked: set[str] = set()
    if scenario.base_solution_id is not None:
        base, locked = encoded_placements(db, scenario.base_solution_id)
    pins, absent = _scope_pins(problem, base, scenario.scope_department_ids)
    pins.update({session_id: base[session_id] for session_id in locked})
    reference = base if scenario.minimize_changes else None
    config = {
        "kind": "optimize",
        "mode": scenario.solver_mode,
        "time_limit_seconds": scenario.time_limit_seconds,
        "seed": scenario.seed,
        "workers": get_settings().solver_workers,
        "profiles": _profiles(snapshot, scenario.profile_codes, reference is not None),
        "pins": pins,
        "absent": absent,
        "locked": sorted(locked),
        "reference": reference,
        "hint": base or None,
        "name": scenario.name,
        "scope_department_ids": [str(d) for d in scenario.scope_department_ids],
    }
    return _new_run(
        db,
        principal,
        term_id=scenario.term_id,
        kind="optimize",
        snapshot_id=snapshot_id,
        config=config,
        scenario_id=scenario.id,
        source_solution_id=scenario.base_solution_id,
        summary=f"Requested a run of scenario {scenario.name}",
        department_ids=scenario.scope_department_ids,
    )


def request_solution_run(
    db: Session,
    principal: Principal,
    solution_id: uuid.UUID,
    *,
    kind: str,
    time_limit_seconds: int,
    mode: str = "fastest",
    scope_department_ids: Sequence[uuid.UUID] = (),
) -> SolverRun:
    """``repair``: re-optimize a timetable against current data, changing as little as
    possible; ``relaxation``: diagnose which data changes would let everything be placed."""
    if kind not in ("repair", "relaxation"):
        raise InvalidInput("Unknown run kind.", [FieldError("kind", kind)])
    solution = get_solution(db, solution_id)
    require_scheduling(principal, scope_department_ids)
    ceiling = get_settings().solver_max_time_limit_seconds
    if not 5 <= time_limit_seconds <= ceiling:
        raise InvalidInput(
            "Invalid time limit.",
            [FieldError("time_limit_seconds", f"Choose between 5 and {ceiling} seconds.")],
        )
    if mode not in ("fastest", "reproducible"):
        raise InvalidInput("Invalid solving mode.", [FieldError("mode", mode)])
    _refuse_if_active(db, source_solution_id=solution.id, kind=kind)
    snapshot_id, snapshot, problem = _snapshot(db, solution.term_id)
    base, locked = encoded_placements(db, solution.id)
    config: dict[str, Any] = {
        "kind": kind,
        "mode": mode,
        "time_limit_seconds": time_limit_seconds,
        "seed": 1,
        "workers": get_settings().solver_workers,
        "hint": base or None,
        "name": solution.name,
        "scope_department_ids": [str(d) for d in scope_department_ids],
    }
    if kind == "repair":
        pins, absent = _scope_pins(problem, base, scope_department_ids)
        pins.update({session_id: base[session_id] for session_id in locked})
        objectives = dict(solution.objective_config.get("objectives", {}))
        objectives["stability"] = [STABILITY_TIER, 1]
        known = {p.code for p in snapshot.profiles}
        config |= {
            "profiles": [
                {
                    "code": solution.profile_code if solution.profile_code in known else "custom",
                    "name": solution.name,
                    "objectives": objectives,
                }
            ],
            "pins": pins,
            "absent": absent,
            "locked": sorted(locked),
            "reference": base,
        }
    summary = (
        f"Requested a repair of {solution.name}"
        if kind == "repair"
        else f"Requested a diagnosis of {solution.name}"
    )
    return _new_run(
        db,
        principal,
        term_id=solution.term_id,
        kind=kind,
        snapshot_id=snapshot_id,
        config=config,
        scenario_id=None,
        source_solution_id=solution.id,
        summary=summary,
        department_ids=scope_department_ids,
    )


def cancel_run(db: Session, principal: Principal, run_id: uuid.UUID) -> SolverRun:
    run = get_run(db, run_id)
    scope = [uuid.UUID(d) for d in run.config.get("scope_department_ids", [])]
    require_scheduling(principal, scope)
    if run.status == "queued":
        run.status = "cancelled"
        run.finished_at = datetime.now(UTC)
        db.add(SolverRunEvent(run_id=run.id, kind="cancelled", payload={}))
    elif run.status == "running":
        if not run.cancel_requested:
            run.cancel_requested = True
            db.add(SolverRunEvent(run_id=run.id, kind="cancel_requested", payload={}))
    else:
        raise Conflict("This run has already finished.", code="run_finished")
    db.flush()
    audit.record(
        db,
        principal,
        action="run.cancel",
        entity_type="solver_run",
        entity_id=run.id,
        summary=f"Cancelled run {run.config.get('name', run.id)}",
        term_id=run.term_id,
        department_ids=scope,
    )
    return run
