"""The run record and its lifecycle.

Solving takes minutes, so no HTTP request is held open for it
(docs/architecture.md). `POST /runs` records a run in `PENDING` and returns
202; a background task moves it through the states below; the client polls
`GET /runs/{id}`.

    PENDING -> PREANALYSIS -> SOLVING -> SCORING -> COMPLETED
                                  |
                                  +-> INFEASIBLE -> DIAGNOSING -> DIAGNOSED
    (any non-terminal)  -> FAILED

**PREANALYSIS runs the five checks** (FR-12, Phase 5 M1). They live in
`optiedt.preanalysis.verifications`, carry BOTH the period bound and the
contiguity bound - the period bound alone is what let C-13 through - and their
results are recorded on the run whether they pass or fail. A failing check does
not stop the run: stage 1 then stage 2 always, and stage 3 only on INFEASIBLE
(docs/architecture.md).

**DIAGNOSING/DIAGNOSED are entered** (FR-8, Phase 5 M2), and only from
`INFEASIBLE` - never speculatively. `Solver.diagnose` returns the rules
sufficient to explain the conflict, at one worker with no objective.

⚠️ An infeasible run therefore ends in `DIAGNOSED`, not `INFEASIBLE`, and
`DIAGNOSED` does NOT mean a conflict was named: the diagnosis can be
inconclusive (CP-SAT could not prove the infeasibility) or conclusive with an
empty set (no relaxable rule explains it). `DiagnosisResult.detail` says which.

Storage is in memory: a restart loses every run. That is Phase 4's documented
position (`docs/status.md`) - the run record proper is Phase 5, FR-19. The
Protocol below is the seam.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol

from optiedt.analysis.interfaces import Decomposition, DominanceVerdict, Recommendation
from optiedt.analysis.ranking import DefaultRanker
from optiedt.domain.entities import (
    Candidate,
    ConstraintCode,
    DiagnosisResult,
    Run,
    RunId,
)
from optiedt.domain.enums import RunState
from optiedt.preanalysis.checks import CheckResult

MODEL_VERSION = "weekly.h1-h12.s2-s10"
"""What produced a candidate, recorded with every run.

Bump it when the constraint set or a criterion formula changes, because a score
is only comparable across runs that were computed the same way. It is a
property of the MODEL, not of the package version - a documentation fix must
not invalidate a recorded run.
"""


ALLOWED_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.PENDING: frozenset({RunState.PREANALYSIS, RunState.FAILED}),
    RunState.PREANALYSIS: frozenset({RunState.SOLVING, RunState.FAILED}),
    RunState.SOLVING: frozenset({RunState.SCORING, RunState.INFEASIBLE, RunState.FAILED}),
    RunState.SCORING: frozenset({RunState.COMPLETED, RunState.FAILED}),
    RunState.INFEASIBLE: frozenset({RunState.DIAGNOSING}),
    RunState.DIAGNOSING: frozenset({RunState.DIAGNOSED, RunState.FAILED}),
    RunState.COMPLETED: frozenset(),
    RunState.DIAGNOSED: frozenset(),
    RunState.FAILED: frozenset(),
}
"""Which state may follow which.

`INFEASIBLE` is deliberately NOT terminal: the diagnosis branch leaves from it
(Phase 5). `COMPLETED`, `DIAGNOSED` and `FAILED` are.

⚠️ `SOLVING -> INFEASIBLE` bypasses `SCORING` on purpose. There is nothing to
score: an instance admitting no timetable under one profile admits none under
any, because H1-H12 are declared identically whatever the weights, which is why
`generate_portfolio` stops at the first infeasible solve.
"""

TERMINAL_STATES = frozenset(
    {RunState.COMPLETED, RunState.DIAGNOSED, RunState.FAILED},
)


class IllegalTransitionError(RuntimeError):
    """Raised rather than silently corrected.

    A run that jumps a state is a bug in the executor, and letting it through
    would leave the record describing a pipeline that did not happen.
    """


def check_transition(current: RunState, target: RunState) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise IllegalTransitionError(f"{current.value} -> {target.value} is not a legal transition")


@dataclass(frozen=True, slots=True)
class RunRecord:
    """One run, everything known about it, immutable per revision.

    Replaced wholesale on each transition rather than mutated, so a reader
    holding a record never sees it change under them - the same reasoning that
    makes a Candidate immutable (invariant 6).
    """

    run: Run
    weights: dict[ConstraintCode, float]
    """The weights in force: ONE vector prices every candidate of this run.

    Recorded because the exact-decomposition identity only holds when the same
    w_i prices both sides (docs/scoring-and-explanation.md). The comparison
    endpoint must decompose under this vector, not under a candidate's
    producing profile, which is provenance only.
    """

    candidates: tuple[Candidate, ...] = ()
    pre_analysis: tuple[CheckResult, ...] = ()
    diagnosis: DiagnosisResult | None = None
    duplicates_removed: tuple[str, ...] = ()
    deterministic_time_used: float = 0.0
    wall_clock_seconds: float = 0.0
    error: str | None = None

    @property
    def state(self) -> RunState:
        return self.run.state

    def to(self, target: RunState) -> RunRecord:
        check_transition(self.run.state, target)
        return replace(self, run=replace(self.run, state=target))


class RunStore(Protocol):
    """Runs by id. Phase 5 substitutes a database-backed implementation."""

    def create(self, record: RunRecord) -> None: ...

    def get(self, run_id: RunId) -> RunRecord | None: ...

    def save(self, record: RunRecord) -> None: ...

    def all(self) -> tuple[RunRecord, ...]: ...


class InMemoryRunStore:
    """Dict-backed, guarded by a lock.

    The lock is not decoration: the executor writes from a worker thread while
    request handlers read, and a dict resized mid-read is exactly the kind of
    fault that appears once a week and never in a test.
    """

    def __init__(self) -> None:
        self._records: dict[RunId, RunRecord] = {}
        self._lock = threading.Lock()

    def create(self, record: RunRecord) -> None:
        with self._lock:
            if record.run.id in self._records:
                raise KeyError(f"run {record.run.id} already exists")
            self._records[record.run.id] = record

    def get(self, run_id: RunId) -> RunRecord | None:
        with self._lock:
            return self._records.get(run_id)

    def save(self, record: RunRecord) -> None:
        with self._lock:
            self._records[record.run.id] = record

    def all(self) -> tuple[RunRecord, ...]:
        with self._lock:
            return tuple(
                sorted(self._records.values(), key=lambda r: r.run.created_at, reverse=True)
            )


@dataclass(frozen=True, slots=True)
class RunRequest:
    """What a client asks for. Deliberately small.

    The weight profiles are NOT client-supplied in Phase 4: they are the three
    of `docs/constraint-model.md`, fixed in `services/portfolio.py`. Letting a
    client post arbitrary profiles would make two runs incomparable without
    anything recording why.
    """

    seed: int
    deterministic_budget: float
    """For the WHOLE portfolio, divided between the profiles - never per
    profile. Deterministic time, never wall clock (ADR-011)."""


def new_run_record(
    run_id: RunId, request: RunRequest, weights: dict[ConstraintCode, float]
) -> RunRecord:
    return RunRecord(
        run=Run(
            id=run_id,
            created_at=datetime.now(UTC),
            seed=request.seed,
            deterministic_budget=request.deterministic_budget,
            state=RunState.PENDING,
            model_version=MODEL_VERSION,
        ),
        weights=dict(weights),
    )


# ── Reading a finished run ─────────────────────────────────────────────


def candidate_of(record: RunRecord, candidate_id: str) -> Candidate | None:
    return next((c for c in record.candidates if c.id == candidate_id), None)


def ranker_for(record: RunRecord) -> DefaultRanker:
    """The ranker that priced this run, rebuilt from the recorded weights.

    Rebuilt rather than stored so that a run read back after a restart (Phase 5)
    decomposes identically to one still in memory.
    """
    return DefaultRanker(weights=record.weights)


def decomposition_for(record: RunRecord, a: Candidate, b: Candidate) -> Decomposition:
    return ranker_for(record).decompose(a, b)


def dominance_for(record: RunRecord) -> list[DominanceVerdict]:
    return ranker_for(record).dominance(list(record.candidates))


def recommendation_for(record: RunRecord) -> Recommendation | None:
    return ranker_for(record).recommend(list(record.candidates))
