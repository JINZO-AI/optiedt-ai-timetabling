"""FR-19 / ADR-011: the same inputs must produce the same candidates.

"Two runs with the same data, weights and seed produce identical candidates in
the same order" is both a Phase 3 completion criterion (docs/dashboard.md) and
an increment-1 acceptance criterion (docs/status.md). ADR-011 is the mechanism
that is supposed to deliver it: bound the solve by max_deterministic_time
rather than wall clock, because parallel workers race under a wall clock and a
fixed seed does not fix that.

⚠️ **Read this before changing a solver parameter.** ``max_deterministic_time``
binds PER WORKER, while ``CpSolver.deterministic_time`` reports the SUM across
workers. So a run configured for 5 units on a 16-core machine legitimately
reports ~54 - that is the workers each honouring their 5, not one run
overshooting by 11x. An earlier reading of that aggregate as an overshoot is
recorded and corrected in docs/status.md; the ratio test below exists so the
distinction cannot be lost again.

⚠️⚠️ **These tests deliberately do NOT run at the production worker count.**
Measured 2026-07-30, and the two instances disagree in a way worth stating:
on the TINY instance 1, 2 and 4 workers all reproduced and 8 and 0 did not;
on the REFERENCE instance only **1** reproduced - 4 workers produced two
candidates on one run and one on the next. So a worker count that looks
deterministic on a small instance is not evidence it is deterministic on a
real one, and the safe count is the one where there is no parallelism to
race at all.

On the tiny instance every run proved optimality, so the solves are not
being cut short - they find *different optimal solutions* and return
whichever worker reported first. Bounding the deterministic time does not
remove that race; it only makes the amount of work deterministic.

So ADR-011's mechanism is sound and its conclusion - "Reproducibility holds
... and the search keeps its parallelism" - is not. Pinning reproducibility
here at ``workers=1`` verifies that the ENGINE and the portfolio add no
nondeterminism of their own, which is the part this codebase controls. The
production path is knowingly not covered, and the acceptance criterion it
serves stays unticked in docs/status.md rather than being quietly
reinterpreted. Proposed revision is recorded there; it is not applied here.

These run on the tiny instance, not the reference one: six full reference
solves at the production setting take ~18 minutes, too slow to guard a
regression. The reference-instance measurement is in docs/status.md.
"""

from __future__ import annotations

import pytest

from optiedt.services.portfolio import (
    PortfolioRequest,
    generate_portfolio,
    placement_signature,
)
from optiedt.solver.engine import CpSatSolver
from optiedt.solver.interfaces import SolverInput

SEED = 42
BUDGET = 2.0
WALL_CLOCK_CEILING = 120.0

REPRODUCIBLE_WORKERS = 1
"""Worker count at which CP-SAT is measurably reproducible on this project.

NOT the production default (``CpSatSolver.workers = 0``, meaning all cores).
Pinned at 1 rather than at the highest count that happened to reproduce,
because 1 is the only setting whose determinism follows from there being no
parallelism to race - every other count reproduced on the tiny instance and
then failed on the reference one (see the module docstring). A number that
holds by measurement can stop holding when the machine or the instance
changes; a number that holds by construction cannot.
"""


def _solver(workers: int = REPRODUCIBLE_WORKERS) -> CpSatSolver:
    return CpSatSolver(workers=workers, wall_clock_ceiling_seconds=WALL_CLOCK_CEILING)


def _request(instance, **overrides):
    base = {
        "instance": instance,
        "run": "run-1",
        "seed": SEED,
        "deterministic_budget": BUDGET * 3,  # divided across three profiles
    }
    return PortfolioRequest(**{**base, **overrides})


@pytest.mark.solver
def test_a_single_solve_repeats_exactly(tiny_instance):
    """The narrowest statement: one solve, twice, same everything."""
    from optiedt.services.portfolio import default_profiles

    balanced = default_profiles(tiny_instance)[0]
    request = SolverInput(
        instance=tiny_instance,
        profile=balanced,
        seed=SEED,
        deterministic_budget=BUDGET,
    )

    first = _solver().solve(request)
    second = _solver().solve(request)

    assert placement_signature(first.placements) == placement_signature(second.placements)
    assert first.cost == second.cost


@pytest.mark.solver
def test_the_whole_portfolio_repeats_exactly(tiny_instance):
    """The criterion as the specification states it: identical candidates in
    identical order, across all three profiles."""
    request = _request(tiny_instance)

    first = generate_portfolio(request, _solver())
    second = generate_portfolio(request, _solver())

    assert [c.id for c in first.result.candidates] == [c.id for c in second.result.candidates]
    assert [c.profile_name for c in first.result.candidates] == [
        c.profile_name for c in second.result.candidates
    ]
    assert first.duplicates_removed == second.duplicates_removed

    for a, b in zip(first.result.candidates, second.result.candidates, strict=True):
        assert placement_signature(a.placements) == placement_signature(b.placements), a.id
        assert a.score == pytest.approx(b.score), a.id
        assert [(s.criterion, s.raw_value) for s in a.sub_scores] == [
            (s.criterion, s.raw_value) for s in b.sub_scores
        ], a.id


@pytest.mark.solver
def test_the_deterministic_budget_binds_per_worker(tiny_instance):
    """ADR-011's mechanism, pinned against the misreading that cost this
    project a documented "11x overshoot" that never existed.

    With a single worker the budget binds exactly: consumed deterministic time
    must not exceed what was asked for. Any future change that breaks this
    breaks reproducibility, and would otherwise only show up as candidates
    that quietly stop matching.
    """
    from optiedt.services.portfolio import default_profiles

    balanced = default_profiles(tiny_instance)[0]
    result = _solver(workers=1).solve(
        SolverInput(
            instance=tiny_instance,
            profile=balanced,
            seed=SEED,
            deterministic_budget=BUDGET,
        )
    )

    assert result.deterministic_time_used <= BUDGET + 1e-6, (
        "max_deterministic_time no longer bounds a single worker - ADR-011's "
        "reproducibility argument rests on this"
    )


@pytest.mark.solver
def test_the_engine_adds_no_nondeterminism_of_its_own(tiny_instance):
    """Separates "CP-SAT races at high worker counts" from "our code is
    sloppy". Five repeats at the reproducible worker count must agree
    exactly; if this ever fails, the cause is in this repository - a set
    iterated somewhere, a dict ordering leaking into a placement, an
    unsorted room labeller - and not in the solver."""
    from optiedt.services.portfolio import default_profiles

    balanced = default_profiles(tiny_instance)[0]
    request = SolverInput(
        instance=tiny_instance,
        profile=balanced,
        seed=SEED,
        deterministic_budget=BUDGET,
    )

    signatures = {placement_signature(_solver().solve(request).placements) for _ in range(5)}

    assert len(signatures) == 1, (
        "five identical requests produced more than one timetable at a worker "
        "count that is measurably deterministic - the nondeterminism is ours"
    )


@pytest.mark.solver
def test_the_wall_clock_ceiling_is_not_what_ends_a_solve(tiny_instance):
    """ADR-011: the ceiling is "a hang backstop only... Reaching it is an
    anomaly to log, not a normal exit path." If a solve routinely ends on the
    wall clock, the run is no longer reproducible whatever the seed says."""
    from optiedt.services.portfolio import default_profiles

    balanced = default_profiles(tiny_instance)[0]
    result = _solver().solve(
        SolverInput(
            instance=tiny_instance,
            profile=balanced,
            seed=SEED,
            deterministic_budget=BUDGET,
        )
    )

    assert result.wall_clock_seconds < WALL_CLOCK_CEILING * 0.9, (
        "the solve ended on the wall-clock ceiling rather than its deterministic "
        "budget - reproducibility is not guaranteed on that path"
    )
