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

⚠️ **Since Phase 11 the criterion is met through the ADMINISTRATION SCREEN, and
that is what the second half of this file verifies.** Until then "in
configuration" meant editing `slots.csv` by hand: the mechanism was real and
acceptance-tested, and no user could reach it, which is why FR-9 was `WIP` over
working software. The tests below therefore close the half-day by `PUT
/api/calendar` as an administrator and then launch a run, so the path under
test is the one a person takes.

⚠️ **Two engines here, and the split is the one `conftest` describes.** Whether
H9 removes a closed slot from every session's domain is a question about the
ENGINE and takes real CP-SAT at production settings. Whether an administrator's
save reaches the instance a run is assembled from is a question about the
APPLICATION, and takes the fake solver - which places only on slots the
instance says are open, so a closure that failed to reach the run assembly
would put placements on the closed slots and fail the assertion.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from optiedt.api import deps
from optiedt.api.main import app
from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole
from tests.acceptance.conftest import (
    PRODUCTION_BUDGET,
    PRODUCTION_SEED,
    Application,
    FakeSolver,
    real_solver_factory,
    wire_application,
)

pytestmark = pytest.mark.acceptance

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


@pytest.mark.solver
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


@pytest.mark.solver
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


@pytest.mark.solver
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


@pytest.mark.solver
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


# ── The criterion through the administration screen (Phase 11) ─────────


@contextmanager
def as_role(role: UserRole, username: str = "administrateur") -> Iterator[None]:
    """Make the next requests come from another role, then put it back.

    ⚠️ Needed because the criterion spans TWO actors: SRS Table 2 gives the
    calendar to the administrator and the run to the person in charge, so a
    test that stayed one role could not perform the sentence it verifies.
    """
    previous = app.dependency_overrides.get(deps.current_user)
    app.dependency_overrides[deps.current_user] = lambda: User(
        id=username, username=username, role=role
    )
    try:
        yield
    finally:
        if previous is None:
            app.dependency_overrides.pop(deps.current_user, None)
        else:
            app.dependency_overrides[deps.current_user] = previous


def close_the_half_day_through_the_api(application: Application) -> list[int]:
    """The administrator's own act: PUT the week with one half-day closed."""
    deps.get_instance.cache_clear()
    instance = deps.get_instance()
    closing = [
        s.index for s in instance.slots if s.day_index == CLOSED_DAY and s.period_index in AFTERNOON
    ]
    with as_role(UserRole.ADMINISTRATOR):
        response = application.client.put(
            "/api/calendar",
            json={"slots": [{"slot": index, "isOpen": False} for index in closing]},
        )
    assert response.status_code == 200, response.text
    return closing


@pytest.fixture
def administered() -> Iterator[Application]:
    """The application over a fake solver, with a calendar store of its own."""
    solver = FakeSolver()
    with wire_application(lambda: solver) as wired:
        yield wired
    deps.get_calendar_store.cache_clear()


def test_an_administrator_closes_a_half_day_through_the_interface(
    administered: Application,
) -> None:
    """The half of the criterion Phase 11 delivers: *reachable* configuration.

    Until Phase 11 "in configuration" meant editing `slots.csv` by hand - real,
    tested, and reachable by nobody, which is why FR-9 stayed `WIP` over
    working software.
    """
    closed = close_the_half_day_through_the_api(administered)

    instance = administered.client.get("/api/instance")
    assert instance.status_code == 200
    by_index = {s["index"]: s for s in instance.json()["slots"]}
    assert closed, "the reference instance must have a Wednesday afternoon to close"
    assert all(by_index[index]["isOpen"] is False for index in closed)


def test_the_closed_slots_appear_in_no_timetable_of_the_next_run(
    administered: Application,
) -> None:
    """**The criterion itself, through the screen** - the application's half.

    ⚠️ The fake solver is a real detector here rather than a convenience: it
    draws every start from `instance.slots ... if s.is_open`, so a closure that
    was saved but never reached run assembly - the whole risk of layering an
    edit over an `lru_cache`d instance - would put starts straight onto the
    closed slots. With 28 open slots and 218 sessions cycling through them, it
    would do so many times over.

    ⚠️ **It asserts on the START slot, and deliberately not on occupancy.** The
    fake places by start index and models neither H8 nor H9, so a two-period
    session it starts on the last open period of a day spills into the next
    slot - measured here on the first run, S0012 at slot 12 reaching the closed
    13. That is a property of the double, not of the product: **whether a
    closed slot is free of OCCUPANCY is a question about the engine**, and
    `test_the_closed_slots_appear_in_no_timetable` above answers it against
    real CP-SAT at production settings. Do not "strengthen" this assertion to
    occupancy; it would be asserting H9 against something that does not
    implement it.
    """
    closed = set(close_the_half_day_through_the_api(administered))

    run = administered.launch()

    assert run["state"] == "COMPLETED", run["error"]
    assert run["candidates"], "a completed run must carry candidates"
    for candidate in run["candidates"]:
        for placement in candidate["placements"]:
            assert placement["slot"] not in closed, (
                f"{placement['session']} starts on a closed slot in candidate {candidate['id']}"
            )


def test_the_pre_analysis_measures_the_week_the_administrator_left(
    administered: Application,
) -> None:
    """The operator is told what the closure cost, on the very next run.

    ⚠️ This is the answer to "why is a calendar that makes the instance
    infeasible saved rather than refused": the report names the margin. On this
    instance the closure takes `Lab_Info` to exactly 100.0 % of its two-period
    windows, so the next closure has nowhere to come from - and C-13 is the
    record of what reading only the period figure costs.
    """
    close_the_half_day_through_the_api(administered)

    run = administered.launch()

    coverage = next(c for c in run["preAnalysis"] if c["name"] == "SLOT_COVERAGE")
    assert "80/80 2-period windows = 100.0%" in coverage["detail"]


def test_a_closure_can_be_withdrawn_and_the_loaded_calendar_returns(
    administered: Application,
) -> None:
    """⚠️ The reason the edit is LAYERED rather than written into the instance.

    `services/calendar.py` says an edit that is layered can be withdrawn and an
    edit written into the loaded instance cannot. This is that sentence as a
    test: after `DELETE`, the week is the one the 13 CSVs describe.
    """
    closed = close_the_half_day_through_the_api(administered)

    with as_role(UserRole.ADMINISTRATOR):
        reset = administered.client.delete("/api/calendar")
    assert reset.status_code == 200, reset.text

    by_index = {s["index"]: s for s in administered.client.get("/api/instance").json()["slots"]}
    assert all(by_index[index]["isOpen"] is True for index in closed)


def test_a_holiday_list_is_stated_and_withdrawn_as_a_whole(
    administered: Application,
) -> None:
    """⚠️ An EMPTY list is a statement; a missing one is not.

    "There are no holidays this year" and "nobody has said" are different
    facts, and only the first withdraws the instance's own eighteen.
    """
    with as_role(UserRole.ADMINISTRATOR):
        stated = administered.client.put(
            "/api/calendar",
            json={
                "slots": [],
                "holidays": [
                    {
                        "date": "2026-03-20",
                        "label": "Aid el-Fitr",
                        "lunar": True,
                        "approximate": True,
                        "blocking": True,
                    }
                ],
            },
        )
        assert stated.status_code == 200, stated.text
        assert [h["label"] for h in stated.json()["holidays"]] == ["Aid el-Fitr"]
        assert stated.json()["holidaysStated"] is True

        emptied = administered.client.put("/api/calendar", json={"slots": [], "holidays": []})
        assert emptied.json()["holidays"] == []
        assert emptied.json()["holidaysStated"] is True

        withdrawn = administered.client.delete("/api/calendar")

    assert withdrawn.json()["holidaysStated"] is False
    assert len(withdrawn.json()["holidays"]) == 18


def test_the_shortened_day_shifts_displayed_hours_and_moves_no_slot(
    administered: Application,
) -> None:
    """⚠️ **ADR-003's second effect, and the line it must not cross.**

    A shortened-day window shifts each period's start and end hour and **the
    slot index does not change**, so no variable and no constraint is affected.
    A change that made the shift move a slot would be a calendar rule reaching
    into the model, which is the bug ADR-003 exists to prevent.
    """
    before = {s["index"]: s for s in administered.client.get("/api/instance").json()["slots"]}

    with as_role(UserRole.ADMINISTRATOR):
        response = administered.client.put(
            "/api/calendar",
            json={
                "slots": [],
                "shortenedDay": {
                    "start": "2026-02-18",
                    "end": "2026-03-19",
                    "shiftMinutes": 60,
                },
            },
        )
    assert response.status_code == 200, response.text

    shifted = {row["slot"]: row for row in response.json()["shiftedHours"]}
    first = min(shifted)
    assert shifted[first]["startHour"] == "09:30", "08:30 + 60 minutes"

    after = {s["index"]: s for s in administered.client.get("/api/instance").json()["slots"]}
    assert list(after) == list(before), "the shift must not renumber a slot"
    assert all(after[i]["isOpen"] == before[i]["isOpen"] for i in before)
    assert all(after[i]["startHour"] == before[i]["startHour"] for i in before), (
        "the grid keeps its ordinary hours; the window shifts what is DISPLAYED for it"
    )


def test_only_an_administrator_may_state_the_calendar(administered: Application) -> None:
    """SRS Table 2 gives the calendar to the administrator, and C-8 settled
    that Table 2 wins where the prose disagrees.

    ⚠️ The person in charge is refused too. They have read and write on all
    *data*; the calendar is the other actor's surface, and widening it to
    "whoever has the most rights elsewhere" would be this layer deciding a
    right the specification assigns.
    """
    for role in (UserRole.PERSON_IN_CHARGE, UserRole.TEACHER, UserRole.STUDENT):
        with as_role(role, username=role.value.lower()):
            assert administered.client.get("/api/calendar").status_code == 403, role
            assert administered.client.put("/api/calendar", json={"slots": []}).status_code == 403
            assert administered.client.delete("/api/calendar").status_code == 403, role


def test_a_calendar_naming_a_slot_that_does_not_exist_is_refused(
    administered: Application,
) -> None:
    """422 rather than a silently ignored row: a slot index nobody recognises
    means the client and the instance disagree about the week."""
    with as_role(UserRole.ADMINISTRATOR):
        response = administered.client.put(
            "/api/calendar", json={"slots": [{"slot": 9999, "isOpen": False}]}
        )

    assert response.status_code == 422
    assert "9999" in response.json()["detail"]


def test_one_slot_stated_twice_is_refused(administered: Application) -> None:
    """Two entries saying different things about one slot is a client bug, not
    a merge to resolve silently - `routers/availability` refuses the same."""
    with as_role(UserRole.ADMINISTRATOR):
        response = administered.client.put(
            "/api/calendar",
            json={"slots": [{"slot": 13, "isOpen": False}, {"slot": 13, "isOpen": True}]},
        )

    assert response.status_code == 422
    assert "13" in response.json()["detail"]


def test_the_administration_screen_shows_what_the_instance_loaded(
    administered: Application,
) -> None:
    """⚠️ So a closure reads as a CHANGE rather than as a state.

    Without the loaded week beside the effective one, an administrator opening
    the screen cannot tell a half-day their predecessor closed from one the
    institution's own files never opened.
    """
    closed = close_the_half_day_through_the_api(administered)

    with as_role(UserRole.ADMINISTRATOR):
        calendar = administered.client.get("/api/calendar").json()

    assert set(closed).issubset(set(calendar["loadedOpenSlots"])), (
        "the loaded calendar has these slots open; only the stated one closes them"
    )
    assert all(s["isOpen"] is False for s in calendar["slots"] if s["index"] in set(closed))
    assert calendar["editedBy"] == "administrateur"
    assert calendar["openSlotCount"] == 28 - len(closed)
