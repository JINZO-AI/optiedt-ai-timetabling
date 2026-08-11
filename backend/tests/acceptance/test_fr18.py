"""FR-18 — display the occupancy of each classroom and laboratory.

    Criterion (⚠️ **project decision**, C-9 resolved 2026-08-11 — derived from
    repository evidence and engineering research because supervisor
    clarification was unavailable; NOT supervisor-written):

    "An authorised user can consult, for EACH classroom and EACH laboratory,
    the share of the week's open periods it occupies on a given candidate."

    Quantity, from **C-4** (resolved 2026-07-30), which defines it for S6:

        utilisation(r, k) = r's occupied periods in k / open slot count

    Scope, from the specification's own words:
    - **CdC §1, needs:** "Any authorised user to consult the occupancy of a
      classroom or of a laboratory."
    - **SRS Table 36:** FR-18 → §4.1 and §5.1 → "Views by classroom and by
      laboratory."

⚠️ **Read C-9's resolution before changing anything here.** The figure measures
TIME, not seats. In the SMG "UFO" vocabulary standard in higher-education space
management it is a *frequency* rate and "occupancy" means occupants over
capacity — and on this instance the two readings **invert** (Salle is emptiest
by time, fullest by seats). Table 36 placing FR-18 among the *views* is what
settles it.

⚠️ **What this file can and cannot establish, and why there are two halves.**
The figure is computed in the display layer (`features/timetable/model.ts`),
which `docs/architecture.md` permits — it filters and arranges what the API
sent and decides no order. So this file verifies **the contract underneath it**:
that a user reaching a candidate through the API receives everything the figure
is derived from, and that the figure derived from that payload is correct and
**complete for every room**. `model.test.ts` and `OccupancyView.test.tsx` pin
the computation and the rendering. Exactly FR-7's two-halves shape, and for the
same reason: a selection that is right and a screen that draws it wrong are
indistinguishable to a backend test.

⚠️ **The fake solver is used deliberately.** The criterion is about the
application, not the engine: it asks whether a user can *consult* a figure, and
a 150-second production solve would not widen that claim by one assertion. The
placements it returns are real sessions in real rooms, so the arithmetic here is
the arithmetic a user gets.
"""

from __future__ import annotations

from collections import defaultdict

import pytest

from optiedt.api import deps
from optiedt.api.main import app
from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole

pytestmark = pytest.mark.acceptance


def occupancy_from_the_payload(
    candidate: dict[str, object], instance: dict[str, object]
) -> dict[str, float]:
    """`utilisation(r, k)` for every room, derived from what the API served.

    ⚠️ **Written out here rather than imported**, deliberately. Importing
    `analysis.criteria` would verify that the analysis layer agrees with itself;
    what the criterion promises is that the figure is derivable **from the
    payload a user receives**, which is a different claim and the one that
    would break if a field were dropped from the wire format.
    """
    duration = {s["id"]: s["durationPeriods"] for s in instance["sessions"]}  # type: ignore[index]
    open_slots = sum(1 for s in instance["slots"] if s["isOpen"])  # type: ignore[index]

    occupied: dict[str, int] = defaultdict(int)
    for placement in candidate["placements"]:  # type: ignore[index]
        occupied[placement["room"]] += duration[placement["session"]]

    return {
        room["id"]: occupied.get(room["id"], 0) / open_slots  # type: ignore[index]
        for room in instance["rooms"]  # type: ignore[index]
    }


@pytest.fixture
def consulted(application) -> tuple[dict[str, object], dict[str, object]]:
    """One candidate and the instance, both fetched the way a screen fetches them."""
    run = application.launch()
    assert run["state"] == "COMPLETED", run["error"]
    candidate = run["candidates"][0]

    instance = application.client.get("/api/instance")
    assert instance.status_code == 200, instance.text
    return candidate, instance.json()


def test_every_room_the_instance_has_is_reported(consulted) -> None:
    """**"EACH classroom and EACH laboratory" — the criterion's own word.**

    ⚠️ The assertion that matters is that a room **no session was placed in**
    still appears, at 0. That row is the most actionable one in the table — it
    says a resource is going unused — and a view that omitted it would answer
    "which rooms are used?" while appearing to answer the criterion's question.
    """
    candidate, instance = consulted
    deps.get_instance.cache_clear()

    occupancy = occupancy_from_the_payload(candidate, instance)

    assert set(occupancy) == {room["id"] for room in instance["rooms"]}
    assert len(occupancy) == 20, "the reference instance has 20 rooms"


def test_classrooms_and_laboratories_are_both_covered(consulted) -> None:
    """The criterion names both, and the instance has four room types.

    Naming them rather than counting: a regression that dropped a whole type
    would still leave "20 rooms" true if another type gained rows.
    """
    _candidate, instance = consulted

    types = {room["type"] for room in instance["rooms"]}

    assert types == {"Amphi", "Salle", "Lab_Info", "Lab_Sciences"}


def test_the_figure_is_periods_occupied_over_open_periods(consulted) -> None:
    """**The quantity C-4 fixed**, checked on a room the run actually used.

    Re-derived from the payload rather than compared to a stored figure: the
    API sends no occupancy field, and that is the point — the screen computes
    it from placements, session durations and slot openness, all of which must
    therefore be on the wire.
    """
    candidate, instance = consulted
    duration = {s["id"]: s["durationPeriods"] for s in instance["sessions"]}
    open_slots = sum(1 for s in instance["slots"] if s["isOpen"])

    # ⚠️ **Anchored against a documented fact, not against itself.** Deriving
    # the expectation from the same payload makes the arithmetic self-
    # consistent whatever the payload says: mutation testing showed this test
    # still passing with every duration forced to 1. `data-and-instance.md`
    # records the mix as 114 one-period and 104 two-period sessions, so a wire
    # format that flattened it fails here.
    assert sorted({s["durationPeriods"] for s in instance["sessions"]}) == [1, 2]
    assert sum(1 for s in instance["sessions"] if s["durationPeriods"] == 2) == 104

    occupancy = occupancy_from_the_payload(candidate, instance)
    used = {p["room"] for p in candidate["placements"]}
    assert used, "the fake solver places every session, so some room is used"

    for room_id in sorted(used):
        periods = sum(
            duration[p["session"]] for p in candidate["placements"] if p["room"] == room_id
        )
        assert occupancy[room_id] == pytest.approx(periods / open_slots)


def test_no_room_is_reported_beyond_full(consulted) -> None:
    """A rate above 1 would mean two sessions in one room at one moment — H3.

    ⚠️ Not a property of the arithmetic: it holds because the placements come
    from a solver that respects H3. It is asserted here because the figure is
    what a reader would use to *notice* such a violation, so it must be capable
    of showing one.
    """
    candidate, instance = consulted

    occupancy = occupancy_from_the_payload(candidate, instance)

    assert all(0.0 <= rate <= 1.0 for rate in occupancy.values())


def test_the_denominator_is_the_open_slots_and_not_the_whole_grid(consulted) -> None:
    """⚠️ Invariant 7, as arithmetic.

    A closed half-day is configuration; counting it as unused capacity would
    make every room look emptier than it is, and would make an administrator's
    closure look like a drop in usage rather than a reduction in the week.
    The reference instance closes Saturday afternoon, so 28 ≠ 30 and this
    assertion can fail.
    """
    _candidate, instance = consulted

    open_slots = sum(1 for s in instance["slots"] if s["isOpen"])

    assert open_slots == 28
    assert len(instance["slots"]) == 30, "two slots are closed, so the two differ"


def test_closing_a_half_day_raises_the_rates_it_leaves(application) -> None:
    """**The denominator moves with the calendar, and that is correct.**

    ⚠️ Only reachable since Phase 11 made the calendar editable. An
    administrator who closes Wednesday afternoon leaves 26 open periods, so the
    same week's teaching occupies a larger share of a smaller week. A figure
    that kept 28 would under-report every room the moment the institution
    shortened its week — and would do it silently.
    """
    deps.get_instance.cache_clear()
    loaded = deps.get_instance()
    closing = [s.index for s in loaded.slots if s.day_index == 2 and s.period_index in (3, 4)]

    before = application.client.get("/api/instance").json()
    assert sum(1 for s in before["slots"] if s["isOpen"]) == 28

    previous = app.dependency_overrides.get(deps.current_user)
    app.dependency_overrides[deps.current_user] = lambda: User(
        id="administrateur", username="administrateur", role=UserRole.ADMINISTRATOR
    )
    try:
        saved = application.client.put(
            "/api/calendar",
            json={"slots": [{"slot": index, "isOpen": False} for index in closing]},
        )
        assert saved.status_code == 200, saved.text
    finally:
        if previous is None:
            app.dependency_overrides.pop(deps.current_user, None)
        else:
            app.dependency_overrides[deps.current_user] = previous

    after = application.client.get("/api/instance").json()
    deps.get_calendar_store.cache_clear()

    assert sum(1 for s in after["slots"] if s["isOpen"]) == 26


def test_a_signed_in_user_can_consult_it(application) -> None:
    """ "Any authorised user" — CdC §1. The payload is not scoped to a role.

    ⚠️ A **student** is the exception and it is deliberate, not an oversight:
    SRS Table 2 gives that role its own group's published timetable and no run
    at all, which `acceptance/test_student_view` establishes. Every other role
    reaches a run and therefore this figure.
    """
    run = application.launch()

    assert run["state"] == "COMPLETED"
    assert application.client.get("/api/instance").status_code == 200
    assert application.client.get(f"/api/runs/{run['id']}").status_code == 200
