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

⚠️⚠️ **These tests run at the PRODUCTION settings, and that is the point.**
Reproducibility here rests on one solver parameter - ``interleave_search``,
set in engine.py - and without it the production path is NOT reproducible:
measured 2026-07-30, three identical requests produced three different
timetables, every one of them proving optimality. The workers were not being
cut short; they found *different optimal solutions* and returned whichever
reported first. Bounding deterministic time makes the amount of work
deterministic, nothing more.

The parameter is documented as "deterministic (independently of
num_workers!)" but marked **Experimental** upstream, so this file exists to
verify the behaviour rather than trust the documentation - an OR-Tools
upgrade that regressed it would otherwise be invisible until a published
timetable failed to reproduce. See ADR-011 and C-16.

Disabling worker information sharing was also tried and does not help. The
race is in the scheduling, not the sharing.

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

PRODUCTION_WORKERS = 0
"""The production default - all cores. Deterministic because engine.py sets
``interleave_search``; see the module docstring."""


def _solver(workers: int = PRODUCTION_WORKERS) -> CpSatSolver:
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
    """Five repeats at production settings must agree exactly.

    A failure here has two possible causes and both matter: either
    ``interleave_search`` has regressed upstream (it is marked Experimental),
    or this repository introduced nondeterminism of its own - a set iterated
    somewhere, dict ordering leaking into a placement, an unsorted room
    labeller."""
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
        "five identical requests produced more than one timetable at production "
        "settings - either interleave_search regressed upstream, or this "
        "repository introduced nondeterminism of its own"
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
