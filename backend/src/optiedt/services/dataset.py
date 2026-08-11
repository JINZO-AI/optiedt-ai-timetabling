"""FR-1 — the department dataset a run is assembled from, and its replacement.

    SRS §3.2, Table 4. FR-1. Data management:
      Input       Files or forms validated by the server
      Processing  Verification of the types and of the references, then
                  recording
      Output      Entities recorded and report of the rejected lines

`instance/validation.py` is the verification. This module is the **recording**,
and the one rule that governs when a recording may happen at all.

---

## The A7 project decision

> **Project decision — determined from repository evidence and engineering
> research because supervisor clarification was unavailable.**
>
> A dataset replacement must be rejected if it would leave existing persisted
> FR-2 declarations or FR-9 calendar overrides invalid or orphaned. Existing
> overlay data must not be silently deleted. The existing dataset remains active
> when compatibility validation fails. A successful replacement must preserve
> referential integrity and be committed atomically.

⚠️ **This is not a new policy — it is the missing half of one the application
already enforces.** Neither overlay can be *created* pointing at something
absent: `api/routers/availability.py` answers 404 for an unknown teacher and 422
for an unknown slot, and `services/calendar.build_overrides` raises
`CalendarError` for an unknown slot index. A base change is the only way an
orphan can come into existence, so refusing one is the same rule seen from the
other side. It is also PostgreSQL's own default referential action — `NO ACTION`
refuses; `CASCADE` has to be asked for.

⚠️ **Nothing here writes to an overlay store.** That is a design constraint as
much as a policy: each store owns its own session, so there is **no transaction
spanning two of them**, and an import that cleared declarations could not be
atomic with the write that replaced the dataset. Refusing keeps the write set to
one row of one store, which is exactly what makes atomicity true rather than
claimed.

## Why two compatibility checks and not one

Compatibility is judged on the **complete effective dataset** — the candidate
with the stored calendar and the stored declarations applied — because that is
where an orphan actually lands: `apply_declarations` appends the store's rows
verbatim, so a declaration naming a departed teacher survives into
`Instance.availability` and is then silently ignored by
`solver/variables.py::unavailable_by_teacher`, which reads `.get(...)`. Nothing
raises. The declaration simply stops meaning anything.

**But the effective dataset cannot see an orphaned calendar**, and that is the
second check's whole reason for existing. `apply_calendar` iterates the *new*
instance's slots and consults the stated map only for slots it finds, so a
`slot_open` entry whose index the new dataset does not have is dropped without
trace. Checked against the effective instance alone, the administrator's
statement would be silently deleted — precisely what the decision above forbids.
So the calendar's stated indices are compared against the candidate directly.

⚠️ **An inert declaration marker must not block an import.** The SQL store keeps
a `-1` marker row so that "asked and answered nothing" stays distinct from
"never asked" (`db/repositories.py`). A teacher whose grid was emptied is still
named by `declared_teachers()` while contributing **no** availability rows.
Judging compatibility on the effective rows rather than on that set is what
keeps the one escape route open: there is no endpoint that forgets a
declaration, so a store-level test would make a departed teacher an
unresolvable block on every future import.

## Known limitations, recorded rather than absorbed

- **A slot whose index survives but whose meaning changes is undetectable.** If
  the new dataset numbers slot 7 as Tuesday period 2 where the old one had
  Monday period 3, every check here passes and the administrator's closure now
  closes a different half-day. Detecting it needs a slot identity the model does
  not have, and inventing one is a larger change than FR-1 asks for.
- **No protection against a concurrent write.** A declaration saved between the
  compatibility check and the replacement is not seen by the check. The
  repository has no locking of any kind and the specification asks for none;
  building one for this path alone would be new architecture.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from optiedt.domain.instance import Instance
from optiedt.services.availability import AvailabilityStore, apply_declarations
from optiedt.services.calendar import CalendarStore, apply_calendar

DECLARED_MARKER_SLOT = -1
"""The slot index `db/repositories.py` reserves for "asked and answered nothing".

Duplicated as a constant rather than imported: `services` may not import
`optiedt.db` in the direction that would make this a shared symbol, and a
magic -1 appearing in a compatibility check with no name would be unreadable.
`tests/unit/test_dataset.py` pins the two together.
"""


@dataclass(frozen=True, slots=True)
class StoredDataset:
    """A department dataset as it was supplied, with who recorded it and when.

    ⚠️ **The FILE TEXTS are stored, not a serialisation of the entities.** One
    parse path then serves both the import and every later read, so a stored
    dataset cannot drift from what the validator accepted, and the file schema
    stays what `docs/data-and-instance.md` already calls it — the contract. A
    second JSON shape for the same entities would be a second thing to keep in
    step with the domain.
    """

    files: Mapping[str, str]
    revision: str
    imported_at: datetime
    imported_by: str


class DatasetStore(Protocol):
    """The imported department dataset, or the absence of one.

    There is one dataset per installation — CdC §3.2 puts *"simultaneous
    treatment of several faculties"* outside the scope — so this store holds one
    document rather than a collection, exactly as `CalendarStore` does.
    """

    def revision(self) -> str | None:
        """A token that changes on every save, or None when nothing is imported.

        ⚠️ **Separate from `current()` so the hot path stays cheap and stays
        correct.** `api/deps.py` reads this on every request and re-reads the
        document only when it has changed, which is what makes a stale cached
        instance impossible rather than unlikely.
        """
        ...

    def current(self) -> StoredDataset | None: ...

    def save(self, files: Mapping[str, str], author: str) -> StoredDataset:
        """Replace the dataset wholesale, in one transaction."""
        ...

    def reset(self) -> None:
        """Withdraw the import; the reference dataset governs again."""
        ...


class InMemoryDatasetStore:
    """One document, held in a field. For tests and for `persistence = memory`."""

    def __init__(self) -> None:
        self._stored: StoredDataset | None = None

    def revision(self) -> str | None:
        return None if self._stored is None else self._stored.revision

    def current(self) -> StoredDataset | None:
        return self._stored

    def save(self, files: Mapping[str, str], author: str) -> StoredDataset:
        self._stored = StoredDataset(
            files=dict(files),
            revision=uuid.uuid4().hex,
            imported_at=datetime.now(UTC),
            imported_by=author,
        )
        return self._stored

    def reset(self) -> None:
        self._stored = None


@dataclass(frozen=True, slots=True)
class Incompatibility:
    """One reason a replacement would orphan something already stored.

    Kept apart from `RejectedLine`: a rejected line is fixed in the file, an
    incompatibility is fixed by a person withdrawing a declaration or a closure.
    Reporting them in one list would tell somebody to edit a file that is
    correct.
    """

    overlay: str
    """`"availability"` (FR-2) or `"calendar"` (FR-9)."""

    subject: str
    """The teacher, or the slot index, the stored statement is about."""

    reason: str

    remedy: str
    """What a person can actually do about it, named in the response."""


AVAILABILITY_OVERLAY = "availability"
CALENDAR_OVERLAY = "calendar"


def check_compatibility(
    candidate: Instance,
    availability: AvailabilityStore,
    calendar: CalendarStore,
) -> tuple[Incompatibility, ...]:
    """Would replacing the base with `candidate` orphan anything already stored?

    Returns every reason, not the first — the same principle as the rejected
    lines, and for the same reason: a person clearing declarations one import at
    a time is being made to do the application's work.
    """
    return (
        *_declarations_that_would_be_orphaned(candidate, availability, calendar),
        *_closures_that_would_be_orphaned(candidate, calendar),
    )


def _declarations_that_would_be_orphaned(
    candidate: Instance,
    availability: AvailabilityStore,
    calendar: CalendarStore,
) -> tuple[Incompatibility, ...]:
    """FR-2, judged on the EFFECTIVE dataset — see the module docstring.

    The candidate is layered exactly as a run would layer it, and the rows that
    come out are checked against what the candidate declares. A teacher who
    declared nothing unavailable contributes no rows and so cannot appear here,
    which is refinement 6 obtained from the arithmetic rather than from a
    special case.
    """
    effective = apply_declarations(apply_calendar(candidate, calendar), availability)

    teachers = {t.id for t in candidate.teachers}
    slots = {s.index for s in candidate.slots}

    # ⚠️ **Every effective row is checked, not only the stored ones**, and the
    # filter that would restrict this to `declared_teachers()` was removed after
    # mutation testing showed it could not fire: a candidate's own availability
    # rows have already had their references verified by
    # `instance/validation.py`, so they cannot fail here. Keeping a guard that
    # can never trigger would imply it protects something.
    found: dict[tuple[str, str], Incompatibility] = {}
    for row in effective.availability:
        if row.teacher not in teachers:
            found.setdefault(
                (AVAILABILITY_OVERLAY, row.teacher),
                Incompatibility(
                    overlay=AVAILABILITY_OVERLAY,
                    subject=row.teacher,
                    reason=(
                        f"teacher {row.teacher} has declared availability, and the supplied "
                        f"dataset does not declare that teacher"
                    ),
                    remedy=(
                        f"keep {row.teacher} in the dataset, or clear that declaration first "
                        f"(PUT /api/teachers/{row.teacher}/availability with no cells)"
                    ),
                ),
            )
        elif row.slot not in slots and row.slot != DECLARED_MARKER_SLOT:
            found.setdefault(
                (AVAILABILITY_OVERLAY, f"{row.teacher}:{row.slot}"),
                Incompatibility(
                    overlay=AVAILABILITY_OVERLAY,
                    subject=f"{row.teacher}:{row.slot}",
                    reason=(
                        f"teacher {row.teacher} has declared slot {row.slot}, and the supplied "
                        f"dataset has no such slot"
                    ),
                    remedy=(
                        f"keep slot {row.slot} in the dataset, or clear that declaration first "
                        f"(PUT /api/teachers/{row.teacher}/availability with no cells)"
                    ),
                ),
            )
    return tuple(found.values())


def _closures_that_would_be_orphaned(
    candidate: Instance, calendar: CalendarStore
) -> tuple[Incompatibility, ...]:
    """FR-9, judged against the CANDIDATE directly — see the module docstring.

    ⚠️ **This cannot be folded into the check above.** `apply_calendar` consults
    the stated map only for slots the candidate has, so an orphaned closure
    leaves no trace in the effective dataset. Reading it there would report
    "compatible" while deleting the administrator's statement.
    """
    stated = calendar.overrides().slot_open
    if not stated:
        return ()

    slots = {s.index for s in candidate.slots}
    return tuple(
        Incompatibility(
            overlay=CALENDAR_OVERLAY,
            subject=str(index),
            reason=(
                f"the calendar states slot {index} as "
                f"{'open' if is_open else 'closed'}, and the supplied dataset has no such slot"
            ),
            remedy=(
                f"keep slot {index} in the dataset, or ask an administrator to withdraw the "
                f"calendar first (DELETE /api/calendar)"
            ),
        )
        for index, is_open in stated
        if index not in slots
    )
