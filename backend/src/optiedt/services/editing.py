"""Editing draft timetables: moves checked by the independent evaluator, locks, placement
suggestions, copies, and the change log of every edit (docs/product/requirements.md §3.4)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, FieldError, InvalidInput, PermissionDenied
from optiedt.evaluation.evaluator import Evaluator
from optiedt.evaluation.suggest import options_for, rank
from optiedt.evaluation.types import Evaluation, Placement, Violation
from optiedt.models import Publication, Solution, SolutionAssignment, SolutionChange
from optiedt.problem.model import Problem
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import check_version
from optiedt.services.solutions import (
    Evaluated,
    create_solution,
    encoded_placements,
    evaluate,
    get_solution,
    require_read,
    store_evaluation,
    violation_json,
)

SUGGESTION_LIMIT = 20


@dataclass(frozen=True, slots=True)
class Move:
    session_id: str
    day: int | None
    """``None`` takes the session out of the timetable."""
    period: int | None
    room_id: str | None


@dataclass
class MovePreview:
    evaluated: Evaluated
    after: dict[int, Placement]
    evaluation: Evaluation
    introduced: list[Violation]
    resolved: list[Violation]
    moved: list[int]

    def as_json(self) -> dict[str, Any]:
        p, codec = self.evaluated.problem, self.evaluated.codec
        before = self.evaluated.evaluation
        return {
            "valid": not self.introduced,
            "introduced": [violation_json(p, codec, v) for v in self.introduced],
            "resolved": [violation_json(p, codec, v) for v in self.resolved],
            "tiers_before": before.tiers,
            "tiers_after": self.evaluation.tiers,
            "objective_deltas": {
                code: self.evaluation.objective_values[code] - value
                for code, value in before.objective_values.items()
                if self.evaluation.objective_values[code] != value
            },
            "rule_deltas": {
                rule_id: self.evaluation.rule_values.get(rule_id, 0) - value
                for rule_id, value in before.rule_values.items()
                if self.evaluation.rule_values.get(rule_id, 0) != value
            },
            "hard_violations_after": len(self.evaluation.violations),
            "complete_after": self.evaluation.complete,
        }


def _key(v: Violation) -> tuple[str, tuple[int, ...], str | None, int | None]:
    return (v.code, tuple(sorted(v.sessions)), v.rule_id, v.subject)


def require_editable(solution: Solution) -> None:
    if solution.status != "draft":
        raise Conflict(
            "Only drafts can be edited. Make a copy of this timetable to change it.",
            code="not_editable",
        )


def require_edit(principal: Principal, problem: Problem, sessions: Iterable[int]) -> None:
    scope = principal.scope(Permission.SOLUTIONS_EDIT)
    if scope.is_empty:
        raise PermissionDenied()
    if scope.everywhere:
        return
    departments = {
        uuid.UUID(problem.activities[problem.sessions[s].activity].department_id) for s in sessions
    }
    if not scope.covers_all(departments):
        raise PermissionDenied("You may only change sessions of your departments.")


def _decode(evaluated: Evaluated, moves: Sequence[Move]) -> tuple[dict[int, Placement], list[int]]:
    p, codec = evaluated.problem, evaluated.codec
    after = dict(evaluated.placements)
    moved: list[int] = []
    errors: list[FieldError] = []
    for position, move in enumerate(moves):
        s = codec.session_index.get(move.session_id)
        if s is None:
            errors.append(FieldError(f"moves[{position}].session_id", "Unknown session."))
            continue
        if s in moved:
            errors.append(FieldError(f"moves[{position}].session_id", "Moved twice."))
            continue
        moved.append(s)
        if move.day is None or move.period is None:
            after.pop(s, None)
            continue
        if not (0 <= move.day < p.n_days and 0 <= move.period < p.n_periods):
            errors.append(FieldError(f"moves[{position}]", "No such day and period."))
            continue
        room = None
        if move.room_id is not None:
            room = p.room_index.get(move.room_id)
            if room is None:
                errors.append(FieldError(f"moves[{position}].room_id", "Unknown room."))
                continue
        after[s] = Placement(p.slot(move.day, move.period), room)
    if errors:
        raise InvalidInput("The moves are invalid.", errors)
    return after, moved


def preview(db: Session, solution: Solution, moves: Sequence[Move]) -> MovePreview:
    evaluated = evaluate(db, solution)
    after, moved = _decode(evaluated, moves)
    evaluation = Evaluator(evaluated.problem, evaluated.config).evaluate(after)
    before_keys = {_key(v) for v in evaluated.evaluation.violations}
    after_keys = {_key(v) for v in evaluation.violations}
    return MovePreview(
        evaluated=evaluated,
        after=after,
        evaluation=evaluation,
        introduced=[v for v in evaluation.violations if _key(v) not in before_keys],
        resolved=[v for v in evaluated.evaluation.violations if _key(v) not in after_keys],
        moved=moved,
    )


def preview_moves(
    db: Session, principal: Principal, solution_id: uuid.UUID, moves: Sequence[Move]
) -> dict[str, Any]:
    require_read(principal)
    return preview(db, get_solution(db, solution_id), moves).as_json()


def _next_seq(db: Session, solution_id: uuid.UUID) -> int:
    current = db.scalar(
        select(func.max(SolutionChange.seq)).where(SolutionChange.solution_id == solution_id)
    )
    return int(current or 0) + 1


def _where(problem: Problem, placement: Placement | None) -> str:
    if placement is None:
        return "unscheduled"
    room = f" ({problem.rooms[placement.room].code})" if placement.room is not None else ""
    return f"{problem.slot_label(placement.slot)}{room}"


def _state(problem: Problem, placement: Placement | None) -> dict[str, Any] | None:
    if placement is None:
        return None
    return {
        "day": problem.day_of(placement.slot),
        "period": problem.period_of(placement.slot),
        "room_id": problem.rooms[placement.room].id if placement.room is not None else None,
    }


def apply_moves(
    db: Session,
    principal: Principal,
    solution_id: uuid.UUID,
    *,
    version: int,
    moves: Sequence[Move],
    reason: str | None = None,
    force: bool = False,
) -> tuple[Solution, dict[str, Any]]:
    """Applies the moves together. Moves that break hard requirements are refused unless
    ``force`` is given (placing anyway is a deliberate step; the draft then cannot be
    submitted until the problems are resolved)."""
    solution = get_solution(db, solution_id)
    require_editable(solution)
    check_version(solution, version, "timetable")
    result = preview(db, solution, moves)
    problem = result.evaluated.problem
    require_edit(principal, problem, result.moved)
    _, locked = encoded_placements(db, solution.id)
    blocked = [problem.sessions[s].id for s in result.moved if problem.sessions[s].id in locked]
    if blocked:
        raise Conflict("Unlock the sessions before moving them.", code="locked", sessions=blocked)
    if result.introduced and not force:
        raise Conflict(
            "The move breaks hard requirements.",
            code="move_invalid",
            preview=result.as_json(),
        )

    rows = {
        str(row.session_id): row
        for row in db.scalars(
            select(SolutionAssignment).where(SolutionAssignment.solution_id == solution.id)
        )
    }
    seq = _next_seq(db, solution.id)
    before_placements = result.evaluated.placements
    for s in result.moved:
        session = problem.sessions[s]
        activity = problem.activities[session.activity]
        old, new = before_placements.get(s), result.after.get(s)
        if old == new:
            continue
        row = rows.get(session.id)
        if new is None:
            if row is not None:
                db.delete(row)
        elif row is None:
            db.add(
                SolutionAssignment(
                    solution_id=solution.id,
                    session_id=uuid.UUID(session.id),
                    day=problem.day_of(new.slot),
                    period=problem.period_of(new.slot),
                    room_id=uuid.UUID(problem.rooms[new.room].id) if new.room is not None else None,
                )
            )
        else:
            row.day = problem.day_of(new.slot)
            row.period = problem.period_of(new.slot)
            row.room_id = uuid.UUID(problem.rooms[new.room].id) if new.room is not None else None
        rooms = {x.room for x in (old, new) if x is not None and x.room is not None}
        kind = "unschedule" if new is None else "place" if old is None else "move"
        db.add(
            SolutionChange(
                solution_id=solution.id,
                seq=seq,
                actor_id=principal.user_id,
                actor_label=principal.label,
                kind=kind,
                session_id=uuid.UUID(session.id),
                before=_state(problem, old),
                after=_state(problem, new),
                summary=(
                    f"{problem.describe_session(session)}: {_where(problem, old)} → "
                    f"{_where(problem, new)}"
                ),
                reason=reason,
                affected_instructor_ids=[
                    uuid.UUID(problem.instructors[i].id) for i in activity.instructors
                ],
                affected_group_ids=[uuid.UUID(problem.groups[g].id) for g in activity.groups],
                affected_room_ids=[uuid.UUID(problem.rooms[r].id) for r in sorted(rooms)],
            )
        )
        seq += 1
    db.flush()
    evaluated = Evaluated(
        result.evaluated.problem,
        result.evaluated.codec,
        result.evaluated.config,
        result.after,
        result.evaluation,
    )
    store_evaluation(solution, evaluated, _solver_extra(solution))
    db.flush()
    audit.record(
        db,
        principal,
        action="solution.edit",
        entity_type="solution",
        entity_id=solution.id,
        summary=f"Moved {len(result.moved)} session(s) in {solution.name}",
        reason=reason,
        term_id=solution.term_id,
    )
    return solution, result.as_json()


def _solver_extra(solution: Solution) -> dict[str, Any]:
    """Keeps the solver's own record on an edited solver timetable, marked as edited."""
    extra: dict[str, Any] = {"edited": True}
    if "solver" in solution.evaluation:
        extra["solver"] = solution.evaluation["solver"]
    return extra


def set_locks(
    db: Session,
    principal: Principal,
    solution_id: uuid.UUID,
    *,
    version: int,
    session_ids: Sequence[str],
    locked: bool,
    reason: str | None = None,
) -> Solution:
    """Locked sessions stay where they are in re-optimization and cannot be moved by hand
    until unlocked."""
    solution = get_solution(db, solution_id)
    require_editable(solution)
    check_version(solution, version, "timetable")
    evaluated = evaluate(db, solution)
    problem, codec = evaluated.problem, evaluated.codec
    indices = [codec.session_index.get(i) for i in session_ids]
    if any(i is None for i in indices):
        raise InvalidInput("Unknown session.", [FieldError("session_ids", "unknown")])
    require_edit(principal, problem, [i for i in indices if i is not None])
    rows = {
        str(row.session_id): row
        for row in db.scalars(
            select(SolutionAssignment).where(
                SolutionAssignment.solution_id == solution.id,
                SolutionAssignment.session_id.in_([uuid.UUID(i) for i in session_ids]),
            )
        )
    }
    missing = [i for i in session_ids if i not in rows]
    if missing:
        raise Conflict("Only placed sessions can be locked.", code="not_placed", sessions=missing)
    seq = _next_seq(db, solution.id)
    changed = 0
    for session_id in session_ids:
        row = rows[session_id]
        if row.locked == locked:
            continue
        row.locked = locked
        session = problem.sessions[codec.session_index[session_id]]
        db.add(
            SolutionChange(
                solution_id=solution.id,
                seq=seq,
                actor_id=principal.user_id,
                actor_label=principal.label,
                kind="lock" if locked else "unlock",
                session_id=uuid.UUID(session_id),
                summary=f"{'Locked' if locked else 'Unlocked'} {problem.describe_session(session)}",
                reason=reason,
            )
        )
        seq += 1
        changed += 1
    if changed:
        solution.updated_at = datetime.now(UTC)  # a lock change is an edit: bump the version
        db.flush()
        audit.record(
            db,
            principal,
            action="solution.lock" if locked else "solution.unlock",
            entity_type="solution",
            entity_id=solution.id,
            summary=f"{'Locked' if locked else 'Unlocked'} {changed} session(s) in {solution.name}",
            term_id=solution.term_id,
        )
    return solution


def suggestions(
    db: Session,
    principal: Principal,
    solution_id: uuid.UUID,
    session_id: str,
    limit: int = SUGGESTION_LIMIT,
) -> dict[str, Any]:
    """Every place the session could go, the valid ones best first by the lexicographic
    change of the solution's objective, and the best blocked ones with their reasons."""
    require_read(principal)
    solution = get_solution(db, solution_id)
    evaluated = evaluate(db, solution)
    problem, codec = evaluated.problem, evaluated.codec
    s = codec.session_index.get(session_id)
    if s is None:
        raise InvalidInput("Unknown session.", [FieldError("session_id", session_id)])
    evaluator = Evaluator(problem, evaluated.config)
    valid, blocked = rank(options_for(evaluator, evaluated.placements, s))

    def place(placement: Placement) -> dict[str, Any]:
        state = _state(problem, placement)
        assert state is not None
        return state

    return {
        "session_id": session_id,
        "current": _state(problem, evaluated.placements.get(s)),
        "valid": [
            {
                **place(o.placement),
                "is_current": o.is_current,
                "tier_deltas": list(o.tier_deltas),
                "objective_deltas": {k: v for k, v in o.objective_deltas.items() if v},
            }
            for o in valid[:limit]
        ],
        "blocked": [
            {
                **place(o.placement),
                "violations": [violation_json(problem, codec, v) for v in o.violations],
            }
            for o in blocked[:limit]
        ],
        "valid_count": len(valid),
        "blocked_count": len(blocked),
    }


def duplicate(
    db: Session, principal: Principal, solution_id: uuid.UUID, name: str | None = None
) -> Solution:
    """A new draft with the same placements and locks, derived from the given timetable."""
    principal.require(Permission.SOLUTIONS_EDIT)
    source = get_solution(db, solution_id)
    placements, locked = encoded_placements(db, source.id)
    base = source.base_publication_id
    if source.status == "published":
        base = db.scalar(
            select(Publication.id)
            .where(Publication.solution_id == source.id)
            .order_by(Publication.version_no.desc())
            .limit(1)
        )
    copy = create_solution(
        db,
        term_id=source.term_id,
        snapshot_id=source.snapshot_id,
        name=name or f"{source.name} (copy)",
        origin="copy",
        objective_config=source.objective_config,
        placements=placements,
        locked=locked,
        profile_code=source.profile_code,
        parent_id=source.id,
        created_by_id=principal.user_id,
    )
    copy.base_publication_id = base
    db.flush()
    audit.record(
        db,
        principal,
        action="solution.duplicate",
        entity_type="solution",
        entity_id=copy.id,
        summary=f"Copied {source.name} as {copy.name}",
        term_id=source.term_id,
    )
    return copy


def list_changes(
    db: Session, principal: Principal, solution_id: uuid.UUID, *, after: int = 0, limit: int = 200
) -> list[SolutionChange]:
    require_read(principal)
    get_solution(db, solution_id)
    return list(
        db.scalars(
            select(SolutionChange)
            .where(SolutionChange.solution_id == solution_id, SolutionChange.seq > after)
            .order_by(SolutionChange.seq)
            .limit(limit)
        )
    )
