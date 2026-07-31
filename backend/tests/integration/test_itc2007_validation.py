"""Validation on the published instances — `docs/testing-strategy.md` §1.

Two claims, and they are of different kinds.

**The cost function reproduces published results.** Seven solutions the archive
ships, produced by a third-party solver years before this project existed, are
re-evaluated here and must come out at exactly the cost the archive records for
them. This is what makes every number the harness prints checkable rather than
merely self-consistent, and it needs **no solver**, so it runs on every
`scripts/run-checks.ps1`. If ITC-2007's rules were ever misread, this is where it
surfaces.

**The model produces valid timetables on foreign instances.** Solver-marked, on
the two smallest instances, because the point is that the *engine* is validated
and not that a laptop can beat a metaheuristic. The full 21-instance sweep is
`scripts/validate-itc2007.ps1`, and its results are in `docs/status.md`.

⚠️ Every test here is skipped when `data/reference/` is absent. The archives are
gitignored (ADR-008, `data/reference/PROVENANCE.md`), so a fresh clone has none,
and a suite that failed for that reason would train the next reader to ignore it.
"""

from __future__ import annotations

import pytest

from optiedt.validation.itc2007.cost import evaluate
from optiedt.validation.itc2007.model import SolveConfig, solve
from optiedt.validation.itc2007.published import (
    instances_with_published_results,
    published_result,
)
from optiedt.validation.itc2007.reader import (
    archive_root,
    archives_present,
    competition_instance_names,
    instance_path,
    read_instance,
    read_solution,
)

pytestmark = pytest.mark.skipif(
    not archives_present(),
    reason="data/reference/ is gitignored; run scripts/check-reference-data.ps1",
)

SEED = 42
BUDGET = 4.0
"""Deterministic, never wall clock (ADR-011). Small: these tests establish that
a valid timetable comes out, not how good it is."""


@pytest.mark.parametrize("name", instances_with_published_results())
def test_the_cost_function_reproduces_the_published_cost(name):
    """The archive's own solution, re-costed here, must match what it publishes.

    The reference is the bundled report's own "best" column
    (`docs/latex/itc2007.tex`, Confronto II), which `published.py` transcribes as
    ``bundled_solver_unbounded`` - the cost of exactly the `.sol` files read
    here. Agreement on all seven, across four independent cost components, is
    what licenses quoting any other number this package produces.
    """
    instance = read_instance(instance_path(name))
    solution = read_solution(archive_root() / "results" / "races" / f"{name}.ctt.sol", instance)
    reference = published_result(name)
    assert reference is not None

    evaluation = evaluate(instance, solution)

    assert evaluation.hard.total == 0, f"{name}: the archive's own solution is not feasible"
    assert evaluation.soft.total == reference.bundled_solver_unbounded, (
        f"{name}: recomputed {evaluation.soft.total}, archive publishes "
        f"{reference.bundled_solver_unbounded} - ITC-2007's rules are being read wrongly"
    )


def test_every_competition_instance_parses():
    """21 instances, matching PROVENANCE.md, and every one structurally sane."""
    names = competition_instance_names()
    assert len(names) == 21

    for name in names:
        instance = read_instance(instance_path(name))
        assert instance.courses, name
        assert instance.rooms, name
        assert instance.periods > 0, name
        assert all(course.lectures > 0 for course in instance.courses), name
        # Every curriculum member and every unavailability must name a real
        # course; a typo here would silently drop a hard constraint.
        known = {course.id for course in instance.courses}
        for curriculum in instance.curricula:
            assert set(curriculum.members) <= known, f"{name}/{curriculum.id}"
        assert {course for course, _ in instance.unavailable} <= known, name
        assert all(0 <= period < instance.periods for _, period in instance.unavailable), name


def test_the_reader_matches_the_published_header_counts():
    """comp01's header states its own sizes; the reader must agree with them
    rather than with however many records it happened to consume."""
    instance = read_instance(instance_path("comp01"))
    assert instance.name == "Fis0506-1"
    assert len(instance.courses) == 30
    assert len(instance.rooms) == 6
    assert instance.days == 5
    assert instance.periods_per_day == 6
    assert len(instance.curricula) == 14
    assert len(instance.unavailable) == 53


@pytest.mark.solver
@pytest.mark.parametrize("name", ["toy", "comp01"])
def test_the_model_produces_a_valid_timetable_on_a_foreign_instance(name):
    """The claim `docs/testing-strategy.md` §1 makes first: no hard constraint
    violated, on an instance the engine was not built around.

    Judged by re-deriving the four constraints from the instance, never from
    CP-SAT's status - the same discipline as `test_h1_h12.py`.
    """
    instance = read_instance(instance_path(name))
    report = solve(instance, SolveConfig(seed=SEED, deterministic_budget=BUDGET))

    assert not report.infeasible, f"{name} is a feasible competition instance"
    assert report.solution, f"{name}: no timetable produced within the budget"

    evaluation = evaluate(instance, report.solution)
    assert evaluation.hard.lectures == 0
    assert evaluation.hard.repeated_period == 0
    assert evaluation.hard.conflicts == 0
    assert evaluation.hard.availability == 0
    assert evaluation.hard.room_occupancy == 0


@pytest.mark.solver
@pytest.mark.parametrize("name", ["toy", "comp01"])
def test_the_encoding_equals_the_independently_recomputed_cost(name):
    """The cross-layer guard, transplanted.

    `model.py` encodes each soft cost exactly, so the value CP-SAT gives each
    auxiliary must equal what `cost.py` derives from the placements — component
    by component, because a total can agree while two components cancel. Two
    independent derivations of one number; a divergence means the encoding
    drifted from ITC-2007's rules. Same guard, same reason, as
    `tests/integration/test_objective_matches_analysis.py`.

    ⚠️ This deliberately compares the **encoding**, not
    ``CpSolver.objective_value``. Measured 2026-07-31: under `interleave_search`
    the reported objective can sit a few units above the value of the objective
    expression at the solution actually returned, on solves that stop before
    proving optimality. Asserting on that number would make this test flaky for
    a reason that has nothing to do with what it is guarding.
    """
    instance = read_instance(instance_path(name))
    report = solve(instance, SolveConfig(seed=SEED, deterministic_budget=BUDGET))

    assert report.solution
    assert report.objective_breakdown == evaluate(instance, report.solution).soft


@pytest.mark.solver
def test_the_same_seed_and_budget_reproduce_the_same_timetable():
    """ADR-011 on a foreign instance: identical inputs, identical output.

    The configuration is the production one - all workers, deterministic budget,
    `interleave_search`. Reproducibility that only held on the instance the
    project generated for itself would be a property of that instance.
    """
    instance = read_instance(instance_path("toy"))
    config = SolveConfig(seed=SEED, deterministic_budget=BUDGET)

    first = solve(instance, config)
    second = solve(instance, config)

    def signature(solution):
        # Assignment is frozen but not ordered, so sort on an explicit key
        # rather than on the dataclass. Comparing the tuples directly would
        # also work today - model.py emits them in a fixed order - but that
        # would make this test depend on an ordering it is not testing.
        return sorted((a.course, a.period, a.room) for a in solution)

    assert signature(first.solution) == signature(second.solution)
    assert first.objective_breakdown == second.objective_breakdown
