"""Timetable solutions: storage, independent evaluation, timetable views, comparison and
explanations. Editing and the approval workflow live in ``services.editing``."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from optiedt.errors import FieldError, InvalidInput, NotFound, PermissionDenied
from optiedt.evaluation.evaluator import Evaluator
from optiedt.evaluation.explain import explain
from optiedt.evaluation.types import Evaluation, Violation
from optiedt.models import Solution, SolutionAssignment
from optiedt.problem.catalog import MAX_TIER, UNSCHEDULED
from optiedt.problem.encoding import Codec, EncodedPlacements
from optiedt.problem.model import Problem
from optiedt.problem.solution import ObjectiveConfig, Placement
from optiedt.security.permissions import Permission, Principal
from optiedt.services.crud import page
from optiedt.services.problems import problem_for

INSTRUCTOR_CODES = frozenset({"instructor_unavailable", "instructor_conflict"})
ROOM_CODES = frozenset(
    {
        "room_type",
        "room_features",
        "room_capacity",
        "campus",
        "building",
        "room_not_allowed",
        "room_unavailable",
        "room_conflict",
        "fixed_moved",
    }
)
MAX_COMPARED = 6


def require_read(principal: Principal) -> None:
    if not principal.can(Permission.SOLUTIONS_READ):
        raise PermissionDenied()


def get_solution(db: Session, solution_id: uuid.UUID) -> Solution:
    solution = db.get(Solution, solution_id)
    if solution is None:
        raise NotFound("Timetable")
    return solution


def list_solutions(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    *,
    status: str | None = None,
    run_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[Sequence[Solution], int]:
    require_read(principal)
    statement: Select[Solution] = select(Solution).where(Solution.term_id == term_id)
    if status is not None:
        statement = statement.where(Solution.status == status)
    if run_id is not None:
        statement = statement.where(Solution.run_id == run_id)
    statement = statement.order_by(Solution.created_at.desc(), Solution.name)
    return page(db, statement, offset=offset, limit=limit)


# ── placements and evaluation ──────────────────────────────────────────


def encoded_placements(db: Session, solution_id: uuid.UUID) -> tuple[EncodedPlacements, set[str]]:
    """``{session_id: [day, period, room_id]}`` and the locked session identifiers."""
    rows = db.scalars(
        select(SolutionAssignment).where(SolutionAssignment.solution_id == solution_id)
    )
    placements: EncodedPlacements = {}
    locked: set[str] = set()
    for row in rows:
        key = str(row.session_id)
        placements[key] = [row.day, row.period, str(row.room_id) if row.room_id else None]
        if row.locked:
            locked.add(key)
    return placements, locked


def objective_config(solution: Solution, codec: Codec) -> ObjectiveConfig:
    stored = solution.objective_config or {}
    objectives = {
        code: (int(tier), int(weight))
        for code, (tier, weight) in stored.get("objectives", {}).items()
    }
    reference = codec.placements(stored.get("reference")) if stored.get("reference") else None
    return ObjectiveConfig(objectives, reference)


@dataclass
class Evaluated:
    problem: Problem
    codec: Codec
    config: ObjectiveConfig
    placements: dict[int, Placement]
    evaluation: Evaluation


def evaluate(db: Session, solution: Solution) -> Evaluated:
    problem = problem_for(db, solution.snapshot_id)
    codec = Codec(problem)
    encoded, _ = encoded_placements(db, solution.id)
    placements = codec.placements(encoded)
    config = objective_config(solution, codec)
    return Evaluated(
        problem, codec, config, placements, Evaluator(problem, config).evaluate(placements)
    )


def _subject(problem: Problem, code: str, subject: int | None) -> tuple[str | None, str | None]:
    """Kind and identifier of the record a violation or obstacle is about."""
    if subject is None:
        return None, None
    if code in INSTRUCTOR_CODES:
        return "instructor", problem.instructors[subject].id
    if code == "students_unavailable":
        return "group", problem.groups[subject].id
    if code == "activity_unavailable":
        return "activity", problem.activities[subject].id
    if code in ROOM_CODES:
        return "room", problem.rooms[subject].id
    return None, None


def violation_json(problem: Problem, codec: Codec, violation: Violation) -> dict[str, Any]:
    kind, subject_id = _subject(problem, violation.code, violation.subject)
    return {
        "code": violation.code,
        "message": violation.message,
        "sessions": [problem.sessions[s].id for s in violation.sessions],
        "slots": [codec.slot(u) for u in violation.slots],
        "rule_id": violation.rule_id,
        "subject_kind": kind,
        "subject_id": subject_id,
    }


def evaluation_json(problem: Problem, codec: Codec, evaluation: Evaluation) -> dict[str, Any]:
    return {
        "tiers": evaluation.tiers,
        "objective_values": evaluation.objective_values,
        "rule_values": evaluation.rule_values,
        "unscheduled": [problem.sessions[s].id for s in evaluation.unscheduled],
        "violations": [violation_json(problem, codec, v) for v in evaluation.violations],
        "contributors": {
            code: [[label, value] for label, value in items]
            for code, items in evaluation.contributors.items()
        },
    }


def store_evaluation(solution: Solution, evaluated: Evaluated, extra: Mapping[str, Any]) -> None:
    evaluation = evaluated.evaluation
    solution.is_complete = evaluation.complete
    solution.hard_violation_count = len(evaluation.violations)
    solution.evaluation = {
        **evaluation_json(evaluated.problem, evaluated.codec, evaluation),
        **extra,
    }
    solution.evaluated_at = datetime.now(UTC)


def create_solution(
    db: Session,
    *,
    term_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    name: str,
    origin: str,
    objective_config: dict[str, Any],
    placements: EncodedPlacements,
    locked: AbstractSet[str] = frozenset(),
    profile_code: str | None = None,
    run_id: uuid.UUID | None = None,
    parent_id: uuid.UUID | None = None,
    created_by_id: uuid.UUID | None = None,
    evaluation_extra: Mapping[str, Any] | None = None,
) -> Solution:
    solution = Solution(
        term_id=term_id,
        snapshot_id=snapshot_id,
        run_id=run_id,
        parent_id=parent_id,
        name=name,
        origin=origin,
        profile_code=profile_code,
        objective_config=objective_config,
        status="draft",
        created_by_id=created_by_id,
    )
    db.add(solution)
    db.flush()
    db.add_all(
        SolutionAssignment(
            solution_id=solution.id,
            session_id=uuid.UUID(session_id),
            day=day,
            period=period,
            room_id=uuid.UUID(room_id) if room_id else None,
            locked=session_id in locked,
        )
        for session_id, (day, period, room_id) in placements.items()
    )
    db.flush()
    store_evaluation(solution, evaluate(db, solution), evaluation_extra or {})
    return solution


# ── views ──────────────────────────────────────────────────────────────


def timetable(db: Session, principal: Principal, solution_id: uuid.UUID) -> dict[str, Any]:
    require_read(principal)
    solution = get_solution(db, solution_id)
    problem = problem_for(db, solution.snapshot_id)
    encoded, locked = encoded_placements(db, solution_id)
    return timetable_payload(problem, encoded, locked, solution.evaluation.get("violations", []))


def timetable_payload(
    problem: Problem,
    encoded: EncodedPlacements,
    locked: set[str],
    violations: list[dict[str, Any]],
) -> dict[str, Any]:
    """The shape every timetable view filters (docs/design/api.md)."""
    snapshot = problem.snapshot
    sessions = []
    for session in problem.sessions:
        activity = problem.activities[session.activity]
        placed = encoded.get(session.id)
        sessions.append(
            {
                "id": session.id,
                "activity_id": activity.id,
                "occurrence": session.occurrence,
                "course_code": activity.course_code,
                "course_title": activity.course_title,
                "type": activity.type_code,
                "type_name": activity.type_name,
                "label": activity.label,
                "groups": [problem.groups[g].id for g in activity.groups],
                "instructors": [problem.instructors[i].id for i in activity.instructors],
                "duration": session.duration,
                "online": activity.online,
                "day": placed[0] if placed else None,
                "period": placed[1] if placed else None,
                "room_id": placed[2] if placed else None,
                "locked": session.id in locked,
            }
        )
    return {
        "grid": {
            "days": [{"index": d.index, "weekday": d.weekday} for d in snapshot.days],
            "periods": [
                {"index": p.index, "label": p.label, "start": p.start, "end": p.end}
                for p in snapshot.periods
            ],
            "closed": [[s.day, s.period] for s in snapshot.slots if s.closed],
        },
        "sessions": sessions,
        "unscheduled": [s["id"] for s in sessions if s["day"] is None],
        "resources": {
            "groups": {
                g.id: {
                    "code": g.code,
                    "name": g.name,
                    "size": g.size,
                    "parent_id": problem.groups[g.parent].id if g.parent is not None else None,
                }
                for g in problem.groups
            },
            "instructors": {i.id: {"code": i.code, "name": i.name} for i in problem.instructors},
            "rooms": {
                r.id: {"code": r.code, "name": r.name, "capacity": r.capacity}
                for r in problem.rooms
            },
        },
        "violations": violations,
    }


def tiers_under(problem: Problem, evaluation: Mapping[str, Any], profile_code: str) -> list[int]:
    """Tier vector of a stored evaluation under one of the snapshot's profiles."""
    profile = next((p for p in problem.snapshot.profiles if p.code == profile_code), None)
    if profile is None:
        raise InvalidInput("Unknown objective profile.", [FieldError("profile", profile_code)])
    values = evaluation.get("objective_values", {})
    rule_values = evaluation.get("rule_values", {})
    tiers = [0] * (MAX_TIER + 1)
    tiers[0] = int(values.get(UNSCHEDULED, 0))
    for code, setting in profile.objectives.items():
        if setting.enabled:
            tiers[setting.tier] += setting.weight * int(values.get(code, 0))
    for rule in problem.rules:
        if rule.enforcement == "soft":
            tiers[rule.tier] += rule.weight * int(rule_values.get(rule.id, 0))
    return tiers


def compare(
    db: Session,
    principal: Principal,
    solution_ids: Sequence[uuid.UUID],
    profile_code: str | None,
) -> dict[str, Any]:
    require_read(principal)
    if not 2 <= len(set(solution_ids)) <= MAX_COMPARED:
        raise InvalidInput(
            f"Compare between 2 and {MAX_COMPARED} timetables.", [FieldError("ids", "count")]
        )
    solutions = [get_solution(db, i) for i in dict.fromkeys(solution_ids)]
    if len({s.term_id for s in solutions}) != 1:
        raise InvalidInput("Only timetables of the same term can be compared.")
    profile = profile_code or solutions[0].profile_code or "balanced"
    rows = []
    for solution in solutions:
        problem = problem_for(db, solution.snapshot_id)
        values = solution.evaluation.get("objective_values", {})
        rows.append(
            {
                "id": str(solution.id),
                "name": solution.name,
                "profile_code": solution.profile_code,
                "status": solution.status,
                "complete": solution.is_complete,
                "hard_violations": solution.hard_violation_count,
                "unscheduled_periods": int(values.get(UNSCHEDULED, 0)),
                "tiers": tiers_under(problem, solution.evaluation, profile),
                "objective_values": {k: v for k, v in values.items() if k != "stability"},
                "rule_values": solution.evaluation.get("rule_values", {}),
            }
        )
    ranking = sorted(rows, key=lambda r: (r["hard_violations"], r["tiers"]))
    metrics = sorted({k for r in rows for k in r["objective_values"]})

    def vector(row: dict[str, Any]) -> list[int]:
        return [row["hard_violations"]] + [int(row["objective_values"].get(k, 0)) for k in metrics]

    dominance = [
        [a["id"], b["id"]]
        for a in rows
        for b in rows
        if a is not b
        and all(x <= y for x, y in zip(vector(a), vector(b), strict=True))
        and vector(a) != vector(b)
    ]
    baseline, _ = encoded_placements(db, solutions[0].id)
    differences = []
    for solution in solutions[1:]:
        other, _ = encoded_placements(db, solution.id)
        differences.append({"id": str(solution.id), **_difference(baseline, other)})
    return {
        "profile": profile,
        "solutions": rows,
        "ranking": [r["id"] for r in ranking],
        "dominance": dominance,
        "differences": differences,
    }


def _difference(before: EncodedPlacements, after: EncodedPlacements) -> dict[str, int]:
    moved = rooms = 0
    for session_id, placed in before.items():
        now = after.get(session_id)
        if now is None:
            continue
        if now[:2] != placed[:2]:
            moved += 1
        elif now[2] != placed[2]:
            rooms += 1
    return {
        "moved": moved,
        "room_changes": rooms,
        "added": sum(1 for s in after if s not in before),
        "removed": sum(1 for s in before if s not in after),
    }


def explanation(
    db: Session, principal: Principal, solution_id: uuid.UUID, session_id: str
) -> dict[str, Any]:
    require_read(principal)
    solution = get_solution(db, solution_id)
    evaluated = evaluate(db, solution)
    problem, codec = evaluated.problem, evaluated.codec
    s = codec.session_index.get(session_id)
    if s is None:
        raise NotFound("Session")
    result = explain(Evaluator(problem, evaluated.config), evaluated.placements, s, max_free=10)
    return {
        "session_id": session_id,
        "windows": result.windows,
        "rooms": result.rooms,
        "free": [
            {
                "day": problem.day_of(p.slot),
                "period": problem.period_of(p.slot),
                "room_id": problem.rooms[p.room].id if p.room is not None else None,
            }
            for p in result.free
        ],
        "obstacles": [
            dict(
                zip(
                    ("subject_kind", "subject_id"),
                    _subject(problem, o.code, o.subject),
                    strict=True,
                ),
                code=o.code,
                windows=o.windows,
                sessions=[problem.sessions[x].id for x in o.sessions],
                rule_id=o.rule_id,
                message=o.message,
            )
            for o in result.obstacles
        ],
        "room_problems": result.room_problems,
        "summary": result.summary,
    }
