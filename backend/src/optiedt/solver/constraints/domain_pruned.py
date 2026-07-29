"""H4, H5, H6, H8, H9, H10 — domain restrictions, registered but inert here.

Each of these narrows a variable's domain at construction time (see
solver/variables.py), which is the only way CP-SAT domain restriction can
work: a variable's domain is fixed the moment it is created, so there is
nothing left to "apply" once the model exists. apply() is a documented
no-op for every class below, not an oversight.

They are still registered as ConstraintBuilder instances, one per code, so
the catalogue stays traceable (every H-code maps to something in the
codebase) and so carries_assumption_literal has a real, checkable answer
for all six: False, because none of them is a posted constraint object -
there is nothing for an assumption literal to attach to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ortools.sat.python import cp_model

    from optiedt.domain.entities import ConstraintCode
    from optiedt.domain.instance import Instance
    from optiedt.solver.variables import Variables


@dataclass(frozen=True, slots=True)
class H4:
    """Session placed in a room of the required type. Enforced by
    candidate_rooms only ever including rooms of session.required_room_type
    (solver/variables.py, _candidate_rooms)."""

    @property
    def code(self) -> ConstraintCode:
        return "H4"

    @property
    def carries_assumption_literal(self) -> bool:
        return False

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        return None


@dataclass(frozen=True, slots=True)
class H5:
    """Room capacity covers the group size. Enforced by candidate_rooms
    only including rooms whose capacity is sufficient (solver/variables.py,
    _candidate_rooms)."""

    @property
    def code(self) -> ConstraintCode:
        return "H5"

    @property
    def carries_assumption_literal(self) -> bool:
        return False

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        return None


@dataclass(frozen=True, slots=True)
class H6:
    """Teacher-declared unavailability respected. Enforced by excluding
    every unavailable slot from start[s]'s domain before it exists
    (solver/variables.py, _valid_starts)."""

    @property
    def code(self) -> ConstraintCode:
        return "H6"

    @property
    def carries_assumption_literal(self) -> bool:
        return False

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        return None


@dataclass(frozen=True, slots=True)
class H8:
    """A multi-period session stays within one day. Enforced by excluding
    any start value whose consumed periods span two day_index values
    (solver/variables.py, _valid_starts)."""

    @property
    def code(self) -> ConstraintCode:
        return "H8"

    @property
    def carries_assumption_literal(self) -> bool:
        return False

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        return None


@dataclass(frozen=True, slots=True)
class H9:
    """No session on a closed slot or a holiday. Enforced by excluding
    every slot with is_open == False from every session's start domain
    (solver/variables.py, _valid_starts). Holidays act through the same
    mechanism: a holiday closes slots by setting is_open = 0 on them
    (ADR-003), it is not a separate check here."""

    @property
    def code(self) -> ConstraintCode:
        return "H9"

    @property
    def carries_assumption_literal(self) -> bool:
        return False

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        return None


@dataclass(frozen=True, slots=True)
class H10:
    """A locked session keeps the slot and room given to it.

    Not yet enforceable: SolverInput.locked_sessions carries only session
    ids, with no field for the (slot, room) a locked session should keep.
    build_variables() raises rather than silently ignore a non-empty set
    of locked session ids - see its docstring and docs/open-questions.md.
    The reference instance has no locked sessions, so this path is dormant
    until recommendation-driven regeneration (Phase 3) has a prior
    candidate to lock a placement FROM.
    """

    @property
    def code(self) -> ConstraintCode:
        return "H10"

    @property
    def carries_assumption_literal(self) -> bool:
        return False

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        return None
