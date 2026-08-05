"""FR-12 — verify data before solving; report structural risks.

    Acceptance criterion (docs/testing-strategy.md §4):
    "Verify an instance with insufficient rooms → the resource concerned and
    the quantity missing are named."

The emphasis is the specification's own: a failing check must name the
**resource** and the **quantity**, not return a boolean. A verdict-only report
is what let C-13 through - the check whose whole purpose is to tell "this
instance has no solution" from "the model has a bug" answered with a
comfortable percentage and nobody could act on it.

Fake solver throughout: FR-12's criterion is about the five checks, which run
in stage 1 before any solve and need no engine at all. The two infeasible
shapes are exercised against the real solver in `test_fr08.py`.
"""

from __future__ import annotations

import pytest

from optiedt.api import deps
from tests.acceptance.conftest import (
    FakeSolver,
    keeping_only_computer_laboratories,
    the_original_room_mix,
    wire_application,
)

pytestmark = pytest.mark.acceptance


def _run_against(instance_builder) -> dict[str, object]:
    deps.get_instance.cache_clear()
    instance = instance_builder(deps.get_instance())
    solver = FakeSolver()
    with wire_application(lambda: solver, instance_provider=lambda: instance) as application:
        return application.launch()


def _slot_coverage(run: dict[str, object]) -> dict[str, object]:
    checks = run["preAnalysis"]
    assert checks, "an empty check list means the stage did not run, never 'nothing wrong'"
    found = [c for c in checks if c["name"] == "SLOT_COVERAGE"]
    assert found, f"SLOT_COVERAGE missing from {[c['name'] for c in checks]}"
    return dict(found[0])


def test_an_instance_short_of_rooms_fails_the_coverage_check() -> None:
    check = _slot_coverage(_run_against(lambda i: keeping_only_computer_laboratories(i, 4)))

    assert check["passed"] is False


def test_the_resource_concerned_is_named() -> None:
    """`Lab_Info`, not "a room type" and not a percentage."""
    check = _slot_coverage(_run_against(lambda i: keeping_only_computer_laboratories(i, 4)))

    assert check["resource"] == "Lab_Info"


def test_the_quantity_missing_is_named() -> None:
    """160 periods of demand against 4 rooms x 28 = 112 available: short by 48.

    A figure the reader can act on - four laboratories were withdrawn, and the
    report says how much capacity that cost rather than that something is
    wrong.
    """
    check = _slot_coverage(_run_against(lambda i: keeping_only_computer_laboratories(i, 4)))

    assert check["missingQuantity"] == pytest.approx(48.0)
    assert "short by 48 periods" in check["detail"]


def test_the_contiguity_bound_fires_where_the_period_bound_would_not() -> None:
    """⚠️ **The C-13 case, end to end.** This is the one that matters.

    On the original room mix the PERIOD bound reads 160/168 = 95.2 %, which is
    comfortable, and the instance has no solution: every laboratory session
    spans two periods, a two-period session must fit inside one day, and a
    5-period day gives a room only two such windows. Six computer laboratories
    offer 66 windows against 80 needed.

    The check must therefore name the shortfall in WINDOWS. If this ever
    passes, or fires on the period bound instead, the blind spot that cost
    three sessions is back inside the product.
    """
    check = _slot_coverage(_run_against(the_original_room_mix))

    assert check["passed"] is False
    assert check["resource"] == "Lab_Info"
    assert check["missingQuantity"] == pytest.approx(14.0)
    assert "short by 14 2-period windows" in check["detail"]
    # Science laboratories are short by 2 on the same mix, and the report says
    # so rather than stopping at the first resource it finds.
    assert "Lab_Sciences is short by 2" in check["detail"]
    # And the reassuring period figure is shown BESIDE the failure, not instead
    # of it - a reader who sees only 95.2 % draws exactly the wrong conclusion.
    assert "95.2%" in check["detail"]


def test_the_report_says_this_is_arithmetic_rather_than_a_slow_solver() -> None:
    """The sentence that stops the next reader spending three sessions on it."""
    check = _slot_coverage(_run_against(the_original_room_mix))

    assert "pigeonhole" in check["detail"]
    assert "no timetable exists" in check["detail"].lower()


def test_the_reference_instance_passes_every_check() -> None:
    """The other half of the claim.

    A check that fails on everything names no resource in particular. This is
    what makes the failures above informative.
    """
    run = _run_against(lambda i: i)

    checks = run["preAnalysis"]
    assert len(checks) == 5
    failed = [c["name"] for c in checks if not c["passed"]]
    assert failed == [], f"the reference instance should pass all five, {failed} failed"


def test_the_report_shows_figures_rather_than_five_green_ticks() -> None:
    """SLOT_COVERAGE passes on the reference instance AND says Lab_Info is the
    binding resource at 90.9 % of two-period windows against 71.4 % of periods.

    A verdict-only report would reproduce exactly the reading error C-13 cost
    three sessions - which is why the passing case is asserted too.
    """
    check = _slot_coverage(_run_against(lambda i: i))

    assert check["passed"] is True
    assert "90.9%" in check["detail"]
    assert "71.4%" in check["detail"]


def test_one_half_of_verification_5_says_it_is_not_covered() -> None:
    """`Instance` excludes `Student` (increment 2), so "425 students match the
    declared subgroup sizes" stays with `scripts/verify-instance.ps1`.

    A narrower check must not pass for the documented one, and the report says
    so in its own words rather than leaving the reader to assume.
    """
    run = _run_against(lambda i: i)
    hierarchy = next(c for c in run["preAnalysis"] if c["name"] == "GROUP_HIERARCHY")

    assert "NOT checked here" in hierarchy["detail"]
    assert "verify-instance" in hierarchy["detail"]
