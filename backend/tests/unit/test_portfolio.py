"""Portfolio orchestration rules, verified against a recording fake solver.

The four rules in services/portfolio.py's docstring are all invisible in a
normal run - a portfolio that hands each profile the full budget, or varies
the seed, or solves concurrently, still returns three candidates and looks
correct. What it stops being is *reproducible* and *within budget*, neither of
which shows up until much later. So each rule is pinned here against a fake
Solver that records exactly what it was asked, rather than inferred from a
real solve's output.

No CP-SAT: substituting the Solver protocol is the whole point, and it keeps
these in the fast suite where a regression surfaces immediately.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from optiedt.domain.entities import DiagnosisResult, Placement
from optiedt.domain.instance import Instance
from optiedt.services.portfolio import (
    EMPHASIS,
    PortfolioRequest,
    catalogue_weights,
    default_profiles,
    generate_portfolio,
    placement_signature,
)
from optiedt.solver.interfaces import SolverInput, SolverOutput


@dataclass
class RecordingSolver:
    """A Solver that returns scripted placements and records every request."""

    scripted: list[tuple[Placement, ...]]
    requests: list[SolverInput] = field(default_factory=list)
    infeasible_at: int | None = None

    def solve(self, request: SolverInput) -> SolverOutput:
        index = len(self.requests)
        self.requests.append(request)
        if self.infeasible_at is not None and index >= self.infeasible_at:
            return SolverOutput(
                placements=(),
                cost=0,
                infeasible=True,
                proven_optimal=False,
                deterministic_time_used=1.0,
                wall_clock_seconds=2.0,
            )
        return SolverOutput(
            placements=self.scripted[index % len(self.scripted)],
            cost=0,
            infeasible=False,
            proven_optimal=True,
            deterministic_time_used=1.0,
            wall_clock_seconds=2.0,
        )

    def diagnose(self, request: SolverInput) -> DiagnosisResult:
        raise AssertionError("the portfolio must not run the diagnosis itself - Phase 5")


def _placements(*slots: int) -> tuple[Placement, ...]:
    return tuple(
        Placement(session=sid, slot=slot, room="R1")
        for sid, slot in zip(("s_leaf", "s_mid", "s_top"), slots, strict=True)
    )


def _request(instance: Instance, **overrides: object) -> PortfolioRequest:
    base = {
        "instance": instance,
        "run": "run-1",
        "seed": 42,
        "deterministic_budget": 30.0,
    }
    return PortfolioRequest(**{**base, **overrides})  # type: ignore[arg-type]


def test_default_profiles_are_the_three_the_specification_names(tiny_instance):
    """balanced / student-favouring / teacher-favouring, in a fixed order."""
    profiles = default_profiles(tiny_instance)
    assert [p.name for p in profiles] == ["balanced", "student-favouring", "teacher-favouring"]


def test_balanced_profile_is_exactly_the_catalogue(tiny_instance):
    balanced, _, _ = default_profiles(tiny_instance)
    assert balanced.weights == catalogue_weights(tiny_instance)


def test_favouring_profiles_raise_only_their_own_criteria(tiny_instance):
    """student-favouring raises S2; teacher-favouring raises S3 and S5. Every
    other weight must be untouched, or the profiles stop differing for the
    reason the comparison screen claims they differ."""
    catalogue = catalogue_weights(tiny_instance)
    _, student, teacher = default_profiles(tiny_instance)

    for code, weight in catalogue.items():
        expected_student = weight * EMPHASIS if code == "S2" else weight
        expected_teacher = weight * EMPHASIS if code in {"S3", "S5"} else weight
        assert student.weights[code] == pytest.approx(expected_student), code
        assert teacher.weights[code] == pytest.approx(expected_teacher), code


def test_the_total_budget_is_divided_between_the_profiles(tiny_instance):
    """docs/constraint-model.md: "The total budget is divided between them."
    Handing each profile the full budget would triple a run's real cost while
    every test still passed."""
    solver = RecordingSolver(
        scripted=[_placements(0, 1, 2), _placements(0, 1, 3), _placements(0, 1, 4)]
    )
    generate_portfolio(_request(tiny_instance, deterministic_budget=30.0), solver)

    assert len(solver.requests) == 3
    assert [r.deterministic_budget for r in solver.requests] == [10.0, 10.0, 10.0]


def test_every_profile_is_solved_under_the_same_seed(tiny_instance):
    """Diversity must come from the objective, never the seed - otherwise two
    candidates differ for a reason nobody can state."""
    solver = RecordingSolver(
        scripted=[_placements(0, 1, 2), _placements(0, 1, 3), _placements(0, 1, 4)]
    )
    generate_portfolio(_request(tiny_instance, seed=7), solver)

    assert {r.seed for r in solver.requests} == {7}


def test_each_profile_reaches_the_solver_in_order(tiny_instance):
    solver = RecordingSolver(
        scripted=[_placements(0, 1, 2), _placements(0, 1, 3), _placements(0, 1, 4)]
    )
    generate_portfolio(_request(tiny_instance), solver)

    assert [r.profile.name for r in solver.requests] == [
        "balanced",
        "student-favouring",
        "teacher-favouring",
    ]


def test_identical_timetables_are_not_retained_twice(tiny_instance):
    """SRS Table 29: "at most 3, duplicates removed". All three profiles
    converge here, so exactly one candidate survives."""
    same = _placements(0, 1, 2)
    solver = RecordingSolver(scripted=[same, same, same])
    report = generate_portfolio(_request(tiny_instance), solver)

    assert len(report.result.candidates) == 1
    assert report.duplicates_removed == ("student-favouring", "teacher-favouring")


def test_a_duplicate_is_reported_rather_than_silently_dropped(tiny_instance):
    """C-5 turns on how often duplicates actually happen. A mechanism that
    removed them without saying so would destroy the evidence needed to settle
    it."""
    same = _placements(0, 1, 2)
    solver = RecordingSolver(scripted=[same, _placements(0, 1, 3), same])
    report = generate_portfolio(_request(tiny_instance), solver)

    assert len(report.result.candidates) == 2
    assert report.duplicates_removed == ("teacher-favouring",)


def test_duplicate_detection_ignores_the_order_placements_come_back_in(tiny_instance):
    """Two solves may return the same assignment in a different order; they
    are the same timetable and must not both be retained."""
    forward = _placements(0, 1, 2)
    shuffled = tuple(reversed(forward))
    assert placement_signature(forward) == placement_signature(shuffled)

    solver = RecordingSolver(scripted=[forward, shuffled, _placements(0, 1, 3)])
    report = generate_portfolio(_request(tiny_instance), solver)

    assert len(report.result.candidates) == 2
    assert report.duplicates_removed == ("student-favouring",)


def test_an_infeasible_instance_stops_the_portfolio_at_the_first_solve(tiny_instance):
    """H1-H12 are declared identically whatever the weights, so an instance
    with no timetable under one profile has none under any. Continuing would
    spend the rest of the budget to learn nothing."""
    solver = RecordingSolver(scripted=[_placements(0, 1, 2)], infeasible_at=0)
    report = generate_portfolio(_request(tiny_instance), solver)

    assert report.infeasible
    assert report.result.candidates == ()
    assert len(solver.requests) == 1, "the portfolio kept solving after an infeasible result"


def test_the_portfolio_never_runs_the_diagnosis_itself(tiny_instance):
    """Stage 3 is entered by the caller on report.infeasible, and is Phase 5.
    RecordingSolver.diagnose raises if this is violated."""
    solver = RecordingSolver(scripted=[_placements(0, 1, 2)], infeasible_at=0)
    report = generate_portfolio(_request(tiny_instance), solver)

    assert report.result.diagnosis is None


def test_every_candidate_is_scored_under_one_weight_vector(tiny_instance):
    """Not under its own producing profile: the exact-decomposition identity
    only holds when the same w_i prices both candidates being compared."""
    solver = RecordingSolver(
        scripted=[_placements(0, 1, 2), _placements(0, 1, 3), _placements(0, 2, 4)]
    )
    weights = {**catalogue_weights(tiny_instance), "S2": 1.0}
    report = generate_portfolio(_request(tiny_instance, scoring_weights=weights), solver)

    # Recomputing each candidate's score under the same vector must reproduce
    # the stored score exactly - which it cannot if profiles were used.
    from optiedt.analysis.scoring import DefaultScorer

    scorer = DefaultScorer()
    for candidate in report.result.candidates:
        assert candidate.score == pytest.approx(scorer.score(candidate, weights))


def test_candidates_come_back_ranked_by_decreasing_score(tiny_instance):
    solver = RecordingSolver(
        scripted=[_placements(0, 1, 2), _placements(0, 1, 3), _placements(0, 2, 4)]
    )
    report = generate_portfolio(_request(tiny_instance), solver)

    scores = [c.score for c in report.result.candidates]
    assert scores == sorted(scores, reverse=True)


def test_each_candidate_records_the_profile_that_produced_it(tiny_instance):
    """Provenance, not a scoring input - but it must survive, or the
    comparison screen cannot say why two candidates differ."""
    solver = RecordingSolver(
        scripted=[_placements(0, 1, 2), _placements(0, 1, 3), _placements(0, 2, 4)]
    )
    report = generate_portfolio(_request(tiny_instance), solver)

    assert {c.profile_name for c in report.result.candidates} == {
        "balanced",
        "student-favouring",
        "teacher-favouring",
    }


def test_recommendation_inputs_are_carried_through_to_every_solve(tiny_instance):
    """A regenerated run is this same call with one of the three ADR-007
    inputs changed, so they must reach the solver unaltered."""
    solver = RecordingSolver(
        scripted=[_placements(0, 1, 2), _placements(0, 1, 3), _placements(0, 2, 4)]
    )
    excluded = frozenset({("s_leaf", 4)})
    generate_portfolio(_request(tiny_instance, excluded_slots=excluded), solver)

    assert all(r.excluded_slots == excluded for r in solver.requests)


def test_an_empty_profile_tuple_falls_back_to_the_defaults(tiny_instance):
    """Documented behaviour of PortfolioRequest.profiles - a caller that does
    not care gets the three profiles the specification names."""
    solver = RecordingSolver(
        scripted=[_placements(0, 1, 2), _placements(0, 1, 3), _placements(0, 2, 4)]
    )
    generate_portfolio(_request(tiny_instance, profiles=()), solver)

    assert [r.profile.name for r in solver.requests] == [
        "balanced",
        "student-favouring",
        "teacher-favouring",
    ]
