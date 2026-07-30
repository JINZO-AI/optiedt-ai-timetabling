"""The CP-SAT objective and the analysis criteria must measure the same thing.

This is the test that guards the one deliberate duplication in the codebase.
analysis/criteria.py and solver/objective.py implement the SAME seven formulas
(docs/open-questions.md, C-4) against different substrates - realized
placements versus decision variables - and they may not share code, because
docs/architecture.md forbids the solver from importing the analysis layer.
Nothing but a test can keep them in step, and the failure mode if they drift is
quiet: the solver optimises for one quantity while the interface displays
another, and the ranking stops being explainable by the numbers shown.

Method: solve the tiny instance with exactly ONE criterion at weight 1.0, so
the objective value is that criterion's violation count times _WEIGHT_SCALE,
then recompute the same criterion from the returned placements with the
analysis layer and compare. Solving to OPTIMAL also confirms the idle-time
encoding is tight - first/last are free variables pinned only by the
minimisation direction (see solver/objective.py), so a slack assignment would
show up here as an objective above the recomputed value.

S6 is not covered: on this instance every Salle is interchangeable for every
session, so the type is cumulative-encoded and the objective posts no S6 term
at all (rooms are labelled after solving). That gap is documented in
solver/objective.py and in docs/dashboard.md.
"""

from __future__ import annotations

import pytest

from optiedt.analysis.criteria import build_criteria
from optiedt.domain.entities import Candidate, WeightProfile
from optiedt.domain.instance import Instance
from optiedt.solver.engine import CpSatSolver
from optiedt.solver.interfaces import SolverInput
from optiedt.solver.objective import _WEIGHT_SCALE

SEED = 42
DETERMINISTIC_BUDGET = 10.0
WALL_CLOCK_CEILING = 60.0

# S6 excluded - see module docstring. S10 carries default weight 0 but is
# exercised here at weight 1.0 precisely because nothing else would ever
# optimise for it.
CROSS_CHECKED = ["S2", "S3", "S4", "S5", "S7", "S10"]


def _solve(instance: Instance, weights: dict[str, float]):
    request = SolverInput(
        instance=instance,
        profile=WeightProfile(name="single-criterion", weights=weights),
        seed=SEED,
        deterministic_budget=DETERMINISTIC_BUDGET,
    )
    return CpSatSolver(wall_clock_ceiling_seconds=WALL_CLOCK_CEILING).solve(request)


@pytest.mark.solver
@pytest.mark.parametrize("code", CROSS_CHECKED)
def test_objective_value_equals_the_analysis_measurement(tiny_instance, code):
    weights = {c: (1.0 if c == code else 0.0) for c in [*CROSS_CHECKED, "S6"]}
    result = _solve(tiny_instance, weights)

    assert not result.infeasible
    assert result.proven_optimal, (
        f"{code}: the tiny instance did not solve to optimality, so the objective "
        "value cannot be compared against a recomputation - raise the budget"
    )

    criterion = next(c for c in build_criteria(tiny_instance) if c.code == code)
    scored = Candidate(
        id="x",
        run="r",
        profile_name="single-criterion",
        cost=result.cost,
        score=0.0,
        placements=result.placements,
        sub_scores=(),
    )
    recomputed = criterion.raw_value(scored)

    assert result.cost == round(recomputed * _WEIGHT_SCALE), (
        f"{code}: CP-SAT minimised to {result.cost / _WEIGHT_SCALE} but "
        f"analysis/criteria.py measures {recomputed} on the same placements - "
        "the two implementations of this formula have drifted apart"
    )


@pytest.mark.solver
def test_a_profile_with_no_weight_posts_no_objective(tiny_instance):
    """An all-zero profile must be equivalent to the Phase 2 feasibility solve,
    not merely objective-free: engine.py gates build_occupancy on
    has_active_criteria for exactly this reason."""
    result = _solve(tiny_instance, {c: 0.0 for c in [*CROSS_CHECKED, "S6"]})
    assert not result.infeasible
    assert result.cost == 0


@pytest.mark.solver
def test_optimising_one_criterion_does_not_break_placement_validity(tiny_instance):
    """Whatever the objective does, every session is still placed exactly once."""
    for code in CROSS_CHECKED:
        weights = {c: (1.0 if c == code else 0.0) for c in [*CROSS_CHECKED, "S6"]}
        result = _solve(tiny_instance, weights)
        assert len(result.placements) == len(tiny_instance.sessions), code
        assert len({p.session for p in result.placements}) == len(tiny_instance.sessions), code
