"""FR-12 — the five checks, against instances small enough to verify by hand.

Two things are being tested and they are not the same:

1. Each check FAILS when it should, naming the resource and the quantity
   missing. A structural-risk report that returns a boolean is useless, so the
   named detail is asserted, not just `passed is False`.

2. **SLOT_COVERAGE applies the contiguity bound, not only the period bound.**
   That is the whole point of the check. `test_the_original_room_mix_is_caught`
   below reconstructs the instance as it was before the C-13 repair and
   requires the shortfall to be named — the period bound alone passes that
   instance while reporting a comfortable 95.2 %, which is what sent three
   sessions after a solver bug that did not exist.

The reference-instance figures live in
tests/integration/test_preanalysis_matches_verifier.py, which compares this
implementation against the standalone checker rather than against a constant
copied out of a document.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from optiedt.domain.entities import (
    Availability,
    Group,
    Room,
    Session,
    Teacher,
)
from optiedt.domain.enums import (
    AvailabilityState,
    DeclarationSource,
    GroupLevel,
    RoomType,
    SessionType,
    TeacherRank,
)
from optiedt.domain.instance import Instance
from optiedt.instance.loader import load_instance
from optiedt.preanalysis.checks import (
    CHECK_GROUP_HIERARCHY,
    CHECK_ROOM_SUITABILITY,
    CHECK_SLOT_COVERAGE,
    CHECK_TEACHER_FREE_SLOTS,
    CHECK_TEACHER_LOAD,
)
from optiedt.preanalysis.verifications import (
    ALL_CHECKS,
    DefaultPreAnalysis,
    GroupHierarchy,
    RoomSuitability,
    SlotCoverage,
    TeacherFreeSlots,
    TeacherLoad,
    contiguous_open_runs,
    windows_per_room,
)

INSTANCE_PATH = Path(__file__).resolve().parents[3] / "data" / "instance"


def _group(group_id: str, parent: str | None, level: GroupLevel) -> Group:
    return Group(
        id=group_id, promotion="PR1", parent_group=parent, level=level, label=group_id, size=30
    )


def result_named(instance: Instance, name: str):
    return next(r for r in DefaultPreAnalysis().verify(instance) if r.name == name)


# ── The shape of the report ────────────────────────────────────────────


def test_all_five_checks_are_reported_in_the_documented_order(tiny_instance: Instance) -> None:
    results = DefaultPreAnalysis().verify(tiny_instance)
    assert [r.name for r in results] == [
        CHECK_ROOM_SUITABILITY,
        CHECK_SLOT_COVERAGE,
        CHECK_TEACHER_LOAD,
        CHECK_TEACHER_FREE_SLOTS,
        CHECK_GROUP_HIERARCHY,
    ]


def test_every_check_reports_figures_even_when_it_passes(tiny_instance: Instance) -> None:
    """Passing is not the same as being safe.

    The reference instance passes SLOT_COVERAGE at 90.9 % of two-period
    windows, 8 spare in the week. A report that said only "passed" would hide
    the number most worth watching.
    """
    for result in DefaultPreAnalysis().verify(tiny_instance):
        assert result.passed, result.detail
        assert result.detail, f"{result.name} passed without saying anything"
        assert result.resource is None
        assert result.missing_quantity is None


def test_the_five_names_are_the_five_declared_in_the_contract() -> None:
    assert {c.name for c in ALL_CHECKS} == {
        CHECK_ROOM_SUITABILITY,
        CHECK_SLOT_COVERAGE,
        CHECK_TEACHER_LOAD,
        CHECK_TEACHER_FREE_SLOTS,
        CHECK_GROUP_HIERARCHY,
    }


# ── The contiguity arithmetic itself ───────────────────────────────────


def test_a_five_period_day_offers_two_two_period_windows(tiny_instance: Instance) -> None:
    """The arithmetic C-13 turned on, isolated.

    Two open days of five periods each: 10 periods, but only 2 two-period
    windows per day, so 4 per room per week — not 5. One period per room-day is
    structurally unusable because a 5-period run does not tile with 2-period
    sessions.
    """
    runs = contiguous_open_runs(tiny_instance)
    assert runs == (5, 5)
    assert windows_per_room(runs, 1) == 10
    assert windows_per_room(runs, 2) == 4
    assert windows_per_room(runs, 3) == 2


def test_a_closed_period_splits_a_day_into_two_shorter_runs(tiny_instance: Instance) -> None:
    """A hole in the middle of a day is not the same as a shorter day.

    One 5-period day offers 2 two-period windows. Close its second period and 4
    periods remain — but as runs of 1 and 3, which offer only 1 window between
    them. Counting the 4 remaining periods would say 2. The check must read
    runs, not totals: this is where H9 (closed slots) and H8 (one day) meet, and
    it is what makes the closed Saturday afternoon cost more than its two
    periods.
    """
    one_day = tuple(s for s in tiny_instance.slots if s.day_index == 0)
    instance = dataclasses.replace(
        tiny_instance,
        slots=tuple(dataclasses.replace(s, is_open=s.period_index != 1) for s in one_day),
    )
    runs = contiguous_open_runs(instance)
    assert runs == (1, 3)
    assert sum(runs) == 4
    assert windows_per_room(runs, 2) == 1


# ── 1. Room suitability ────────────────────────────────────────────────


def test_room_suitability_names_the_type_and_the_missing_places(
    tiny_instance: Instance,
) -> None:
    instance = dataclasses.replace(
        tiny_instance,
        rooms=(Room(id="R1", building="B", code="R1", capacity=10, type=RoomType.SALLE),),
    )
    result = RoomSuitability().run(instance)
    assert not result.passed
    assert result.resource == "Salle"
    # The largest Salle seats 10; the biggest group is 30. Short by 20.
    assert result.missing_quantity == 20.0
    assert "short by 20" in result.detail


def test_room_suitability_fails_when_no_room_of_the_type_exists(
    tiny_instance: Instance,
) -> None:
    """A missing room TYPE must not read as a capacity problem of zero."""
    instance = dataclasses.replace(
        tiny_instance,
        sessions=tuple(
            dataclasses.replace(s, required_room_type=RoomType.LAB_INFO)
            for s in tiny_instance.sessions
        ),
    )
    result = RoomSuitability().run(instance)
    assert not result.passed
    assert result.resource == "Lab_Info"


# ── 2. Slot coverage — both bounds ─────────────────────────────────────


def test_slot_coverage_fails_on_the_period_bound(tiny_instance: Instance) -> None:
    """One room, 10 open periods, 11 one-period sessions."""
    sessions = tuple(
        Session(
            id=f"s{i}",
            course="C1",
            group="T",
            teacher="T1",
            type=SessionType.TD,
            duration_periods=1,
            occurrences_per_week=1,
            required_room_type=RoomType.SALLE,
            locked=False,
        )
        for i in range(11)
    )
    instance = dataclasses.replace(
        tiny_instance,
        sessions=sessions,
        rooms=(Room(id="R1", building="B", code="R1", capacity=30, type=RoomType.SALLE),),
    )
    result = SlotCoverage().run(instance)
    assert not result.passed
    assert result.resource == "Salle"
    assert result.missing_quantity == 1.0
    assert "periods" in result.detail


def test_slot_coverage_fails_on_contiguity_where_the_period_bound_passes(
    tiny_instance: Instance,
) -> None:
    """The C-13 shape, in miniature — and the reason this test exists.

    One room, two open 5-period days: 10 open periods. Five two-period sessions
    need 10 periods, so the PERIOD bound reports exactly 100 % and passes. But
    a 5-period run offers only 2 disjoint two-period windows, so the room
    offers 4 in the week against 5 required. No timetable exists, and only the
    contiguity bound can say so.
    """
    sessions = tuple(
        Session(
            id=f"s{i}",
            course="C1",
            group="T",
            teacher=f"T{i}",
            type=SessionType.TP,
            duration_periods=2,
            occurrences_per_week=1,
            required_room_type=RoomType.SALLE,
            locked=False,
        )
        for i in range(5)
    )
    instance = dataclasses.replace(
        tiny_instance,
        sessions=sessions,
        teachers=tuple(
            Teacher(id=f"T{i}", department="D", rank=TeacherRank.ASSISTANT, max_hours_per_week=18)
            for i in range(5)
        ),
        rooms=(Room(id="R1", building="B", code="R1", capacity=30, type=RoomType.SALLE),),
    )
    result = SlotCoverage().run(instance)

    assert not result.passed, "the contiguity bound did not fire — only the period bound is applied"
    assert result.resource == "Salle"
    assert result.missing_quantity == 1.0
    assert "2-period windows" in result.detail
    assert "pigeonhole" in result.detail
    # The period bound is at exactly 100 % here, so it must NOT be what fired.
    assert "10/10 periods = 100.0%" in result.detail


def test_slot_coverage_names_the_binding_resource_even_when_it_passes(
    tiny_instance: Instance,
) -> None:
    """Four two-period sessions against exactly four windows: 100 % and legal."""
    sessions = tuple(
        Session(
            id=f"s{i}",
            course="C1",
            group="T",
            teacher=f"T{i}",
            type=SessionType.TP,
            duration_periods=2,
            occurrences_per_week=1,
            required_room_type=RoomType.SALLE,
            locked=False,
        )
        for i in range(4)
    )
    instance = dataclasses.replace(
        tiny_instance,
        sessions=sessions,
        teachers=tuple(
            Teacher(id=f"T{i}", department="D", rank=TeacherRank.ASSISTANT, max_hours_per_week=18)
            for i in range(4)
        ),
        rooms=(Room(id="R1", building="B", code="R1", capacity=30, type=RoomType.SALLE),),
    )
    result = SlotCoverage().run(instance)
    assert result.passed
    assert "binding resource" in result.detail


@pytest.mark.parametrize(
    ("room_type", "short_by"),
    [(RoomType.LAB_INFO, 14), (RoomType.LAB_SCIENCES, 2)],
)
def test_the_original_room_mix_is_caught(room_type: RoomType, short_by: int) -> None:
    """⚠️ THE C-13 REGRESSION TEST. Do not delete it to make a change compile.

    The reference instance as first generated had Salle 10 / Lab_Info 6 /
    Lab_Sciences 2. It had NO SOLUTION: 80 two-period computer-laboratory
    sessions against 6 rooms x 11 windows = 66, and 24 science-laboratory
    sessions against 2 x 11 = 22.

    It passed verification anyway, because the check compared PERIODS —
    160/168 = a comfortable 95.2 % — and three sessions of work went looking
    for a solver bug that did not exist. This reconstructs that mix from the
    repaired instance by re-typing three rooms back, and requires the check to
    name both shortfalls. If this test ever passes trivially, the contiguity
    bound has been dropped and the blind spot is back inside the product.
    """
    instance = load_instance(INSTANCE_PATH)
    # Re-type the three rooms the C-13 repair converted, in reverse. Room ids
    # are read from the data rather than hardcoded, so the test survives a
    # renumbering of rooms.csv.
    labs_info = [r for r in instance.rooms if r.type is RoomType.LAB_INFO]
    labs_sciences = [r for r in instance.rooms if r.type is RoomType.LAB_SCIENCES]
    reverted = {r.id for r in sorted(labs_info, key=lambda r: r.id)[-2:]} | {
        r.id for r in sorted(labs_sciences, key=lambda r: r.id)[-1:]
    }
    original_mix = dataclasses.replace(
        instance,
        rooms=tuple(
            dataclasses.replace(r, type=RoomType.SALLE) if r.id in reverted else r
            for r in instance.rooms
        ),
    )
    assert sum(1 for r in original_mix.rooms if r.type is RoomType.LAB_INFO) == 6
    assert sum(1 for r in original_mix.rooms if r.type is RoomType.LAB_SCIENCES) == 2

    result = SlotCoverage().run(original_mix)
    assert not result.passed
    assert f"short by {short_by} 2-period windows" in result.detail
    assert f"{room_type} is short by {short_by}" in result.detail


def test_the_repaired_room_mix_passes() -> None:
    """The other half of the regression: the repair must actually hold."""
    result = SlotCoverage().run(load_instance(INSTANCE_PATH))
    assert result.passed, result.detail
    assert "Lab_Info" in result.detail


# ── 3. Teacher load ────────────────────────────────────────────────────


def test_teacher_load_names_the_teacher_and_the_excess_hours(
    tiny_instance: Instance,
) -> None:
    instance = dataclasses.replace(
        tiny_instance,
        teachers=(
            Teacher(id="T1", department="D", rank=TeacherRank.PROFESSEUR, max_hours_per_week=1),
            Teacher(id="T2", department="D", rank=TeacherRank.ASSISTANT, max_hours_per_week=18),
        ),
    )
    result = TeacherLoad().run(instance)
    assert not result.passed
    assert result.resource == "T1"
    # T1 gives two 1-period sessions = 2 periods = 3 h against a 1 h limit.
    assert result.missing_quantity == 2.0
    assert "3 h against a limit of 1 h" in result.detail


def test_teacher_hours_come_from_the_calendar_not_from_a_constant(
    tiny_instance: Instance,
) -> None:
    """ADR-003: an institution running 60-minute periods changes a CSV.

    The same two periods are 3 h at 90 minutes and 2 h at 60, so the same load
    breaches a 2.5 h limit under one calendar and not under the other.
    """
    over = dataclasses.replace(
        tiny_instance,
        teachers=(
            Teacher(id="T1", department="D", rank=TeacherRank.PROFESSEUR, max_hours_per_week=2),
            Teacher(id="T2", department="D", rank=TeacherRank.ASSISTANT, max_hours_per_week=18),
        ),
        calendar_config={**tiny_instance.calendar_config, "period_minutes": "90"},
    )
    assert not TeacherLoad().run(over).passed

    shorter = dataclasses.replace(
        over, calendar_config={**over.calendar_config, "period_minutes": "60"}
    )
    assert TeacherLoad().run(shorter).passed


# ── 4. Teacher free slots ──────────────────────────────────────────────


def test_teacher_free_slots_names_the_teacher_and_the_deficit(
    tiny_instance: Instance,
) -> None:
    """T1 gives 2 periods; leave them only 1 slot free of the 10 open."""
    unavailable = tuple(
        Availability(
            teacher="T1",
            slot=i,
            state=AvailabilityState.UNAVAILABLE,
            semester=2,
            source=DeclarationSource.TEACHER,
        )
        for i in range(9)
    )
    instance = dataclasses.replace(tiny_instance, availability=unavailable)
    result = TeacherFreeSlots().run(instance)
    assert not result.passed
    assert result.resource == "T1"
    assert result.missing_quantity == 1.0
    assert "short by 1" in result.detail


def test_teacher_free_slots_ignores_rows_that_are_not_unavailability(
    tiny_instance: Instance,
) -> None:
    """AVAILABLE and PREFERRED rows must not count against the margin.

    The instance carries only unavailability today (C-12), but the enum admits
    three states and the grid's wire format accepts PREFERRED, so a check that
    counted rows rather than reading `state` would silently start failing the
    day a preferred window is recorded.
    """
    rows = tuple(
        Availability(
            teacher="T1",
            slot=i,
            state=AvailabilityState.PREFERRED,
            semester=2,
            source=DeclarationSource.TEACHER,
        )
        for i in range(9)
    )
    assert TeacherFreeSlots().run(dataclasses.replace(tiny_instance, availability=rows)).passed


# ── 5. Group hierarchy ─────────────────────────────────────────────────


def test_group_hierarchy_catches_a_dangling_parent(tiny_instance: Instance) -> None:
    instance = dataclasses.replace(
        tiny_instance,
        groups=tuple(
            dataclasses.replace(g, parent_group="MISSING") if g.id == "T" else g
            for g in tiny_instance.groups
        ),
    )
    result = GroupHierarchy().run(instance)
    assert not result.passed
    assert result.resource == "T"
    assert "dangling parent reference" in result.detail


def test_group_hierarchy_catches_a_subgroup_hanging_off_a_promotion(
    tiny_instance: Instance,
) -> None:
    """A TP whose parent is a PROMO breaks H12's ancestor walk quietly.

    Nothing raises: the solve succeeds and produces a timetable in which a
    lecture does not gather the subgroup it should. A wrong timetable is worse
    than an absent one, which is why this check is NECESSARY rather than a
    proof of infeasibility.
    """
    instance = dataclasses.replace(
        tiny_instance,
        groups=tuple(
            dataclasses.replace(g, parent_group="P") if g.id == "T" else g
            for g in tiny_instance.groups
        ),
    )
    result = GroupHierarchy().run(instance)
    assert not result.passed
    assert "outside the admitted promotion -> TD -> TP chain" in result.detail


def test_group_hierarchy_catches_a_cycle(tiny_instance: Instance) -> None:
    """H12 walks the chain to the root; a cycle would loop forever."""
    instance = dataclasses.replace(
        tiny_instance,
        # P's parent is G and G's parent is P: the walk never reaches a root.
        groups=(
            _group("P", parent="G", level=GroupLevel.PROMO),
            _group("G", parent="P", level=GroupLevel.TD),
            _group("T", parent="G", level=GroupLevel.TP),
        ),
    )
    result = GroupHierarchy().run(instance)
    assert not result.passed
    assert "in a cycle" in result.detail


def test_group_hierarchy_says_what_it_does_not_check(tiny_instance: Instance) -> None:
    """The student half stays with the standalone verifier, and says so.

    `Instance` excludes `Student` by design, so a narrower check must not pass
    for the documented one.
    """
    result = GroupHierarchy().run(tiny_instance)
    assert "Student" in result.detail
    assert "verify-instance" in result.detail
