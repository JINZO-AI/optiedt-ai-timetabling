"""The calendar an administrator edits — FR-9's write side.

SRS Table 2 gives the administrator *"management of the accounts and of the
calendar"*, and ADR-003 says what a calendar edit is allowed to be: **exactly
two effects**, closing slots (`Slot.is_open = 0`, after which H9 removes them
from every session's domain) and shifting displayed hours. Nothing here posts a
constraint, and adding a CP-SAT rule for a closed Saturday would be a bug
rather than a feature (invariant 7).

⚠️ **The loaded instance stays pristine, exactly as FR-2's declarations do.**
`api/deps.py::get_instance` reads the 13 CSVs once and caches them; this module
layers the administrator's edits *over* that copy at the moment a run is
assembled. The reason is the same one `services/availability.py` gives: an edit
that is layered can be withdrawn, and an edit written into the loaded instance
cannot. `DELETE /api/calendar` is that withdrawal, and it works because the
stored document is the only thing that ever changed.

**Why one document rather than three tables.** The overrides below are one
short record, read whole at run assembly and never queried into — the same
shape `db/models.py` already keeps as JSON for `duplicates_removed` and a run's
`overrides`. Three tables would add three joins to answer a question nobody
asks.

⚠️ **A `None` field is not an empty one.** `holidays = None` means the
administrator has never stated a holiday list, so the instance's own stands;
`holidays = ()` means they stated that there are none. Collapsing the two would
make "there are no holidays this year" impossible to say — the same distinction
`AvailabilityStore` protects with its marker row, obtained here for free
because a document can carry a null field and a set of rows cannot.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

from optiedt.domain.entities import Holiday, SlotIndex
from optiedt.domain.instance import Instance

SHORTENED_DAY_START = "ramadan_start"
SHORTENED_DAY_END = "ramadan_end"
SHORTENED_DAY_SHIFT = "ramadan_shift_minutes"
"""The three `calendar_config` keys the shortened-day window writes.

⚠️ **Reused from `calendar_config.csv` rather than invented.** The instance
already carries these three keys and `docs/data-and-instance.md` documents
them; a second pair of names for one window would be a second answer to "when
does the shortened day apply?". ADR-003 speaks of a shortened-day window "in
particular Ramadan" — the mechanism is general, the key names are the ones the
data uses.
"""

MAX_SHIFT_MINUTES = 240
"""A shift beyond four hours is a data-entry error, not a shortened day.

Bounded because the value is displayed as an hour: `08:30 + 600 minutes` is not
a teaching day, and refusing it at the edge is cheaper than explaining a grid
that starts at half past six in the evening.
"""


@dataclass(frozen=True, slots=True)
class ShortenedDay:
    """A window during which displayed hours shift, and by how much.

    ⚠️ **Displayed hours only (ADR-003).** The slot index does not change, so no
    variable and no constraint is affected — which is exactly why this is
    configuration and not a thirteenth hard rule.
    """

    start: date
    end: date
    shift_minutes: int


@dataclass(frozen=True, slots=True)
class CalendarOverrides:
    """What the administrator has stated about the calendar, or nothing.

    `slot_open` carries only the slots they actually set. A slot absent from it
    keeps whatever `slots.csv` says, which is what makes a partial edit
    meaningful and a withdrawal complete.
    """

    slot_open: tuple[tuple[SlotIndex, bool], ...] = ()
    holidays: tuple[Holiday, ...] | None = None
    shortened_day: ShortenedDay | None = None

    @property
    def is_empty(self) -> bool:
        """True when nothing has been stated and the loaded calendar governs."""
        return not self.slot_open and self.holidays is None and self.shortened_day is None


EMPTY = CalendarOverrides()


@dataclass(frozen=True, slots=True)
class CalendarEdit:
    """Who last stated the calendar, and when.

    Kept apart from `CalendarOverrides` because a run needs the calendar and
    never needs its author: mixing them would put a username inside the value
    the solver's instance is assembled from.
    """

    at: datetime
    by: str


class CalendarStore(Protocol):
    """The administrator's calendar, or the absence of one.

    There is exactly one calendar per installation, so this store holds one
    document rather than a collection. `save` replaces it wholesale — a
    calendar is one statement about a year, the same reason FR-2's `PUT`
    replaces a teacher's grid instead of patching cells.
    """

    def overrides(self) -> CalendarOverrides:
        """What was last saved, or `EMPTY` if nothing ever was."""
        ...

    def save(self, overrides: CalendarOverrides, author: str) -> None: ...

    def last_edit(self) -> CalendarEdit | None:
        """Who saved it and when, or None if nobody ever has.

        ⚠️ Recorded because closing a half-day changes what **every** future run
        can produce — the same reason a publication carries its author.
        """
        ...

    def reset(self) -> None:
        """Withdraw every edit; the loaded instance's calendar governs again."""
        ...


class InMemoryCalendarStore:
    """One document, held in a field. For tests and for `persistence = memory`."""

    def __init__(self) -> None:
        self._overrides = EMPTY
        self._edit: CalendarEdit | None = None

    def overrides(self) -> CalendarOverrides:
        return self._overrides

    def save(self, overrides: CalendarOverrides, author: str) -> None:
        self._overrides = overrides
        self._edit = CalendarEdit(at=datetime.now(UTC), by=author)

    def last_edit(self) -> CalendarEdit | None:
        return self._edit

    def reset(self) -> None:
        self._overrides = EMPTY
        self._edit = None


def apply_calendar(instance: Instance, store: CalendarStore) -> Instance:
    """The instance as the administrator's calendar leaves it.

    Returns a new `Instance`; the loaded one is never mutated, so two runs
    cannot disagree about what they were given.

    ⚠️ **A slot's INDEX is never touched**, only its `is_open` flag and, for the
    shortened day, three configuration values. That is ADR-003's whole
    guarantee: closing a half-day removes moments, it never renumbers them, and
    a shifted hour moves what is printed rather than what is solved.
    """
    overrides = store.overrides()
    if overrides.is_empty:
        return instance

    stated = dict(overrides.slot_open)
    slots = tuple(
        dataclasses.replace(slot, is_open=stated[slot.index]) if slot.index in stated else slot
        for slot in instance.slots
    )
    holidays = instance.holidays if overrides.holidays is None else overrides.holidays
    return dataclasses.replace(
        instance,
        slots=slots,
        holidays=holidays,
        calendar_config=_with_shortened_day(instance.calendar_config, overrides.shortened_day),
    )


def _with_shortened_day(config: dict[str, str], shortened: ShortenedDay | None) -> dict[str, str]:
    """The configuration with the window written into its three keys.

    Copied rather than mutated: `Instance` is frozen and its `calendar_config`
    is a plain dict, so editing in place would reach back into the cached
    pristine instance every later request reads.
    """
    if shortened is None:
        return dict(config)
    return {
        **config,
        SHORTENED_DAY_START: shortened.start.isoformat(),
        SHORTENED_DAY_END: shortened.end.isoformat(),
        SHORTENED_DAY_SHIFT: str(shortened.shift_minutes),
    }


class CalendarError(ValueError):
    """A calendar that cannot be applied. Carries the reason for the caller.

    A distinct type so the router can answer 422 with the message and nothing
    else has to guess whether a `ValueError` from here meant "bad input" or
    "bug".
    """


def build_overrides(
    instance: Instance,
    slot_open: dict[SlotIndex, bool],
    holidays: tuple[Holiday, ...] | None,
    shortened_day: ShortenedDay | None,
) -> CalendarOverrides:
    """Validate an administrator's calendar and put it in storable form.

    ⚠️ **It does not refuse a calendar that makes the instance infeasible**, and
    that is deliberate. On this instance any half-day closure takes `Lab_Info`
    to exactly 100.0 % of its two-period windows (`acceptance/test_fr09`), so a
    second one leaves no packing at all — and the honest answer to that is
    FR-12's pre-analysis reporting the shortfall on the next run, not a save
    button that refuses a decision the institution has taken. Refusing would
    also mean this module deciding feasibility, which is the solver's job.

    Sorted so that two identical calendars produce identical records —
    reproducibility starts at the inputs.
    """
    known = {s.index for s in instance.slots}
    unknown = sorted(set(slot_open) - known)
    if unknown:
        raise CalendarError(f"Unknown slot indices: {unknown}")

    if shortened_day is not None:
        if shortened_day.end < shortened_day.start:
            raise CalendarError(
                "The shortened-day window ends before it starts: "
                f"{shortened_day.start.isoformat()} → {shortened_day.end.isoformat()}"
            )
        if not 0 <= shortened_day.shift_minutes <= MAX_SHIFT_MINUTES:
            raise CalendarError(
                f"A shift of {shortened_day.shift_minutes} minutes is outside "
                f"0..{MAX_SHIFT_MINUTES}"
            )

    if holidays is not None:
        blank = [h for h in holidays if not h.label.strip()]
        if blank:
            raise CalendarError("A holiday must carry a label")

    return CalendarOverrides(
        slot_open=tuple(sorted(slot_open.items())),
        holidays=None if holidays is None else tuple(sorted(holidays, key=_holiday_order)),
        shortened_day=shortened_day,
    )


def _holiday_order(holiday: Holiday) -> tuple[date, str]:
    return (holiday.date, holiday.label)


def shifted_hours(instance: Instance) -> tuple[tuple[SlotIndex, str, str], ...]:
    """Each slot's hours as they read during the shortened-day window.

    ⚠️ **This is a projection, not a second grid.** ADR-003 gives the window one
    effect — displayed and printed hours — so the shift is computed where it is
    shown rather than written onto `Slot`, which would make every screen and
    every export read shifted hours all year.

    Returns an empty tuple when no window is configured, which reads as
    "nothing to show" rather than as "the same hours twice".
    """
    raw = instance.calendar_config.get(SHORTENED_DAY_SHIFT, "").strip()
    if not raw:
        return ()
    try:
        shift = int(raw)
    except ValueError:
        return ()
    if shift == 0:
        return ()

    return tuple(
        (
            slot.index,
            _shift(slot.start_hour.hour, slot.start_hour.minute, shift),
            _shift(slot.end_hour.hour, slot.end_hour.minute, shift),
        )
        for slot in instance.slots
    )


def _shift(hour: int, minute: int, minutes: int) -> str:
    """ "HH:MM" moved by `minutes`, wrapped inside the day.

    Wrapped rather than clamped: a wrap is visibly wrong on screen, whereas a
    clamp silently reports 23:59 for a window nobody could teach in.
    """
    total = (hour * 60 + minute + minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"
