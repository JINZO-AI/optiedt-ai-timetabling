"""Stage 1 of every run: five arithmetic checks, no solver involved.

Their purpose is to distinguish two situations a solver reports identically:
an instance that GENUINELY has no solution, and an ERROR IN THE MODEL.

This is the primary debugging instrument of the project, not a nicety. The
reference instance sits at 95% computer-laboratory occupancy; at that
saturation a modelling regression surfaces as INFEASIBLE rather than as a slow
solve, and without these checks you cannot tell which you are looking at.
Run them first, always.

May NOT import the solver — enforced by .importlinter. If it could call the
solver it would stop being the instrument described above.

Expected results on the reference instance are in docs/data-and-instance.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CheckResult:
    """The outcome of one verification.

    A failing check must name the RESOURCE CONCERNED and the QUANTITY MISSING —
    not return a boolean. That named detail is the content FR-12 requires of the
    structural-risk report.
    """

    name: str
    passed: bool
    resource: str | None = None
    missing_quantity: float | None = None
    detail: str = ""


class Check(Protocol):
    """One of the five verifications."""

    @property
    def name(self) -> str: ...

    def run(self, instance: object) -> CheckResult: ...


# The five checks, in the order they are reported. Expected results on the
# reference instance, all passing:
#
#   ROOM_SUITABILITY    0 sessions without a suitable room
#   SLOT_COVERAGE       lecture theatres 57% · classrooms 29%
#                       · computer laboratories 95% ← the number to watch
#                       · science laboratories 86%
#   TEACHER_LOAD        0 teachers above the limit; heaviest 12 periods (18 h)
#   TEACHER_FREE_SLOTS  0 teachers in difficulty; smallest margin 11 free slots
#   GROUP_HIERARCHY     0 invalid references, 0 invalid chains;
#                       425 students matching declared group sizes

CHECK_ROOM_SUITABILITY = "ROOM_SUITABILITY"
"""Each session finds a room of the required type and sufficient capacity."""

CHECK_SLOT_COVERAGE = "SLOT_COVERAGE"
"""Open slots cover the demand for each room type.

⚠️ This is the check to watch. Computer laboratories at 95% of available
capacity are the tightest point of the instance: withdrawing one laboratory
would very probably make it infeasible. Re-read this figure whenever the
instance is modified.

Note that this duplicates H11 in arithmetic form — see C-6 on whether H11 should
therefore carry its own assumption literal in the diagnosis run.
"""

CHECK_TEACHER_LOAD = "TEACHER_LOAD"
"""No teacher is assigned more hours than the maximum load of their rank."""

CHECK_TEACHER_FREE_SLOTS = "TEACHER_FREE_SLOTS"
"""Each teacher keeps enough free slots for the sessions assigned."""

CHECK_GROUP_HIERARCHY = "GROUP_HIERARCHY"
"""The promotion → tutorial group → laboratory subgroup chain is consistent,
and students match the declared group sizes."""


class PreAnalysis(Protocol):
    """Runs all five checks and reports the structural risks found (FR-12)."""

    def verify(self, instance: object) -> list[CheckResult]: ...
