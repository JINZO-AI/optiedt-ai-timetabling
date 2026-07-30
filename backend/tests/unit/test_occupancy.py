"""y[s][t] channelling against the real reference instance (C-7).

The property that matters is stated once and checked two ways: structurally
here, without solving, and against actual solved placements in
tests/integration/test_h1_h12.py. y[s,t] must mean "s OCCUPIES t" - so a
2-period session sets it for both of its periods, not just the one it starts
in. Getting that wrong would not fail any hard constraint; it would quietly
halve every idle-time and spread measurement the objective is built on, which
is exactly the kind of error that surfaces as "the ranking looks odd" three
weeks later.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ortools.sat.python import cp_model

from optiedt.instance.loader import load_instance
from optiedt.solver.interfaces import SolverInput
from optiedt.solver.occupancy import build_occupancy
from optiedt.solver.variables import build_variables

INSTANCE_PATH = Path(__file__).resolve().parents[3] / "data" / "instance"


@pytest.fixture(scope="module")
def instance():
    return load_instance(INSTANCE_PATH)


@pytest.fixture(scope="module")
def built(instance):
    model = cp_model.CpModel()
    request = SolverInput(instance=instance, profile=None, seed=42, deterministic_budget=5.0)  # type: ignore[arg-type]
    variables = build_variables(model, request)
    return model, variables, build_occupancy(model, variables, instance)


def _domain(var: cp_model.IntVar) -> set[int]:
    flat = list(var.proto.domain)
    return {v for lo, hi in zip(flat[::2], flat[1::2], strict=True) for v in range(lo, hi + 1)}


def test_start_indicators_cover_exactly_the_pruned_domain(instance, built):
    """One x[s,t0] per start H6/H8/H9 actually left legal - no more, no less.

    An extra indicator would offer the objective a start the hard constraints
    forbid; a missing one would hide a legal placement from it."""
    _, variables, occ = built
    for session in instance.sessions:
        legal = _domain(variables.start[session.id])
        indicators = {t for (s, t) in occ.starts_at if s == session.id}
        assert indicators == legal, f"{session.id}: indicators do not match the pruned domain"


def test_occupies_spans_the_full_duration_of_every_reachable_start(instance, built):
    """The C-7 question itself: y is defined for every slot a valid start
    would cover, which for a 2-period session includes start + 1."""
    _, variables, occ = built
    for session in instance.sessions:
        legal = _domain(variables.start[session.id])
        expected = {t0 + offset for t0 in legal for offset in range(session.duration_periods)}
        assert set(occ.occupied_slots(session.id)) == expected, (
            f"{session.id} (duration {session.duration_periods}): "
            "y is not defined over exactly the reachable slots"
        )


def test_two_period_sessions_reach_strictly_more_slots_than_they_can_start_at(instance, built):
    """Guards the specific mistake C-7 warns about - y built as "starts at"
    rather than "occupies" would make these two sets identical."""
    _, _, occ = built
    two_period = [s for s in instance.sessions if s.duration_periods == 2]
    assert two_period, "the reference instance is documented to contain 2-period sessions"
    for session in two_period:
        starts = {t for (s, t) in occ.starts_at if s == session.id}
        assert set(occ.occupied_slots(session.id)) > starts, (
            f"{session.id}: occupies the same slots it can start at, so y means "
            "'starts at' rather than 'occupies' - see C-7"
        )


def test_occupancy_never_reaches_a_closed_slot(instance, built):
    """H9 holds through the accounting layer too. y is channelled from a
    pruned start[s], so this cannot fail without the pruning having failed -
    which is the point: it pins that dependency rather than assuming it."""
    _, _, occ = built
    closed = {s.index for s in instance.slots if not s.is_open}
    assert closed, "the reference instance is documented to have closed slots"
    reached = {t for (_, t) in occ.occupies}
    assert reached.isdisjoint(closed)


def test_effective_variable_count_is_well_below_the_documented_upper_bound(instance, built):
    """docs/constraint-model.md records 6,104 as an upper bound and never as
    an estimate. This pins the measured figure so a change in the pruning
    shows up as a number rather than as a slower solve."""
    _, _, occ = built
    upper_bound = len(instance.sessions) * sum(1 for s in instance.slots if s.is_open)
    assert upper_bound == 6104
    assert len(occ.occupies) == 5328, "effective y[s][t] count changed - see docs/status.md"
    assert len(occ.starts_at) == 4720, "effective x[s][t0] count changed - see docs/status.md"
