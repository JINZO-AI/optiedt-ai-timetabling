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
there is nothing to withdraw.

⚠️ These six therefore cannot be relaxed, and that shapes the diagnosis
run: the domain is already narrowed by the time the model exists, so an
infeasibility caused by one of them is invisible to a search that withdraws
posted constraints, and comes back as an EMPTY conflict set. `Solver.diagnose`
says so in words (DiagnosisResult.detail) and points at the pre-analysis
report, which is where an unplaceable session or an over-declared
unavailability shows up.
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

    Enforced by domain pruning, like H4/H5/H6/H8/H9: build_variables()
    narrows a locked session's start domain to the single locked slot and
    its candidate room tuple to the single locked room. Nothing is posted,
    so there is nothing here to attach an assumption literal to (C-6) and
    the rule costs nothing during search.

    ⚠️ **Dormant until 2026-08-06.** SolverInput carried session ids with
    no target, so build_variables() RAISED on a non-empty lock set rather
    than ignore it. C-19 replaced that field with frozenset[Placement] and
    this rule now executes. The reference instance still has no locked
    sessions - what exercises H10 is regeneration from an accepted
    lock_session recommendation (FR-23).

    A lock INTERSECTS the other rules' pruning rather than replacing it, so
    it cannot place a session on a closed slot or in a room too small for
    its group; build_variables() raises naming the rule that refused.
    """

    @property
    def code(self) -> ConstraintCode:
        return "H10"

    @property
    def carries_assumption_literal(self) -> bool:
        return False

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        return None
