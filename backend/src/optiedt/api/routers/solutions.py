"""Timetable solutions: listing, timetable views, evaluation, comparison, explanations and
the runs requested from a solution (repair, diagnosis)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from optiedt.api.deps import DbSession, PageDep, PrincipalDep
from optiedt.api.idempotency import IdempotencyKey, perform
from optiedt.api.schemas import publishing as p
from optiedt.api.schemas import scheduling as s
from optiedt.api.schemas.common import Page
from optiedt.services import editing, publications, runs, solutions

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


# ── editing ────────────────────────────────────────────────────────────


@router.post("/solutions/{solution_id}/moves", response_model=s.MovesOut)
def move_sessions(
    solution_id: uuid.UUID, body: s.MovesIn, db: DbSession, principal: PrincipalDep
) -> s.MovesOut:
    """Moves sessions together. ``dry_run`` only reports what would change; otherwise moves
    that break hard requirements are refused (409 ``move_invalid``) unless ``force``."""
    moves = [
        editing.Move(str(m.session_id), m.day, m.period, str(m.room_id) if m.room_id else None)
        for m in body.moves
    ]
    if body.dry_run:
        preview = editing.preview_moves(db, principal, solution_id, moves)
        return s.MovesOut(
            applied=False, preview=s.MovePreviewOut.model_validate(preview), solution=None
        )
    solution, preview = editing.apply_moves(
        db,
        principal,
        solution_id,
        version=body.version,
        moves=moves,
        reason=body.reason,
        force=body.force,
    )
    db.commit()
    db.refresh(solution)
    return s.MovesOut(
        applied=True,
        preview=s.MovePreviewOut.model_validate(preview),
        solution=s.SolutionOut.model_validate(solution),
    )


@router.get("/solutions/{solution_id}/suggestions", response_model=s.SuggestionsOut)
def suggest_places(
    solution_id: uuid.UUID,
    session_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
) -> s.SuggestionsOut:
    return s.SuggestionsOut.model_validate(
        editing.suggestions(db, principal, solution_id, str(session_id), limit)
    )


@router.put("/solutions/{solution_id}/locks", response_model=s.SolutionOut)
def set_locks(
    solution_id: uuid.UUID, body: s.LocksIn, db: DbSession, principal: PrincipalDep
) -> s.SolutionOut:
    solution = editing.set_locks(
        db,
        principal,
        solution_id,
        version=body.version,
        session_ids=[str(i) for i in body.session_ids],
        locked=body.locked,
        reason=body.reason,
    )
    db.commit()
    db.refresh(solution)
    return s.SolutionOut.model_validate(solution)


@router.get("/solutions/{solution_id}/changes", response_model=list[s.ChangeLogOut])
def list_changes(
    solution_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    after: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[s.ChangeLogOut]:
    changes = editing.list_changes(db, principal, solution_id, after=after, limit=limit)
    return [s.ChangeLogOut.model_validate(c) for c in changes]


@router.post("/solutions/{solution_id}/duplicate", response_model=s.SolutionOut, status_code=201)
def duplicate(
    solution_id: uuid.UUID, body: s.DuplicateIn, db: DbSession, principal: PrincipalDep
) -> s.SolutionOut:
    copy = editing.duplicate(db, principal, solution_id, body.name)
    db.commit()
    db.refresh(copy)
    return s.SolutionOut.model_validate(copy)


@router.post("/solutions/{solution_id}/rebase", response_model=s.SolutionOut, status_code=201)
def rebase(solution_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.SolutionOut:
    """A new draft on the current data and current publication, keeping this one's changes."""
    draft = publications.rebase(db, principal, solution_id)
    db.commit()
    db.refresh(draft)
    return s.SolutionOut.model_validate(draft)


# ── workflow ───────────────────────────────────────────────────────────


@router.post("/solutions/{solution_id}/submit", response_model=s.SolutionOut)
def submit(
    solution_id: uuid.UUID, body: s.WorkflowIn, db: DbSession, principal: PrincipalDep
) -> s.SolutionOut:
    solution = publications.submit(db, principal, solution_id, version=body.version, note=body.note)
    db.commit()
    db.refresh(solution)
    return s.SolutionOut.model_validate(solution)


@router.post("/solutions/{solution_id}/approve", response_model=s.SolutionOut)
def approve(
    solution_id: uuid.UUID, body: s.WorkflowIn, db: DbSession, principal: PrincipalDep
) -> s.SolutionOut:
    solution = publications.approve(
        db, principal, solution_id, version=body.version, note=body.note
    )
    db.commit()
    db.refresh(solution)
    return s.SolutionOut.model_validate(solution)


@router.post("/solutions/{solution_id}/return", response_model=s.SolutionOut)
def return_to_draft(
    solution_id: uuid.UUID, body: s.ReturnIn, db: DbSession, principal: PrincipalDep
) -> s.SolutionOut:
    solution = publications.return_to_draft(
        db, principal, solution_id, version=body.version, note=body.note
    )
    db.commit()
    db.refresh(solution)
    return s.SolutionOut.model_validate(solution)


@router.post("/solutions/{solution_id}/publish", response_model=p.PublicationOut, status_code=201)
def publish(
    solution_id: uuid.UUID,
    body: p.PublishIn,
    db: DbSession,
    principal: PrincipalDep,
    idempotency_key: IdempotencyKey = None,
) -> JSONResponse:
    def action() -> tuple[int, object]:
        publication = publications.publish(
            db, principal, solution_id, version=body.version, note=body.note
        )
        db.flush()
        db.refresh(publication)
        return 201, p.PublicationOut.model_validate(publication).model_dump(mode="json")

    return perform(
        db,
        principal,
        idempotency_key,
        f"solution-publish:{solution_id}",
        body.model_dump(mode="json"),
        action,
    )
