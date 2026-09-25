"""On random instances, the relaxation diagnosis and the independent evaluator agree: every
requirement the relaxed timetable breaks is a reported change, every reported change is a
broken requirement, physics is never broken, and the reported costs add up to the
optimized total."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, event, given, settings

from optiedt.evaluation.evaluator import Evaluator
from optiedt.problem.model import Problem
from optiedt.problem.solution import ObjectiveConfig
from optiedt.solver.domains import SLOT_RULES, build_context
from optiedt.solver.engine import SolveSettings
from optiedt.solver.relaxation import Relaxation
from tests.solver.helpers import solve
from tests.solver.instances import instances

pytestmark = pytest.mark.solver

PHYSICAL = {
    "instructor_conflict",
    "student_conflict",
    "room_conflict",
    "room_unavailable",
    "crosses_break",
    "past_last_period",
    "room_missing",
    "room_for_online",
}
KIND_OF_CODE = {
    "slot_closed": "slot_closed",
    "instructor_unavailable": "instructor_unavailable",
    "students_unavailable": "students_unavailable",
    "activity_unavailable": "activity_unavailable",
    "fixed_moved": "fixed_moved",
    "room_type": "room_type",
    "room_features": "room_features",
    "room_capacity": "room_capacity",
    "campus": "room_location",
    "building": "room_location",
    "room_not_allowed": "room_not_allowed",
    "same_day_occurrences": "different_days",
}


def _kind(code: str) -> str:
    if code.startswith("rule:"):
        return "slot_rule" if code.removeprefix("rule:") in SLOT_RULES else "rule"
    return KIND_OF_CODE[code]


@settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(problem=instances())
def test_relaxation_reports_exactly_what_its_timetable_breaks(problem: Problem) -> None:
    run = SolveSettings(mode="reproducible", time_limit_seconds=1.0, workers=2, seed=5)
    result = Relaxation(build_context(problem), run).run()
    evaluation = Evaluator(problem, ObjectiveConfig({})).evaluate(result.placements)
    event("relaxations needed" if result.changes else "feasible as is")
    for change in result.changes:
        event(f"change: {change.kind}")

    broken: set[tuple[str, int | None]] = set()
    for violation in evaluation.violations:
        assert violation.code not in PHYSICAL, violation.message
        kind = _kind(violation.code)
        if kind == "rule":
            broken.add(
                (kind, next(i for i, r in enumerate(problem.rules) if r.id == violation.rule_id))
            )
        else:
            broken |= {(kind, s) for s in violation.sessions}

    reported: set[tuple[str, int | None]] = set()
    for change in result.changes:
        if change.kind in ("oversized_room", "unscheduled"):
            continue  # not a broken requirement: a search restriction, or nothing placed
        if change.kind == "rule":
            reported.add(("rule", change.subject))
        else:
            reported |= {(change.kind, s) for s in change.sessions}
    assert broken == reported

    assert sorted(result.unscheduled) == sorted(evaluation.unscheduled)
    if result.phases and result.phases[-1].tier == 1 and result.phases[-1].value is not None:
        assert result.total_cost == result.phases[-1].value
    engine = solve(problem, seconds=1.0)
    assert evaluation.unscheduled_periods <= (engine.tier0.value or 0)
