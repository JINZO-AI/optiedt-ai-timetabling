"""FR-13 — launch a generation and follow it.

`POST /runs` returns **202 with a run id and nothing else**. Solving the
reference instance takes around 150 seconds (`docs/status.md`), so no request
is held open for it: the client polls `GET /runs/{id}` and watches `state`
(docs/architecture.md, "The run lifecycle").

⚠️ The budget is **deterministic time, not seconds** (ADR-011). Wall-clock
bounds with parallel workers are not reproducible - workers race and a fixed
seed does not fix it. An interface that renders `deterministicBudget` as a
duration is making a promise the system does not make.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from optiedt.api.deps import ExecutorDep, InstanceDep, RunStoreDep, SettingsDep
from optiedt.api.schemas import RunCreatedOut, RunCreateIn, RunOut, RunSummaryOut
from optiedt.services.portfolio import catalogue_weights
from optiedt.services.runs import RunRecord, RunRequest, new_run_record

router = APIRouter(tags=["runs"])


def _require_run(store: RunStoreDep, run_id: str) -> RunRecord:
    record = store.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No run {run_id!r}")
    return record


@router.post(
    "/runs",
    response_model=RunCreatedOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Launch a generation; returns immediately",
)
def create_run(
    instance: InstanceDep,
    store: RunStoreDep,
    executor: ExecutorDep,
    settings: SettingsDep,
    payload: RunCreateIn | None = None,
) -> RunCreatedOut:
    request = payload or RunCreateIn()
    record = new_run_record(
        run_id=uuid.uuid4().hex[:12],
        request=RunRequest(
            seed=request.seed if request.seed is not None else settings.solver_seed,
            deterministic_budget=(
                request.deterministic_budget
                if request.deterministic_budget is not None
                else settings.solver_deterministic_budget
            ),
        ),
        # The catalogue is the authority on default weights, not a constant
        # here (docs/dashboard.md). One vector prices every candidate of this
        # run - see services/runs.py, RunRecord.weights.
        weights=catalogue_weights(instance),
    )
    store.create(record)
    executor.submit(record.run.id)
    return RunCreatedOut(run_id=record.run.id)


@router.get("/runs", response_model=list[RunSummaryOut], summary="Runs, newest first")
def list_runs(store: RunStoreDep) -> list[RunSummaryOut]:
    return [RunSummaryOut.of(r) for r in store.all()]


@router.get("/runs/{run_id}", response_model=RunOut, summary="One run, polled")
def read_run(store: RunStoreDep, run_id: str) -> RunOut:
    return RunOut.of(_require_run(store, run_id))
