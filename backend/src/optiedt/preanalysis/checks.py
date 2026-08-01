"""Stage 1 of every run: five arithmetic checks, no solver involved.

Their purpose is to distinguish two situations a solver reports identically:
an instance that GENUINELY has no solution, and an ERROR IN THE MODEL.

This is the primary debugging instrument of the project, not a nicety. The
reference instance sits at 91% computer-laboratory occupancy OF TWO-PERIOD
WINDOWS — 8 spare in the whole week; at that saturation a modelling regression
surfaces as INFEASIBLE rather than as a slow solve, and without these checks
you cannot tell which you are looking at. Run them first, always.

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
#   SLOT_COVERAGE       BY PERIOD, necessary but NOT sufficient:
#                       lecture theatres 57% · classrooms 42%
#                       · computer laboratories 71% · science laboratories 57%
#                       BY TWO-PERIOD WINDOW, the bound that binds:
#                       computer laboratories 91% ← the number to watch
#                       · science laboratories 73%
#   TEACHER_LOAD        0 teachers above the limit; heaviest 12 periods (18 h)
#   TEACHER_FREE_SLOTS  0 teachers in difficulty; smallest margin 11 free slots
#   GROUP_HIERARCHY     0 invalid references, 0 invalid chains;
#                       425 students matching declared group sizes

CHECK_ROOM_SUITABILITY = "ROOM_SUITABILITY"
"""Each session finds a room of the required type and sufficient capacity."""

CHECK_SLOT_COVERAGE = "SLOT_COVERAGE"
"""Open slots cover the demand for each room type.

⚠️ This is the check to watch, and it MUST APPLY BOTH BOUNDS.

The period bound (`sessions * duration <= rooms * open_slots`) is necessary but
NOT sufficient. Every laboratory session spans two periods, a two-period
session must fit inside one day (H8) and a 5-period day offers a room only two
such windows — so what a room really offers is `Σ floor(L/2)` over the week's
contiguous runs: 11 windows, not 28 periods. The contiguity bound is
`sessions of duration d <= rooms * Σ floor(L/d)`.

Computer laboratories are the tightest point at 91% OF TWO-PERIOD WINDOWS —
8 spare in the week — against a reassuring 71% of periods. Withdrawing one
laboratory removes 11 windows and makes the instance infeasible.

⚠️ Shipping the period bound alone would put the C-13 blind spot inside the
product: it passed a genuinely infeasible instance while reporting a
comfortable 95%, and three sessions went looking for a solver bug that did not
exist. FR-12 must port BOTH bounds. The working logic is already in
data/verification/verify_instance.py.

Note that this duplicates H11 in arithmetic form. C-6 is RESOLVED: H11 carries
NO assumption literal, because it is implied by H3 once `room[s]` is assigned
and there is no separate posting to attach one to. Only H1, H3, H7 and H12
carry literals.
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
