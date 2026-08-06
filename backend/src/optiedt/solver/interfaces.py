"""Contracts of the decision layer.

This is the ONLY part of the system that assigns a slot and a room to a session.
Its correctness is guaranteed by construction rather than by testing: the solver
never produces an assignment violating a rule it was given.

See docs/constraint-model.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from ortools.sat.python import cp_model

from optiedt.domain.entities import (
    Candidate,
    ConstraintCode,
    DiagnosisResult,
    Placement,
    RoomId,
    SessionId,
    SlotIndex,
    WeightProfile,
)
from optiedt.domain.instance import Instance

if TYPE_CHECKING:
    # Deferred: variables.py imports SolverInput from this module, so a
    # top-level import here would be circular. Safe as a type-only import
    # because every annotation in this file is a lazy string (see the
    # __future__ import above) - Protocol.apply() never evaluates Variables
    # at runtime, only mypy needs to resolve it.
    from optiedt.solver.variables import Variables


@dataclass(frozen=True, slots=True)
class SolverInput:
    """Everything one solve needs.

    The three ``locked`` / ``excluded`` fields are the only things a
    recommendation may change (ADR-007). A recommendation can alter what the
    solver is ASKED to do, never what a solver call is ALLOWED to return.
    """

    instance: Instance
    profile: WeightProfile
    seed: int
    deterministic_budget: float
    """Deterministic time, NOT wall-clock seconds.

    Wall-clock bounds with parallel workers are not reproducible — workers race,
    and a fixed seed does not fix it. See ADR-011. A wall-clock ceiling exists
    separately as a hang backstop only.
    """

    locked_placements: frozenset[Placement] = frozenset()
    """H10: sessions pinned to the slot and room they already hold.

    Carries the TARGET, not just the session id, because "locked" is
    meaningless without saying locked to what. It reuses the domain's own
    ``Placement`` deliberately: a lock IS a placement the solver must
    reproduce, and a separate ``LockedSession(session, slot, room)`` type would
    be ``Placement`` under a second name (C-19).

    ⚠️ This field replaced ``locked_sessions: frozenset[SessionId]`` on
    2026-08-06. That field could never be honoured - ``build_variables``
    raised on it - so nothing is lost and a caller can no longer choose the
    form that cannot work.

    ``recommendations.LockedPlacement`` is a separate type carrying the same
    three values, because ``solver`` may not import ``recommendations``
    (docs/architecture.md's module map). ``services/`` maps one onto the
    other; that mapping is the layer boundary doing its job.
    """

    excluded_slots: frozenset[tuple[SessionId, SlotIndex]] = frozenset()
    excluded_rooms: frozenset[tuple[SessionId, RoomId]] = frozenset()


@dataclass(frozen=True, slots=True)
class SolverOutput:
    """The result of one solve.

    ``placements`` is empty when ``infeasible`` is True, which is the signal to
    enter the diagnosis run — never the ordinary path.
    """

    placements: tuple[Placement, ...]
    cost: int
    infeasible: bool
    proven_optimal: bool
    deterministic_time_used: float
    wall_clock_seconds: float


class ConstraintBuilder(Protocol):
    """Builds one hard constraint into the CP-SAT model.

    Registered by code, H1 through H12.

    Two things to know before implementing one:

    - **H4, H5, H6, H8, H9 and H10 are applied by reducing variable domains
      BEFORE the search begins**, not by posting constraints checked afterwards.
      This costs nothing during solving and shrinks the space to explore.

    - **``carries_assumption_literal`` must be False for any constraint that
      overlaps another.** H2 is subsumed by H12; H11 is implied by H3. If two
      relaxable constraints covered the same ground, the diagnosis could name
      either, and the report would name a rule the user cannot act on. The
      mapping must be 1:1 and non-redundant. This is C-6, RESOLVED: only H1,
      H3, H7 and H12 qualify, because they are the only constraints that are
      posted objects at all.

    ⚠️ **``carries_assumption_literal`` no longer describes a literal.** Read it
    as *"may be withdrawn individually"*: it selects which constraints
    ``Solver.diagnose`` omits, one at a time, to find which are responsible for
    an infeasibility (C-17). The name is kept because C-6's recorded resolution
    references it across four documents and codes in this project are stable
    identifiers; the four constraints it selects, and the reason, are unchanged.

    **Stage 2 and stage 3 post through the SAME builders**, deliberately: a
    separate diagnosis model could name a conflict that does not exist in the
    model actually solved, and nothing would catch it. Stage 3 differs only in
    which builders it calls.
    """

    @property
    def code(self) -> ConstraintCode: ...

    @property
    def carries_assumption_literal(self) -> bool: ...

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None: ...


class Solver(Protocol):
    """The three-stage pipeline. See docs/architecture.md.

    Stage 2 (``solve``) uses all workers and carries the objective.
    Stage 3 (``diagnose``) is entered ONLY on an infeasible result. It
    withdraws one withdrawable rule at a time and solves plainly, and obeys
    three rules:

      - **a single worker** — for reproducibility of the VERDICT, not because
        CP-SAT requires it. ``max_deterministic_time`` is a per-worker budget,
        so more workers do more total work and could flip an ``UNKNOWN`` to an
        ``INFEASIBLE`` between machines. A conflict report naming different
        rules on different machines would be worse than none;
      - **no objective** — imposed. This is a feasibility question;
      - **sufficient AND irreducible**, when every removal was decided. A
        removal the solver could not decide keeps its rule for want of
        evidence, and ``is_minimal`` stays False.

    ⚠️ Two of those three were rewritten by **C-17** (2026-08-04). They had
    been recorded as "imposed by CP-SAT itself" and were imposed by the
    enforcement-literal mechanism that C-17 replaced: an infeasibility a plain
    solve proves in 0.0 s returned ``UNKNOWN`` after 240 s under assumptions,
    because a literal takes its constraint out of presolve.
    """

    def solve(self, request: SolverInput) -> SolverOutput: ...

    def diagnose(self, request: SolverInput) -> DiagnosisResult: ...


@dataclass(frozen=True, slots=True)
class PortfolioResult:
    """The candidates of one run, one per weight profile, duplicates removed.

    ⚠️ "Duplicates removed" once looked like a conflict with the acceptance
    criterion: if two profiles converge, the system behaves correctly and a
    test demanding three candidates fails. **C-5 resolved this on 2026-08-05**
    and the implementation did not move — the general contract is "at most
    three, duplicates removed" (SRS Table 29), while the acceptance criterion
    is tied to the verified reference instance at production settings, where
    the measurement is 3 distinct / 0 removed. ``tests/acceptance/test_fr13.py``
    asserts exactly three; a weaker assertion would hide a regression.
    """

    candidates: tuple[Candidate, ...] = field(default_factory=tuple)
    diagnosis: DiagnosisResult | None = None
