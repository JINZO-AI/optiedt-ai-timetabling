"""The CP-SAT model and the independent evaluator must agree, on random instances.

1. With every placement fixed, each tier of the model has exactly one value (its minimum and
   maximum coincide) and it is the evaluator's value: no auxiliary variable has freedom left,
   so a solution that is not optimal still reports its true objective values.
2. Every timetable the engine returns satisfies every hard requirement, and the values it
   reports are the evaluator's.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from ortools.sat.python import cp_model

from optiedt.evaluation.evaluator import Evaluator
from optiedt.problem.catalog import MAX_TIER, OBJECTIVES
from optiedt.problem.model import Problem
from optiedt.problem.solution import ObjectiveConfig, Placement
from optiedt.solver.domains import build_context
from optiedt.solver.heuristic import construct
from optiedt.solver.model import ScheduleModel
from tests.solver.helpers import evaluate, solve
from tests.solver.instances import instances

pytestmark = pytest.mark.solver

SLOW = settings(
    deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large]
)


def _fix(builder: ScheduleModel, placements: dict[int, Placement]) -> None:
    m = builder.model
    for session in builder.p.sessions:
        s = session.index
        present = builder.present[s]
        if present is None:
            continue
        placement = placements.get(s)
        if placement is None:
            m.add(present == 0)
            continue
        m.add(builder.x[s][placement.slot] == 1)
        if placement.room is not None:
            m.add(builder.y[s][placement.room] == 1)


def _extreme(builder: ScheduleModel, expr: cp_model.LinearExprT, maximize: bool) -> int:
    model = builder.model.clone()
    if maximize:
        model.maximize(expr)
    else:
        model.minimize(expr)
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.max_time_in_seconds = 20
    status = solver.solve(model)
    assert status == cp_model.OPTIMAL, solver.status_name(status)
    return round(solver.objective_value)


@settings(SLOW, max_examples=150)
@given(problem=instances(hard_rules=False), data=st.data())
def test_fixed_timetables_have_exactly_the_evaluators_values(
    problem: Problem, data: st.DataObject
) -> None:
    context = build_context(problem)
    seed = data.draw(st.integers(0, 10_000), label="seed")
    placements = construct(context, seed)
    if placements:
        dropped = data.draw(st.sets(st.sampled_from(sorted(placements)), max_size=3), label="drop")
        placements = {s: p for s, p in placements.items() if s not in dropped}
    reference = construct(context, seed + 1)
    codes = sorted(set(OBJECTIVES) - {"stability"})
    objectives = {
        code: (data.draw(st.integers(1, MAX_TIER)), data.draw(st.integers(1, 3)))
        for code in codes
    }
    objectives["stability"] = (data.draw(st.integers(1, MAX_TIER)), 1)
    config = ObjectiveConfig(objectives, reference)

    builder = ScheduleModel(context, reference=reference)
    placements = builder.canonical(placements)
    _fix(builder, placements)
    expected = Evaluator(problem, config).evaluate(placements).tiers
    for tier in range(MAX_TIER + 1):
        expr = builder.tier_expression(config, tier)
        if expr is None or isinstance(expr, int):
            assert expected[tier] == (expr or 0), tier
            continue
        low = _extreme(builder, expr, maximize=False)
        high = _extreme(builder, expr, maximize=True)
        assert low == high == expected[tier], (tier, low, high, expected[tier])


@settings(SLOW, max_examples=60)
@given(problem=instances())
def test_engine_timetables_are_valid_and_report_true_values(problem: Problem) -> None:
    result = solve(problem, ("balanced", "student_centred"), seconds=1.0)
    base = evaluate(problem, result.base)
    assert base.violations == [], [v.message for v in base.violations][:3]
    assert base.unscheduled_periods == result.tier0.value
    for outcome in result.profiles:
        evaluation = evaluate(problem, outcome.placements, outcome.code)
        assert evaluation.violations == [], [v.message for v in evaluation.violations][:3]
        assert evaluation.tiers[0] <= (result.tier0.value or 0)
        solved = [tier for tier in outcome.tiers if tier.value is not None]
        # A finished tier bounds the later searches, which may still improve it.
        for tier in solved:
            assert evaluation.tiers[tier.tier] <= tier.value, (outcome.code, tier)
        if solved:
            last = solved[-1]
            assert evaluation.tiers[last.tier] == last.value, (outcome.code, last)
