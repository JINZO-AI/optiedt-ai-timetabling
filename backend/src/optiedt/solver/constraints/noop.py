"""H2 and H11 — subsumed by a sibling constraint, not separately posted.

H2 ("a group has at most one session per slot") is a strict subset of what
H12 already forbids: H12's NoOverlap is built per promotion over every
session belonging to any group in that promotion's hierarchy, and a single
group is trivially part of its own hierarchy. Posting H2 again would add
a second, redundant NoOverlap over a subset of intervals H12 already
covers.

H11 ("aggregate demand does not exceed room capacity") falls out of H3
plus H7 as a mathematical consequence, not an extra rule: if every room of
a type has its own NoOverlap (H3) and every session picks exactly one
compatible room (H7), then at most as many sessions of that type can be
simultaneously active as there are rooms of that type - which is exactly
what H11 states. No Cumulative constraint is needed to get it.

Both are registered so the catalogue stays complete and so
carries_assumption_literal has an explicit, checkable answer: False in
both cases, because there is no separate posting for a literal to attach
to, and attaching one to H12's or H3's posting on their behalf would be
exactly the redundant-literal problem C-6 warns against - the solver
could name H2 or H11 in a conflict report for a rule the user cannot act
on independently of H12 or H3.

⚠️ The `literal` argument each apply() below accepts is therefore IGNORED.
A conflict that is "really" H2's is reported as H12, and one that is
"really" H11's as H3 - which is correct, not a loss: those are the rules
the user can actually change.
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
class H2:
    """Subsumed by H12 - see module docstring."""

    @property
    def code(self) -> ConstraintCode:
        return "H2"

    @property
    def carries_assumption_literal(self) -> bool:
        return False

    def apply(
        self,
        model: cp_model.CpModel,
        variables: Variables,
        instance: Instance,
        literal: cp_model.IntVar | None = None,
    ) -> None:
        return None


@dataclass(frozen=True, slots=True)
class H11:
    """Subsumed by H3 + H7 - see module docstring."""

    @property
    def code(self) -> ConstraintCode:
        return "H11"

    @property
    def carries_assumption_literal(self) -> bool:
        return False

    def apply(
        self,
        model: cp_model.CpModel,
        variables: Variables,
        instance: Instance,
        literal: cp_model.IntVar | None = None,
    ) -> None:
        return None
