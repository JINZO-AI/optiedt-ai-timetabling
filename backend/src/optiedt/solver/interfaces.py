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

    locked_sessions: frozenset[SessionId] = frozenset()
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
      overlaps another.** H2 is subsumed by H12; H11 is implied by H3. Redundant
      literals let the solver return either one, so the conflict report can name
      a rule the user cannot act on. The mapping constraint → literal must be
      1:1 and non-redundant. This is C-6, RESOLVED: only H1, H3, H7 and H12
      carry one, because they are the only constraints that are posted objects
      at all.

    ``apply`` takes an optional enforcement ``literal``, used only by the
    diagnosis run (stage 3, ``Solver.diagnose``). **Stage 2 and stage 3 post
    through the SAME builders**, deliberately: a separate diagnosis model could
    name a conflict that does not exist in the model actually solved, and
    nothing would catch it. A builder whose ``carries_assumption_literal`` is
    False ignores the argument — it has no posting to attach one to.
    """

    @property
    def code(self) -> ConstraintCode: ...

    @property
    def carries_assumption_literal(self) -> bool: ...

    def apply(
        self,
        model: cp_model.CpModel,
        variables: Variables,
        instance: Instance,
        literal: cp_model.IntVar | None = None,
    ) -> None: ...


class Solver(Protocol):
    """The three-stage pipeline. See docs/architecture.md.

    Stage 2 (``solve``) uses all workers and carries the objective.
    Stage 3 (``diagnose``) is entered ONLY on an infeasible result and obeys
    three rules imposed by CP-SAT itself:

      - a single worker — solving under assumptions admits no parallelism;
      - no objective — with one, the whole assumption set is returned and the
        mechanism becomes useless;
      - the result is sufficient, not minimal.
    """

    def solve(self, request: SolverInput) -> SolverOutput: ...

    def diagnose(self, request: SolverInput) -> DiagnosisResult: ...


@dataclass(frozen=True, slots=True)
class PortfolioResult:
    """The candidates of one run, one per weight profile, duplicates removed.

    ⚠️ "Duplicates removed" conflicts with the acceptance criterion "at least
    three candidates produced": if two profiles converge, the system behaves
    correctly and the test fails. This is C-5 — resolve it before writing the
    FR-13 acceptance test.
    """

    candidates: tuple[Candidate, ...] = field(default_factory=tuple)
    diagnosis: DiagnosisResult | None = None
