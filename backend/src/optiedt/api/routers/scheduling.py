"""Scenarios and solver runs."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from optiedt.api.deps import DbSession, PageDep, PrincipalDep
from optiedt.api.idempotency import IdempotencyKey, perform
from optiedt.api.schemas import scheduling as s
from optiedt.api.schemas.common import Page
from optiedt.errors import Conflict
from optiedt.services import runs, scenarios
from optiedt.services.scenarios import require_scheduling

router = APIRouter(tags=["scenarios and runs"])


# ── scenarios ──────────────────────────────────────────────────────────


@router.get("/terms/{term_id}/scenarios", response_model=list[s.ScenarioOut])
def list_scenarios(
    term_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    include_archived: bool = False,
) -> list[s.ScenarioOut]:
    items = scenarios.list_scenarios(db, principal, term_id, include_archived=include_archived)
    return [s.ScenarioOut.model_validate(x) for x in items]


@router.post("/terms/{term_id}/scenarios", response_model=s.ScenarioOut, status_code=201)
def create_scenario(
    term_id: uuid.UUID, body: s.ScenarioIn, db: DbSession, principal: PrincipalDep
) -> s.ScenarioOut:
    scenario = scenarios.create_scenario(db, principal, term_id, body.model_dump())
    db.commit()
    db.refresh(scenario)
    return s.ScenarioOut.model_validate(scenario)


@router.get("/scenarios/{scenario_id}", response_model=s.ScenarioOut)
def get_scenario(scenario_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.ScenarioOut:
    scenarios.require_read(principal)
    return s.ScenarioOut.model_validate(scenarios.get_scenario(db, scenario_id))


@router.patch("/scenarios/{scenario_id}", response_model=s.ScenarioOut)
def update_scenario(
    scenario_id: uuid.UUID, body: s.ScenarioPatch, db: DbSession, principal: PrincipalDep
) -> s.ScenarioOut:
    scenario = scenarios.update_scenario(
        db, principal, scenario_id, version=body.version, values=body.changes()
    )
    db.commit()
    db.refresh(scenario)
    return s.ScenarioOut.model_validate(scenario)


@router.post("/scenarios/{scenario_id}/archive", response_model=s.ScenarioOut)
def archive_scenario(
    scenario_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> s.ScenarioOut:
    scenario = scenarios.archive_scenario(db, principal, scenario_id)
    db.commit()
    db.refresh(scenario)
    return s.ScenarioOut.model_validate(scenario)


@router.post(
    "/scenarios/{scenario_id}/runs",
    response_model=s.RunOut,
    status_code=202,
    responses={409: {"description": "A run of this scenario is already queued or running"}},
)
def request_run(
    scenario_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    idempotency_key: IdempotencyKey = None,
) -> JSONResponse:
    def action() -> tuple[int, object]:
        run = runs.request_scenario_run(db, principal, scenario_id)
        db.flush()
        db.refresh(run)
        return 202, s.RunOut.model_validate(run).model_dump(mode="json")

    return perform(db, principal, idempotency_key, f"scenario-runs:{scenario_id}", {}, action)


# ── runs ───────────────────────────────────────────────────────────────


@router.get("/terms/{term_id}/runs", response_model=Page[s.RunOut])
def list_runs(
    term_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    scenario_id: uuid.UUID | None = None,
    status: Annotated[str | None, Query(max_length=16)] = None,
) -> Page[s.RunOut]:
    items, total = runs.list_runs(
        db,
        principal,
        term_id,
        scenario_id=scenario_id,
        status=status,
        offset=paging.offset,
        limit=paging.page_size,
    )
    return Page(
        items=[s.RunOut.model_validate(r) for r in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.get("/runs/{run_id}", response_model=s.RunOut)
def get_run(run_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.RunOut:
    runs.require_read(principal)
    return s.RunOut.model_validate(runs.get_run(db, run_id))


@router.get("/runs/{run_id}/events", response_model=list[s.RunEventOut])
def list_run_events(
    run_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    after: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[s.RunEventOut]:
    events = runs.list_events(db, principal, run_id, after=after, limit=limit)
    return [s.RunEventOut.model_validate(e) for e in events]


@router.post("/runs/{run_id}/cancel", response_model=s.RunOut)
def cancel_run(run_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.RunOut:
    run = runs.cancel_run(db, principal, run_id)
    db.commit()
    db.refresh(run)
    return s.RunOut.model_validate(run)


@router.get("/runs/{run_id}/log", response_class=PlainTextResponse)
def get_run_log(run_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> str:
    """The end of the CP-SAT search log, for support and investigation."""
    run = runs.get_run(db, run_id)
    require_scheduling(
        principal, [uuid.UUID(d) for d in run.config.get("scope_department_ids", [])]
    )
    return run.log or ""


@router.get("/runs/{run_id}/diagnosis", response_model=s.DiagnosisOut)
def get_diagnosis(run_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.DiagnosisOut:
    runs.require_read(principal)
    run = runs.get_run(db, run_id)
    if run.kind != "relaxation":
        raise Conflict("This run is not a diagnosis.", code="not_a_diagnosis")
    if run.status not in ("succeeded", "cancelled") or "changes" not in run.result:
        raise Conflict("The diagnosis has not finished.", code="run_not_finished")
    result = run.result
    return s.DiagnosisOut(
        run_id=run.id,
        status=run.status,
        complete=result["complete"],
        unscheduled=result["unscheduled"],
        total_cost=result["total_cost"],
        changes=[s.ChangeOut.model_validate(c) for c in result["changes"]],
    )
