"""Teacher availability declarations — FR-2's write side.

The instance loaded from `data/instance/` is immutable and is the *starting*
state: its 157 rows are all `SYNTHETIC`, generated so the instance is solvable
before any teacher has connected (docs/domain-model.md). When a teacher fills
in the grid, their declaration replaces the generated one **for that teacher
only**, and is marked `TEACHER` so the two never become indistinguishable.

⚠️ **Storage is in memory and does not survive a restart.** That is Phase 4's
documented position — persistence is Phase 5, and `docs/status.md` records that
PostgreSQL is only needed once runs, candidates and publication must survive a
restart. The Protocol below is the seam: Phase 5 supplies a database-backed
implementation and no router changes.

This module writes no placement and reads no score. Replacing a teacher's
availability changes an *input* to the next run; it never touches a candidate
that already exists, which invariant 6 forbids.
"""

from __future__ import annotations

import dataclasses
from typing import Protocol

from optiedt.domain.entities import Availability, SlotIndex, TeacherId
from optiedt.domain.enums import AvailabilityState, DeclarationSource
from optiedt.domain.instance import Instance


class AvailabilityStore(Protocol):
    """Declarations made through the application, by teacher.

    A teacher absent from the store has not declared anything, and the
    instance's generated rows stand. That is deliberately distinct from a
    teacher who declared *nothing unavailable*: the first has not been asked,
    the second has answered "I am free all week", and overwriting the
    distinction would let a generated row masquerade as a real answer.
    """

    def declarations(self, teacher: TeacherId) -> tuple[Availability, ...] | None:
        """Rows this teacher declared, or None if they never have."""
        ...

    def declare(self, teacher: TeacherId, rows: tuple[Availability, ...]) -> None:
        """Replace this teacher's declaration wholesale."""
        ...

    def declared_teachers(self) -> frozenset[TeacherId]: ...


class InMemoryAvailabilityStore:
    """Dict-backed store. Phase 4 only — see the module docstring."""

    def __init__(self) -> None:
        self._by_teacher: dict[TeacherId, tuple[Availability, ...]] = {}

    def declarations(self, teacher: TeacherId) -> tuple[Availability, ...] | None:
        return self._by_teacher.get(teacher)

    def declare(self, teacher: TeacherId, rows: tuple[Availability, ...]) -> None:
        self._by_teacher[teacher] = rows

    def declared_teachers(self) -> frozenset[TeacherId]:
        return frozenset(self._by_teacher)


def build_declaration(
    teacher: TeacherId,
    semester: int,
    cells: dict[SlotIndex, AvailabilityState],
) -> tuple[Availability, ...]:
    """Turn the grid's marked cells into rows, sorted by slot.

    Only non-AVAILABLE cells are stored, matching the instance's own
    convention: `teacher_availability.csv` records unavailability, and a row
    per free slot would be 28 rows per teacher saying nothing.

    Sorted so that two identical declarations produce identical tuples —
    reproducibility starts at the inputs, not at the seed.
    """
    return tuple(
        Availability(
            teacher=teacher,
            slot=slot,
            state=state,
            semester=semester,
            source=DeclarationSource.TEACHER,
        )
        for slot, state in sorted(cells.items())
        if state is not AvailabilityState.AVAILABLE
    )


def effective_availability(
    instance: Instance, store: AvailabilityStore
) -> tuple[Availability, ...]:
    """The instance's rows, with each declaring teacher's rows substituted.

    Substituted wholesale rather than merged: a teacher's grid is the complete
    statement of their week, so a slot they left free must clear a generated
    row that said otherwise. Merging would make a generated declaration
    impossible to withdraw.
    """
    declared = store.declared_teachers()
    kept = tuple(a for a in instance.availability if a.teacher not in declared)
    added: list[Availability] = []
    for teacher in sorted(declared):
        rows = store.declarations(teacher)
        if rows:
            added.extend(rows)
    return kept + tuple(added)


def apply_declarations(instance: Instance, store: AvailabilityStore) -> Instance:
    """The instance a run should actually solve, given what teachers declared.

    Returns a new Instance; the loaded one is never mutated, so two runs cannot
    disagree about what they were given.
    """
    return dataclasses.replace(instance, availability=effective_availability(instance, store))
