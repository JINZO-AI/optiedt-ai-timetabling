"""FR-9 — the administrator configures the calendar.

    Acceptance criterion (SRS §8.6 Table 35, transcribed in
    docs/testing-strategy.md §4):
    "Close a half-day in configuration → those slots disappear from every
    timetable, WITH NO CODE CHANGE."

⚠️ **This router writes configuration, never a constraint.** ADR-003 and
invariant 7 give the calendar exactly two effects — closing slots, which H9
already acts on, and shifting displayed hours — and adding a CP-SAT rule for a
closed Saturday would be a bug rather than a feature. Nothing here reaches the
solver; `acceptance/test_fr09.py` asserts the catalogue still holds exactly
H1-H12 after a closure.

⚠️ **The loaded instance is not edited.** The statement is stored and layered
over the pristine CSVs at run assembly (`services/calendar.apply_calendar`),
which is what `DELETE` can undo. The same shape FR-2's declarations use, and
for the same stated reason: an edit that is layered can be withdrawn.

⚠️ **A calendar that leaves no room for a timetable is SAVED, not refused.**
Closing a second half-day on this instance can make it infeasible — `Lab_Info`
reaches exactly 100.0 % of its two-period windows after the first — and the
answer to that is FR-12's pre-analysis reporting the shortfall on the next run.
A save button that overruled the institution would be deciding feasibility
outside the solver, which is invariant 2's spirit and stage 1's job.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from optiedt.api.deps import (
    AdministratorDep,
    CalendarStoreDep,
    InstanceDep,
    PristineInstanceDep,
)
from optiedt.api.schemas import CalendarIn, CalendarOut
from optiedt.services.calendar import CalendarError, apply_calendar, build_overrides, shifted_hours

router = APIRouter(tags=["calendar"])


@router.get(
    "/calendar",
    response_model=CalendarOut,
    summary="The calendar in force, and what the instance loaded",
)
def read_calendar(
    instance: InstanceDep,
    pristine: PristineInstanceDep,
    store: CalendarStoreDep,
    _user: AdministratorDep,
) -> CalendarOut:
    """⚠️ Administrator only — SRS Table 2 gives this surface to that actor.

    Every other role reads the *effect* through `GET /instance`, which serves
    the same closures; what is restricted here is stating them.
    """
    return CalendarOut.of(
        effective=instance,
        pristine=pristine,
        overrides=store.overrides(),
        edit=store.last_edit(),
        shifted=shifted_hours(instance),
    )


@router.put(
    "/calendar",
    response_model=CalendarOut,
    summary="State the calendar; takes effect on the next run",
)
def declare_calendar(
    pristine: PristineInstanceDep,
    store: CalendarStoreDep,
    user: AdministratorDep,
    payload: CalendarIn,
) -> CalendarOut:
    """Replace the stated calendar wholesale.

    Wholesale rather than per slot, for FR-2's reason: a calendar is one
    statement about a year, so a slot the administrator reopened must be able
    to clear a closure a previous save recorded. A patch endpoint would make a
    closure impossible to withdraw without a second, opposite call.

    ⚠️ Validated against the **pristine** slot indices. Validating against the
    effective instance would let a save that had already closed a slot make
    that slot's index unknown to the next save.
    """
    counts: dict[int, int] = {}
    for cell in payload.slots:
        counts[cell.slot] = counts.get(cell.slot, 0) + 1
    duplicated = sorted(index for index, n in counts.items() if n > 1)
    if duplicated:
        # Two entries stating different things about one slot is a client bug,
        # not a merge to resolve silently — `routers/availability` refuses the
        # same shape for the same reason.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Slot stated more than once: {duplicated}",
        )

    try:
        overrides = build_overrides(
            pristine,
            slot_open={cell.slot: cell.is_open for cell in payload.slots},
            holidays=(
                None if payload.holidays is None else tuple(h.to_domain() for h in payload.holidays)
            ),
            shortened_day=(
                None if payload.shortened_day is None else payload.shortened_day.to_domain()
            ),
        )
    except CalendarError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    store.save(overrides, author=user.username)
    effective = apply_calendar(pristine, store)
    return CalendarOut.of(
        effective=effective,
        pristine=pristine,
        overrides=overrides,
        edit=store.last_edit(),
        shifted=shifted_hours(effective),
    )


@router.delete(
    "/calendar",
    response_model=CalendarOut,
    summary="Withdraw every calendar edit; the loaded calendar governs again",
)
def reset_calendar(
    pristine: PristineInstanceDep,
    store: CalendarStoreDep,
    _user: AdministratorDep,
) -> CalendarOut:
    """The withdrawal the layering exists for.

    ⚠️ It restores `slots.csv`, `holidays.csv` and `calendar_config.csv` as
    loaded — not "the previous save". There is one statement, and removing it
    leaves the institution's own files in force, which is the only state this
    application can restore without keeping a history nobody asked for.
    """
    store.reset()
    return CalendarOut.of(
        effective=pristine,
        pristine=pristine,
        overrides=store.overrides(),
        edit=store.last_edit(),
        shifted=shifted_hours(pristine),
    )
