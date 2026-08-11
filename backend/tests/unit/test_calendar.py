"""The calendar layering — FR-9's mechanism, below the HTTP surface.

`tests/acceptance/test_fr09.py` verifies the criterion through the screen. This
file holds the rules that make that possible and that a screen test cannot
show: that the loaded instance is never mutated, that a `None` is not an empty
list, and that the shift touches hours and nothing else.

⚠️ **The pristine-instance rule is the one to break deliberately if you doubt
it.** `api/deps.get_instance` is `lru_cache`d for the process, so an
`apply_calendar` that mutated its argument would corrupt every later request in
the same process — including runs that were never meant to see the edit. It
would also make `DELETE /api/calendar` a lie.
"""

from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from optiedt.domain.entities import Holiday
from optiedt.services.calendar import (
    MAX_SHIFT_MINUTES,
    SHORTENED_DAY_SHIFT,
    SHORTENED_DAY_START,
    CalendarError,
    CalendarOverrides,
    InMemoryCalendarStore,
    ShortenedDay,
    apply_calendar,
    build_overrides,
    shifted_hours,
)

A_HOLIDAY = Holiday(
    date=date(2026, 3, 20), label="Aid el-Fitr", lunar=True, approximate=True, blocking=True
)


@pytest.fixture
def instance(tiny_instance):
    """The hand-computable instance the criteria suites share, plus a holiday.

    Small enough that every assertion here is checkable by eye, and it carries
    slots at the reference calendar's own hours (08:30, 10:10, ...), so the
    shift below is a real arithmetic check rather than a tautology.

    ⚠️ **The holiday is added deliberately, and mutation testing is what
    demanded it.** `tiny_instance` carries none, so
    `test_a_stated_empty_holiday_list_withdraws_them` was comparing `()` to
    `()`: collapsing "stated empty" into "never stated" left it green. A test
    for a withdrawal needs something to withdraw.
    """
    return dataclasses.replace(tiny_instance, holidays=(A_HOLIDAY,))


@pytest.fixture
def store() -> InMemoryCalendarStore:
    return InMemoryCalendarStore()


def test_an_empty_calendar_returns_the_instance_unchanged(instance, store) -> None:
    """Identity, not a copy — `apply_calendar` short-circuits on `is_empty`.

    Rebuilding an identical instance on every run would be waste that hides
    itself, and `is` is what proves it did not happen.
    """
    assert apply_calendar(instance, store) is instance


def test_a_closure_reaches_the_instance_the_run_is_assembled_from(instance, store) -> None:
    store.save(CalendarOverrides(slot_open=((1, False),)), author="administrateur")

    applied = apply_calendar(instance, store)

    assert {s.index for s in applied.slots if not s.is_open} == {1}


def test_the_loaded_instance_is_never_mutated(instance, store) -> None:
    """⚠️ The rule the whole layering rests on.

    `get_instance()` is cached for the process. An `apply_calendar` that edited
    its argument would close a half-day for every later request in that
    process, and `DELETE /api/calendar` would restore nothing.

    ⚠️ **The snapshot is a COPY of the dict, and mutation testing is what
    demanded it.** This first read `before = dataclasses.replace(instance)`,
    which builds a new `Instance` around **the same `calendar_config` object** —
    so a function that mutated the dict in place changed both sides and the
    comparison held. It was comparing a dict to itself.
    """
    before_slots = instance.slots
    before_holidays = instance.holidays
    before_config = dict(instance.calendar_config)
    store.save(
        CalendarOverrides(
            slot_open=((1, False),),
            holidays=(),
            shortened_day=ShortenedDay(date(2026, 2, 18), date(2026, 3, 19), 60),
        ),
        author="administrateur",
    )

    apply_calendar(instance, store)

    assert instance.slots == before_slots
    assert instance.holidays == before_holidays
    assert instance.calendar_config == before_config


def test_a_slot_not_stated_keeps_what_the_instance_says(instance, store) -> None:
    """A partial statement is a partial statement.

    Closing Wednesday afternoon must not reopen a Saturday the institution's
    own files closed — which is what a store of the whole grid would do if the
    screen forgot a cell.
    """
    closed_by_the_instance = {s.index for s in instance.slots if not s.is_open}
    store.save(CalendarOverrides(slot_open=((1, False),)), author="a")

    applied = apply_calendar(instance, store)

    assert closed_by_the_instance <= {s.index for s in applied.slots if not s.is_open}


def test_an_unstated_holiday_list_leaves_the_instances_own(instance, store) -> None:
    store.save(CalendarOverrides(slot_open=((1, False),)), author="a")

    assert apply_calendar(instance, store).holidays == instance.holidays


def test_a_stated_empty_holiday_list_withdraws_them(instance, store) -> None:
    """⚠️ `None` is "nobody has said"; `()` is "there are none".

    Collapsing them would make the second impossible to state, exactly as an
    availability store without its marker row cannot tell "free all week" from
    "never asked".
    """
    assert instance.holidays == (A_HOLIDAY,), "there must be something to withdraw"

    store.save(CalendarOverrides(holidays=()), author="a")

    assert apply_calendar(instance, store).holidays == ()


def test_the_shortened_day_writes_the_three_configuration_keys(instance, store) -> None:
    store.save(
        CalendarOverrides(shortened_day=ShortenedDay(date(2026, 2, 18), date(2026, 3, 19), 60)),
        author="a",
    )

    config = apply_calendar(instance, store).calendar_config

    assert config[SHORTENED_DAY_START] == "2026-02-18"
    assert config[SHORTENED_DAY_SHIFT] == "60"


def test_the_shortened_day_moves_no_slot(instance, store) -> None:
    """⚠️ **ADR-003's guarantee, and the bug it exists to prevent.**

    The slot index does not change, so no variable and no constraint is
    affected. A shift that renumbered or closed a slot would be a calendar rule
    reaching into the model.
    """
    store.save(
        CalendarOverrides(shortened_day=ShortenedDay(date(2026, 2, 18), date(2026, 3, 19), 90)),
        author="a",
    )

    applied = apply_calendar(instance, store)

    assert applied.slots == instance.slots


def test_shifted_hours_are_computed_where_they_are_shown(instance, store) -> None:
    """The window's only effect: displayed hours.

    Computed on demand rather than written onto `Slot`, which would make every
    screen and every export read shifted hours all year round.
    """
    store.save(
        CalendarOverrides(shortened_day=ShortenedDay(date(2026, 2, 18), date(2026, 3, 19), 60)),
        author="a",
    )
    applied = apply_calendar(instance, store)

    rows = dict((index, (start, end)) for index, start, end in shifted_hours(applied))

    assert rows[0] == ("09:30", "11:00"), "08:30-10:00 moved by an hour"


def test_no_window_means_nothing_to_show(instance) -> None:
    """An empty tuple reads as "nothing configured" rather than as the same
    hours printed twice."""
    assert shifted_hours(instance) == ()


def test_a_slot_the_instance_does_not_have_is_refused(instance) -> None:
    with pytest.raises(CalendarError, match="9999"):
        build_overrides(instance, {9999: False}, holidays=None, shortened_day=None)


def test_a_window_that_ends_before_it_starts_is_refused(instance) -> None:
    with pytest.raises(CalendarError, match="ends before"):
        build_overrides(
            instance,
            {},
            holidays=None,
            shortened_day=ShortenedDay(date(2026, 3, 19), date(2026, 2, 18), 60),
        )


def test_an_absurd_shift_is_refused(instance) -> None:
    """Bounded because the value is displayed as an hour: a ten-hour shift is a
    data-entry error, not a shortened day."""
    with pytest.raises(CalendarError):
        build_overrides(
            instance,
            {},
            holidays=None,
            shortened_day=ShortenedDay(date(2026, 2, 18), date(2026, 3, 19), MAX_SHIFT_MINUTES + 1),
        )


def test_a_holiday_without_a_label_is_refused(instance) -> None:
    """A date nobody can name is a row that will be deleted by whoever inherits
    the calendar, because they cannot tell what it was for."""
    with pytest.raises(CalendarError, match="label"):
        build_overrides(
            instance,
            {},
            holidays=(
                Holiday(
                    date=date(2026, 3, 20),
                    label="  ",
                    lunar=False,
                    approximate=False,
                    blocking=True,
                ),
            ),
            shortened_day=None,
        )


def test_a_calendar_that_leaves_no_open_slot_is_accepted_not_refused(instance) -> None:
    """⚠️ **Deliberate, and the one rule here most likely to be "fixed".**

    Refusing would put a feasibility judgement in the calendar layer, where the
    solver's job would then be done twice and differently. The honest response
    to a calendar with no room for a timetable is FR-12's pre-analysis naming
    the shortfall on the next run — which is what
    `test_the_pre_analysis_measures_the_week_the_administrator_left` verifies.
    """
    every_slot_closed = {s.index: False for s in instance.slots}

    overrides = build_overrides(instance, every_slot_closed, holidays=None, shortened_day=None)

    assert all(not is_open for _, is_open in overrides.slot_open)


def test_two_identical_calendars_produce_identical_records(instance) -> None:
    """Reproducibility starts at the inputs, not at the seed — the same reason
    `build_declaration` sorts a teacher's grid."""
    first = build_overrides(instance, {1: False, 0: True}, holidays=None, shortened_day=None)
    second = build_overrides(instance, {0: True, 1: False}, holidays=None, shortened_day=None)

    assert first == second
