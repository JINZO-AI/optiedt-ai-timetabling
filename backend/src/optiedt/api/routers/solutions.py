"""Timetable solutions: listing, timetable views, evaluation, comparison, explanations and
the runs requested from a solution (repair, diagnosis)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from optiedt.api.deps import DbSession, PageDep, PrincipalDep
from optiedt.api.idempotency import IdempotencyKey, perform
from optiedt.api.schemas import scheduling as s
from optiedt.api.schemas.common import Page
from optiedt.services import runs, solutions

router = APIRouter(tags=["solutions"])


@router.get("/terms/{term_id}/solutions", response_model=Page[s.SolutionOut])
def list_solutions(
    term_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    status: Annotated[str | None, Query(max_length=24)] = None,
    run_id: uuid.UUID | None = None,
) -> Page[s.SolutionOut]:
    items, total = solutions.list_solutions(
        db,
        principal,
        term_id,
        status=status,
        run_id=run_id,
        offset=paging.offset,
        limit=paging.page_size,
    )
    return Page(
        items=[s.SolutionOut.model_validate(x) for x in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.get("/solutions/compare", response_model=s.CompareOut)
def compare_solutions(
    db: DbSession,
    principal: PrincipalDep,
    ids: Annotated[list[uuid.UUID], Query(min_length=2, max_length=6)],
    profile: Annotated[str | None, Query(max_length=32)] = None,
) -> s.CompareOut:
    return s.CompareOut.model_validate(solutions.compare(db, principal, ids, profile))


@router.get("/solutions/{solution_id}", response_model=s.SolutionOut)
def get_solution(solution_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.SolutionOut:
    solutions.require_read(principal)
    return s.SolutionOut.model_validate(solutions.get_solution(db, solution_id))


@router.get("/solutions/{solution_id}/timetable", response_model=s.TimetableOut)
def get_timetable(solution_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.TimetableOut:
    return s.TimetableOut.model_validate(solutions.timetable(db, principal, solution_id))


@router.get("/solutions/{solution_id}/evaluation", response_model=s.EvaluationOut)
def get_evaluation(
    solution_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> s.EvaluationOut:
    solutions.require_read(principal)
    solution = solutions.get_solution(db, solution_id)
    return s.EvaluationOut.model_validate(solution.evaluation)


@router.get("/solutions/{solution_id}/unscheduled/{session_id}", response_model=s.ExplanationOut)
def explain_unscheduled(
    solution_id: uuid.UUID, session_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> s.ExplanationOut:
    """Why a session is not in the timetable, and where it could still go."""
    return s.ExplanationOut.model_validate(
        solutions.explanation(db, principal, solution_id, str(session_id))
    )


@router.post("/solutions/{solution_id}/reoptimize", response_model=s.RunOut, status_code=202)
def reoptimize(
    solution_id: uuid.UUID,
    body: s.SolutionRunIn,
    db: DbSession,
    principal: PrincipalDep,
    idempotency_key: IdempotencyKey = None,
) -> JSONResponse:
    """Repairs the timetable against the current data, moving as little as possible."""

    def action() -> tuple[int, object]:
        run = runs.request_solution_run(
            db,
            principal,
            solution_id,
            kind="repair",
            time_limit_seconds=body.time_limit_seconds,
            mode=body.mode,
            scope_department_ids=body.scope_department_ids,
        )
        db.flush()
        db.refresh(run)
        return 202, s.RunOut.model_validate(run).model_dump(mode="json")

    return perform(
        db,
        principal,
        idempotency_key,
        f"solution-reoptimize:{solution_id}",
        body.model_dump(mode="json"),
        action,
    )


@router.post("/solutions/{solution_id}/relaxation", response_model=s.RunOut, status_code=202)
def diagnose(
    solution_id: uuid.UUID,
    body: s.DiagnosisIn,
    db: DbSession,
    principal: PrincipalDep,
    idempotency_key: IdempotencyKey = None,
) -> JSONResponse:
    """Finds the cheapest set of data changes that would let every session be placed."""

    def action() -> tuple[int, object]:
        run = runs.request_solution_run(
            db,
            principal,
            solution_id,
            kind="relaxation",
            time_limit_seconds=body.time_limit_seconds,
        )
        db.flush()
        db.refresh(run)
        return 202, s.RunOut.model_validate(run).model_dump(mode="json")

    return perform(
        db,
        principal,
        idempotency_key,
        f"solution-relaxation:{solution_id}",
        body.model_dump(mode="json"),
        action,
    )
