"""FR-9 — configure the calendar: holidays, closed slots, shortened day.

    Acceptance criterion (docs/testing-strategy.md §4, and docs/status.md):
    "Close a half-day in configuration → those slots disappear from every
    timetable, WITH NO CODE CHANGE."

This is invariant 7 and ADR-003, stated as a test. The whole argument is that a
rule the institution decides must be changeable by the institution: closing a
half-day sets `Slot.is_open = 0`, H9 removes those slots from every session's
domain, and **adding a CP-SAT constraint for a closed Saturday is a bug, not a
feature**.

⚠️ **"With no code change" is the half that is easy to fake and easy to lose.**
A test that closed a half-day by calling some `close_half_day()` helper in the
solver would pass while proving the opposite of the criterion. So the closure
here is a change to DATA only - `Slot.is_open` on the instance handed to the
run - and the solver is built by the same `cp_sat_factory` the API uses, with
no argument about calendars. Two assertions below check that nothing was added:
the catalogue still holds exactly twelve hard constraints, and no new code
appears in it.

⚠️ **This instance is tight enough that the closure is a real test of the
mechanism rather than a formality.** Any half-day closure costs each room one
two-period window, and `Lab_Info` has exactly 8 spare in the whole week across
8 rooms - so closing a half-day takes it to **exactly 100.0 % of its two-period
windows**. Measured 2026-08-05: the instance is still solvable, all 218
sessions placed, on three different half-days.
"""

from __future__ import annotations

import dataclasses

import pytest

from optiedt.api import deps
from tests.acceptance.conftest import (
    PRODUCTION_BUDGET,
    PRODUCTION_SEED,
    real_solver_factory,
    wire_application,
)

pytestmark = [pytest.mark.acceptance, pytest.mark.solver]

#: Wednesday afternoon. Any half-day would do - the arithmetic is the same on
#: every 5-period day - and this one is measured at 13.4 s to feasibility.
CLOSED_DAY = 2
AFTERNOON = frozenset({3, 4})


def close_half_day(instance, day: int = CLOSED_DAY, periods: frozenset[int] = AFTERNOON):
    """The whole intervention: `is_open = False` on some slots. Nothing else.

    Not a helper the product exposes - deliberately. The product's own way of
    doing this is editing configuration data, and this is that edit expressed
    against the loaded instance.
    """
    return dataclasses.replace(
        instance,
        slots=tuple(
            dataclasses.replace(slot, is_open=False)
            if (slot.day_index == day and slot.period_index in periods)
            else slot
            for slot in instance.slots
        ),
    )


@pytest.fixture(scope="module")
def closed_slots() -> set[int]:
    deps.get_instance.cache_clear()
    instance = deps.get_instance()
    return {
        slot.index
        for slot in instance.slots
        if slot.day_index == CLOSED_DAY and slot.period_index in AFTERNOON
    }


@pytest.fixture(scope="module")
def run_with_a_closed_half_day() -> dict[str, object]:
    deps.get_instance.cache_clear()
    instance = close_half_day(deps.get_instance())
    with wire_application(real_solver_factory(), instance_provider=lambda: instance) as application:
        run = application.launch(seed=PRODUCTION_SEED, deterministicBudget=PRODUCTION_BUDGET)
    assert run["state"] == "COMPLETED", f"state={run['state']} error={run['error']}"
    return run


def test_the_closed_slots_appear_in_no_timetable(
    run_with_a_closed_half_day: dict[str, object], closed_slots: set[int]
) -> None:
    """ "Every timetable", not "the first one" - the criterion's own word.

    A two-period session starting one period before a closed slot would occupy
    it without ever being placed AT it, so occupancy is checked rather than the
    start index.
    """
    deps.get_instance.cache_clear()
    duration = {s.id: s.duration_periods for s in deps.get_instance().sessions}

    for candidate in run_with_a_closed_half_day["candidates"]:
        for placement in candidate["placements"]:
            occupied = range(placement["slot"], placement["slot"] + duration[placement["session"]])
            assert not closed_slots.intersection(occupied), (
                f"{placement['session']} occupies a closed slot in candidate {candidate['id']}"
            )


def test_every_session_is_still_placed(
    run_with_a_closed_half_day: dict[str, object],
) -> None:
    """Closing a half-day must remove slots, not sessions.

    ⚠️ It is a genuine constraint here, not a formality: the closure takes
    `Lab_Info` to exactly 100.0 % of its two-period windows, so a solution
    exists only if a perfect packing does. Measured: it does.
    """
    for candidate in run_with_a_closed_half_day["candidates"]:
        assert len(candidate["placements"]) == 218


def test_no_new_constraint_was_added_to_the_catalogue(
    run_with_a_closed_half_day: dict[str, object],
) -> None:
    """⚠️ **The "with no code change" half, and ADR-003's actual claim.**

    A CP-SAT constraint for a closed half-day would be a bug: the mechanism is
    `is_open` plus H9, which already exists. If someone ever "fixes" a calendar
    rule by adding H13, this is what fails.
    """
    deps.get_instance.cache_clear()
    catalogue = deps.get_instance().constraints
    hard = [c.code for c in catalogue if c.kind == "HARD"]

    assert len(hard) == 12
    assert set(hard) == {f"H{n}" for n in range(1, 13)}


def test_the_closure_is_expressed_only_as_data(closed_slots: set[int]) -> None:
    """The intervention itself, checked rather than described.

    Everything that differs between the two instances is `Slot.is_open`. If
    closing a half-day ever required touching sessions, rooms or the
    catalogue, this is what would say so.
    """
    deps.get_instance.cache_clear()
    before = deps.get_instance()
    after = close_half_day(before)

    assert before.sessions == after.sessions
    assert before.rooms == after.rooms
    assert before.constraints == after.constraints
    assert before.teachers == after.teachers
    assert before.availability == after.availability

    changed = {
        slot.index for slot, other in zip(before.slots, after.slots, strict=True) if slot != other
    }
    assert changed == closed_slots
    # The slot INDEX is untouched, which is what lets a shortened-day window
    # shift displayed hours without moving a single variable (ADR-003).
    assert [s.index for s in before.slots] == [s.index for s in after.slots]


def test_the_pre_analysis_reports_what_the_closure_cost(
    run_with_a_closed_half_day: dict[str, object],
) -> None:
    """The operator is told the new margin, not just that it still works.

    Closing a half-day takes `Lab_Info` from 90.9 % to 100.0 % of its
    two-period windows. A report that said "passed" and nothing else would hide
    that the next closure has nowhere to come from - which is precisely the
    reading error C-13 punished.
    """
    coverage = next(
        c for c in run_with_a_closed_half_day["preAnalysis"] if c["name"] == "SLOT_COVERAGE"
    )

    assert coverage["passed"] is True
    assert "80/80 2-period windows = 100.0%" in coverage["detail"]
    assert "binding resource" in coverage["detail"]
