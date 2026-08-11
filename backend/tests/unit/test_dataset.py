"""FR-1 — the A7 compatibility rule, and why it takes two checks.

> **Project decision — determined from repository evidence and engineering
> research because supervisor clarification was unavailable.**
>
> A dataset replacement must be rejected if it would leave existing persisted
> FR-2 declarations or FR-9 calendar overrides invalid or orphaned. Existing
> overlay data must not be silently deleted. The existing dataset remains active
> when compatibility validation fails. A successful replacement must preserve
> referential integrity and be committed atomically.

⚠️ **The two checks are not interchangeable and this module is where that is
proved.** An orphaned declaration survives into the effective dataset; an
orphaned closure is swallowed by `apply_calendar` and leaves no trace there.
`test_an_orphaned_closure_is_invisible_in_the_effective_dataset` is the reason
`_closures_that_would_be_orphaned` exists at all — delete it and that test is
the only thing that fails.
"""

from __future__ import annotations

import dataclasses

import pytest

from optiedt.domain.entities import Availability
from optiedt.domain.enums import AvailabilityState, DeclarationSource
from optiedt.domain.instance import Instance
from optiedt.instance.loader import load_instance, resolve_instance_path
from optiedt.services.availability import (
    InMemoryAvailabilityStore,
    apply_declarations,
    build_declaration,
)
from optiedt.services.calendar import (
    CalendarOverrides,
    InMemoryCalendarStore,
    apply_calendar,
)
from optiedt.services.dataset import (
    AVAILABILITY_OVERLAY,
    CALENDAR_OVERLAY,
    DECLARED_MARKER_SLOT,
    InMemoryDatasetStore,
    check_compatibility,
)


@pytest.fixture(scope="module")
def reference() -> Instance:
    return load_instance(resolve_instance_path("../data/instance"))


@pytest.fixture
def availability() -> InMemoryAvailabilityStore:
    return InMemoryAvailabilityStore()


@pytest.fixture
def calendar() -> InMemoryCalendarStore:
    return InMemoryCalendarStore()


def without_teacher(instance: Instance, teacher: str) -> Instance:
    """A candidate dataset that no longer declares one teacher.

    Its own availability rows go too, or the candidate would fail the
    validator's own reference check and never reach a compatibility question.
    """
    return dataclasses.replace(
        instance,
        teachers=tuple(t for t in instance.teachers if t.id != teacher),
        availability=tuple(a for a in instance.availability if a.teacher != teacher),
        sessions=tuple(s for s in instance.sessions if s.teacher != teacher),
    )


def without_slots_from(instance: Instance, first_dropped: int) -> Instance:
    return dataclasses.replace(
        instance,
        slots=tuple(s for s in instance.slots if s.index < first_dropped),
        availability=tuple(a for a in instance.availability if a.slot < first_dropped),
    )


def declare(store: InMemoryAvailabilityStore, teacher: str, slots: list[int]) -> None:
    store.declare(
        teacher,
        build_declaration(
            teacher=teacher,
            semester=2,
            cells={slot: AvailabilityState.UNAVAILABLE for slot in slots},
        ),
    )


# ── Nothing stored, nothing to orphan ──────────────────────────────────


def test_a_first_import_on_an_untouched_installation_is_compatible(
    reference, availability, calendar
) -> None:
    """⚠️ The primary path costs nothing: with no declarations and no calendar
    the rule is vacuous, which is why it does not complicate a fresh install."""
    assert check_compatibility(reference, availability, calendar) == ()


def test_replacing_a_dataset_with_itself_is_compatible(reference, availability, calendar) -> None:
    declare(availability, "T001", [13, 14])
    calendar.save(CalendarOverrides(slot_open=((7, False),)), author="administrateur")

    assert check_compatibility(reference, availability, calendar) == ()


# ── FR-2 declarations ──────────────────────────────────────────────────


def test_a_declaration_whose_teacher_is_gone_rejects_the_replacement(
    reference, availability, calendar
) -> None:
    declare(availability, "T001", [13, 14])

    found = check_compatibility(without_teacher(reference, "T001"), availability, calendar)

    assert [(f.overlay, f.subject) for f in found] == [(AVAILABILITY_OVERLAY, "T001")]
    assert "does not declare that teacher" in found[0].reason
    assert "clear that declaration first" in found[0].remedy


def test_a_teacher_who_never_declared_anything_does_not_block(
    reference, availability, calendar
) -> None:
    """T002 is in the instance's own generated rows but has stored nothing.
    Removing them is the institution's business, not an orphaned statement."""
    declare(availability, "T001", [13])

    assert check_compatibility(without_teacher(reference, "T002"), availability, calendar) == ()


def test_a_declaration_whose_slot_is_gone_rejects_the_replacement(
    reference, availability, calendar
) -> None:
    declare(availability, "T001", [26, 27])

    found = check_compatibility(without_slots_from(reference, 25), availability, calendar)

    assert {f.overlay for f in found} == {AVAILABILITY_OVERLAY}
    assert {f.subject for f in found} == {"T001:26", "T001:27"}


def test_every_orphaned_declaration_is_reported_not_only_the_first(
    reference, availability, calendar
) -> None:
    declare(availability, "T001", [13])
    declare(availability, "T002", [13])
    declare(availability, "T003", [13])
    candidate = without_teacher(without_teacher(reference, "T001"), "T002")

    found = check_compatibility(candidate, availability, calendar)

    assert {f.subject for f in found} == {"T001", "T002"}


# ── Refinement 6: the inert marker ─────────────────────────────────────


def test_an_emptied_declaration_does_not_block_a_departing_teacher(
    reference, availability, calendar
) -> None:
    """⚠️ **This is the escape route, and without it A7 would deadlock.**

    There is no endpoint that forgets a declaration — `AvailabilityStore` has no
    delete — so a teacher who has left could otherwise block every future import
    for good. What the person in charge *can* do is empty that teacher's grid
    (`_require_own_grid` returns early for every role but TEACHER). An emptied
    grid contributes no availability row, so judging compatibility on the
    effective rows rather than on `declared_teachers()` lets the import through.
    """
    declare(availability, "T001", [13, 14])
    declare(availability, "T001", [])  # the person in charge clears it

    assert "T001" in availability.declared_teachers(), "still marked as having answered"
    assert check_compatibility(without_teacher(reference, "T001"), availability, calendar) == ()


def test_the_reserved_marker_index_is_never_read_as_a_slot_reference(
    reference, availability, calendar
) -> None:
    """The SQL store filters `-1` out of every read, so this cannot arise
    through the API. It is asserted anyway because the guard in
    `_declarations_that_would_be_orphaned` is what keeps a store that leaked the
    marker from reporting an incompatibility for a slot nobody declared."""
    availability.declare(
        "T001",
        (
            Availability(
                teacher="T001",
                slot=DECLARED_MARKER_SLOT,
                state=AvailabilityState.AVAILABLE,
                semester=2,
                source=DeclarationSource.TEACHER,
            ),
        ),
    )

    assert check_compatibility(reference, availability, calendar) == ()


def test_the_marker_constant_agrees_with_the_one_the_store_reserves() -> None:
    """⚠️ Two homes for one number. `services` may not import `optiedt.db`, so
    the value is duplicated; this is what keeps the copies honest."""
    from optiedt.db.repositories import _DECLARED_MARKER_SLOT

    assert DECLARED_MARKER_SLOT == _DECLARED_MARKER_SLOT


# ── FR-9 closures: the check the effective dataset cannot make ─────────


def test_a_closure_on_a_slot_that_is_gone_rejects_the_replacement(
    reference, availability, calendar
) -> None:
    calendar.save(CalendarOverrides(slot_open=((26, False),)), author="administrateur")

    found = check_compatibility(without_slots_from(reference, 25), availability, calendar)

    assert [(f.overlay, f.subject) for f in found] == [(CALENDAR_OVERLAY, "26")]
    assert "no such slot" in found[0].reason
    assert "DELETE /api/calendar" in found[0].remedy


def test_an_orphaned_closure_is_invisible_in_the_effective_dataset(
    reference, availability, calendar
) -> None:
    """⚠️ **The whole reason FR-9 needs its own check**, stated as an assertion
    rather than as a comment.

    `apply_calendar` iterates the candidate's slots and consults the stated map
    only for those it finds, so a closure on a slot the candidate does not have
    vanishes without trace. Judged on the effective dataset alone, the
    administrator's statement would be silently deleted — which is exactly what
    the A7 decision forbids.
    """
    calendar.save(CalendarOverrides(slot_open=((26, False),)), author="administrateur")
    candidate = without_slots_from(reference, 25)

    effective = apply_declarations(apply_calendar(candidate, calendar), availability)

    assert all(slot.index != 26 for slot in effective.slots), "the closure left no trace"
    assert effective == apply_declarations(candidate, availability), "indistinguishable"
    # ...and yet:
    assert check_compatibility(candidate, availability, calendar)


def test_every_orphaned_closure_is_reported(reference, availability, calendar) -> None:
    calendar.save(
        CalendarOverrides(slot_open=((26, False), (27, False), (3, False))),
        author="administrateur",
    )

    found = check_compatibility(without_slots_from(reference, 25), availability, calendar)

    assert {f.subject for f in found} == {"26", "27"}, "slot 3 survives and is not orphaned"


def test_a_stated_holiday_list_never_blocks_an_import(reference, availability, calendar) -> None:
    """Holidays reference no entity of the dataset — they are dates. A rule that
    blocked on them would refuse an import for a statement nothing can orphan."""
    calendar.save(
        CalendarOverrides(holidays=(), slot_open=()),
        author="administrateur",
    )

    assert check_compatibility(without_slots_from(reference, 25), availability, calendar) == ()


# ── Both overlays at once ──────────────────────────────────────────────


def test_declarations_and_closures_are_reported_together(reference, availability, calendar) -> None:
    """One trip, one list. A person clearing them one import at a time is being
    made to do the application's work."""
    declare(availability, "T001", [26])
    calendar.save(CalendarOverrides(slot_open=((27, False),)), author="administrateur")

    found = check_compatibility(without_slots_from(reference, 25), availability, calendar)

    assert {f.overlay for f in found} == {AVAILABILITY_OVERLAY, CALENDAR_OVERLAY}


# ── Nothing is written by a check ──────────────────────────────────────


def test_checking_compatibility_deletes_nothing_and_changes_nothing(
    reference, availability, calendar
) -> None:
    """⚠️ *"Existing overlay data must not be silently deleted"* — asserted
    against the stores rather than assumed from the absence of a write."""
    declare(availability, "T001", [13, 14])
    stated = CalendarOverrides(slot_open=((26, False),))
    calendar.save(stated, author="administrateur")

    check_compatibility(without_slots_from(reference, 25), availability, calendar)
    check_compatibility(without_teacher(reference, "T001"), availability, calendar)

    assert availability.declared_teachers() == frozenset({"T001"})
    assert availability.declarations("T001") is not None
    assert len(availability.declarations("T001") or ()) == 2
    assert calendar.overrides() == stated
    assert calendar.last_edit() is not None


def test_the_dataset_store_is_untouched_by_a_check(reference, availability, calendar) -> None:
    store = InMemoryDatasetStore()
    store.save({"rooms.csv": "room_id\nR1\n"}, author="responsable")
    before = store.current()

    check_compatibility(without_teacher(reference, "T001"), availability, calendar)

    assert store.current() == before
