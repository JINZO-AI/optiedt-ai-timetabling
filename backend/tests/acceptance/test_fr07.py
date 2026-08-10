"""FR-7 — display the timetable by teacher, by group and by room.

    Verified against SRS §3.2 Table 9, quoted (docs/testing-strategy.md §4):
    input      "Published timetable and chosen filter"
    processing "Selection of the sessions concerning the resource"
    output     "Weekly grid of the resource"

    And SRS §4.1, which names the screen:
    "Timetable view: weekly grid filtered by teacher, group, classroom or
     laboratory, with printing of the displayed view."

⚠️ **FR-7 has no row in SRS Table 35.** Its §3.2 row is the promise, which is
why this file can exist while FR-10's cannot — see docs/testing-strategy.md §4.

⚠️ **This requirement is split across the layer boundary, and so is its
evidence.** The *selection* and the *grid* are display logic, permitted to the
presentation layer by docs/architecture.md ("display, filter, print"), and they
live in `frontend/src/features/timetable/`. What no frontend test can establish
is whether the API hands the screen enough to filter with — and what no backend
test can establish is whether the filtering is right. Both halves exist and
neither substitutes for the other, exactly as FR-15's do:

    frontend/src/features/timetable/model.test.ts        the selection
    frontend/src/features/timetable/TimetableGrid.test.tsx  the weekly grid

This file is the API half: **every placement a run returns must be resolvable
to all three resources, and to a slot with a place in the week.** A timetable
whose placements name a room the instance never defined would filter to an
empty grid on screen with nothing failing anywhere.
"""

from __future__ import annotations

from collections import defaultdict

import pytest

from tests.acceptance.conftest import Application

pytestmark = pytest.mark.acceptance

#: The three filters SRS §4.1 names. "classroom or laboratory" is one
#: dimension — a room — because both are rooms differing only by `RoomType`.
DIMENSIONS = ("teacher", "group", "room")


def _instance(application: Application) -> dict[str, object]:
    response = application.client.get("/api/instance")
    assert response.status_code == 200, response.text
    return dict(response.json())


def _first_candidate(run: dict[str, object]) -> dict[str, object]:
    candidates = run["candidates"]
    assert isinstance(candidates, list) and candidates
    return dict(candidates[0])


def test_every_placement_names_a_session_a_slot_and_a_room(
    application: Application,
) -> None:
    """The three keys the three filters select on.

    A placement is the whole of what a grid draws, so a missing field is not a
    display bug — it is a cell that cannot be drawn at all.
    """
    run = application.launch()
    candidate = _first_candidate(run)

    assert candidate["placements"]
    for placement in candidate["placements"]:
        assert set(placement) == {"session", "slot", "room"}


def test_every_placement_resolves_to_a_teacher_a_group_and_a_room(
    application: Application,
) -> None:
    """Table 9's processing row is only possible if the resource is knowable.

    A `Placement` carries ids alone. The teacher and the group come from the
    session, the room from the placement, and all three must be findable in the
    instance payload the same request served — otherwise a filter has nothing
    to match on and the screen silently shows an empty week.
    """
    run = application.launch()
    candidate = _first_candidate(run)
    instance = _instance(application)

    sessions = {s["id"]: s for s in instance["sessions"]}
    teachers = {t["id"] for t in instance["teachers"]}
    groups = {g["id"] for g in instance["groups"]}
    rooms = {r["id"] for r in instance["rooms"]}

    for placement in candidate["placements"]:
        session = sessions.get(placement["session"])
        assert session is not None, f"{placement['session']} is not in the instance"
        assert session["teacher"] in teachers
        assert session["group"] in groups
        assert placement["room"] in rooms


def test_every_occupied_slot_has_a_place_in_the_week(application: Application) -> None:
    """Table 9's output row: a *weekly grid*, which needs axes.

    Each period a session occupies — both of them, for the 104 two-period
    sessions — must map to a slot carrying a day, a period and the hours to
    label the row with. A session running past the end of the defined week
    would be a placement with nowhere to be drawn.
    """
    run = application.launch()
    candidate = _first_candidate(run)
    instance = _instance(application)

    sessions = {s["id"]: s for s in instance["sessions"]}
    slots = {s["index"]: s for s in instance["slots"]}

    for placement in candidate["placements"]:
        duration = sessions[placement["session"]]["durationPeriods"]
        for period in range(placement["slot"], placement["slot"] + duration):
            slot = slots.get(period)
            assert slot is not None, f"{placement['session']} occupies undefined slot {period}"
            assert isinstance(slot["dayIndex"], int)
            assert isinstance(slot["periodIndex"], int)
            assert slot["startHour"] and slot["endHour"]


def test_a_closed_slot_is_served_as_data_rather_than_omitted(
    application: Application,
) -> None:
    """Why the grid can draw a closed Saturday as closed.

    `isOpen` reaches the screen for every slot, so the week keeps its shape and
    a closed half-day is visibly closed rather than mysteriously absent. This is
    invariant 7 and ADR-003 seen from the wire: the calendar is configuration,
    and the interface must never decide for itself that a day is shut.
    """
    application.launch()
    instance = _instance(application)

    assert all("isOpen" in slot for slot in instance["slots"])
    assert any(not slot["isOpen"] for slot in instance["slots"]), (
        "the reference instance closes 2 of its 30 slots — if none is closed, "
        "this test can no longer tell a served flag from an omitted one"
    )


@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_every_resource_the_screen_offers_can_be_selected(
    application: Application, dimension: str
) -> None:
    """A filter is only usable if its whole list of choices is on the wire.

    The screen builds its dropdown from the instance — every teacher, every
    group, every room — so each must be present, and every value a placement
    filters on must be one of the offered choices. A room that appeared in a
    placement but not in `rooms` would be a timetable entry no filter could
    ever select.
    """
    run = application.launch()
    candidate = _first_candidate(run)
    instance = _instance(application)
    sessions = {s["id"]: s for s in instance["sessions"]}

    offered = {r["id"] for r in instance[f"{dimension}s"]}
    assert offered, f"the screen has no {dimension} to offer"

    used = {
        placement["room"] if dimension == "room" else sessions[placement["session"]][dimension]
        for placement in candidate["placements"]
    }

    assert used <= offered, (
        f"placements name {dimension}s the screen cannot offer: {used - offered}"
    )


def test_selecting_by_teacher_or_by_room_partitions_the_timetable(
    application: Application,
) -> None:
    """Two of the three filters are partitions; the group filter is not.

    A session has one teacher and one room, so those views divide the timetable
    into disjoint pieces. The group view deliberately does not — a CM gathers
    the whole promotion, so a subgroup's week includes its ancestors' sessions
    and the pieces overlap. That asymmetry is the rule the next test states, and
    it is easy to "tidy away" by someone who assumes all three behave alike.
    """
    run = application.launch()
    candidate = _first_candidate(run)
    instance = _instance(application)
    sessions = {s["id"]: s for s in instance["sessions"]}

    for dimension in ("teacher", "room"):
        buckets: dict[str, set[str]] = defaultdict(set)
        for placement in candidate["placements"]:
            key = (
                placement["room"]
                if dimension == "room"
                else sessions[placement["session"]][dimension]
            )
            buckets[key].add(placement["session"])

        total = sum(len(bucket) for bucket in buckets.values())
        assert total == len(candidate["placements"]), (
            f"the {dimension} view double-counts or drops sessions"
        )


def test_a_subgroup_is_concerned_by_its_promotion_s_sessions(
    application: Application,
) -> None:
    """The instance supports the ancestor rule the group view depends on.

    Every group carries `parentGroup`, so the screen can walk a TP subgroup up
    to its TD group and its promotion. Without that chain on the wire, a
    subgroup shown only the sessions addressed to it would display a week with
    holes its students do not have — and the API, not the screen, would be the
    reason.
    """
    application.launch()
    instance = _instance(application)
    groups = {g["id"]: g for g in instance["groups"]}

    leaves = [g for g in instance["groups"] if g["level"] == "TP"]
    assert leaves, "the reference instance has 30 TP subgroups"

    for leaf in leaves:
        chain, current = [], leaf["id"]
        while current is not None:
            chain.append(current)
            current = groups[current]["parentGroup"]
        assert len(chain) == 3, (
            f"{leaf['id']} reaches {chain} — the hierarchy is promotion → TD → TP, "
            "and a broken chain hides a CM from the students who attend it"
        )


def test_a_published_timetable_carries_what_a_view_needs(
    application: Application,
) -> None:
    """Table 9's input row says "**Published** timetable and chosen filter".

    The publication endpoint must therefore serve a candidate complete with its
    placements, not a reference a screen would have to resolve against a run it
    may no longer be able to read.
    """
    run = application.launch()
    candidate = _first_candidate(run)

    published = application.client.post(
        f"/api/runs/{run['id']}/candidates/{candidate['id']}/publish"
    )
    assert published.status_code in (200, 201), published.text

    listed = application.client.get("/api/publications")
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body, "a published timetable did not come back"

    placements = body[0]["candidate"]["placements"]
    assert len(placements) == len(candidate["placements"])
    assert all(set(p) == {"session", "slot", "room"} for p in placements)
