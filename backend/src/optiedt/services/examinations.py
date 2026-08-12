"""The examination session as a use case — FR-20.

Sits between `api` and `examination` for the reason `services/portfolio.py`
sits between `api` and `solver`: the twelfth import contract forbids a router
from importing the examination solver, so a solve cannot be launched inside a
request handler. ADR-005's rule is not about which package is tidier — it is
that solving takes tens of seconds to minutes and no HTTP request is held open
for it.

**The lifecycle is the weekly one, minus the stages exams do not have:**

    PENDING → SOLVING → COMPLETED
                     └→ INFEASIBLE
                     └→ FAILED

No PREANALYSIS (the five checks are about the weekly grid), no SCORING (FR-20
asks for a timetable, not a ranked portfolio) and no DIAGNOSING (FR-8's
conflict report is a weekly-model requirement; nothing asks for one here).
`RunState` is reused rather than duplicated — a second enum with five of the
same members would be two vocabularies for one idea.

⚠️ **Examination runs are held in memory and do not survive a restart, by
scope rather than by oversight.** FR-19 — *"record every run with its data,
seed, weights and results"* — is a requirement about the *generation* run and
is met by the database-backed stores. FR-20 requires *"one slot and one or more
rooms assigned to each examination"* and no record of the solve. Adding a
table, a migration and a store contract for something no requirement asks for
is exactly the scope expansion Phase 13 was told not to undertake. The day a
requirement asks for it, `ExamRunStore` is already the seam to implement.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol

from optiedt.domain.entities import Room
from optiedt.domain.enums import RunState
from optiedt.domain.examination import ExamSession, ExamTimetable
from optiedt.domain.instance import Instance
from optiedt.examination.derive import (
    ExaminationNotDerivableError,
    derive_examination_session,
)
from optiedt.examination.solver import ExamSolver

logger = logging.getLogger(__name__)


def exam_solver_factory(
    workers: int, wall_clock_ceiling_seconds: float
) -> Callable[[], ExamSolver]:
    """The production examination solver, configured from settings.

    Here rather than in `optiedt.api` for the reason `cp_sat_factory` is in
    `tasks`: the API layer may not import the examination solver (the twelfth
    import contract). The API asks `services` for the service and never names
    CP-SAT.
    """

    def build() -> ExamSolver:
        return ExamSolver(
            workers=workers,
            wall_clock_ceiling_seconds=wall_clock_ceiling_seconds,
        )

    return build


@dataclass(frozen=True, slots=True)
class ExamRunRecord:
    """One examination generation, and whatever it has produced so far."""

    id: str
    state: RunState
    created_at: datetime
    seed: int
    deterministic_budget: float
    session: ExamSession | None = None
    timetable: ExamTimetable | None = None
    room_capacities: dict[str, int] = field(default_factory=dict)
    """Capacity per room id, snapshotted when the session was derived.

    Carried on the record so a reader can check X2 — assigned capacity against
    candidate count — without refetching the instance, and so the figure cannot
    drift from the rooms the solve actually saw."""

    error: str | None = None
    """Why the run failed, in words the person in charge can act on.

    ⚠️ Most often this carries `ExaminationNotDerivableError`'s message — an
    empty roster, an unset examination period, a course with no CM teacher.
    Those are refusals to build a session at all, not solver failures, and the
    screen shows them verbatim rather than as "generation failed".
    """

    def to(self, state: RunState) -> ExamRunRecord:
        return replace(self, state=state)


class ExamRunStore(Protocol):
    def save(self, record: ExamRunRecord) -> None: ...
    def get(self, run_id: str) -> ExamRunRecord | None: ...
    def list(self) -> tuple[ExamRunRecord, ...]: ...


@dataclass
class InMemoryExamRunStore:
    """The only implementation. See the module docstring on why there is no
    database-backed sibling."""

    _records: dict[str, ExamRunRecord] = field(default_factory=dict)

    def save(self, record: ExamRunRecord) -> None:
        self._records[record.id] = record

    def get(self, run_id: str) -> ExamRunRecord | None:
        return self._records.get(run_id)

    def list(self) -> tuple[ExamRunRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda r: r.created_at, reverse=True))


InstanceProvider = Callable[[], Instance]


class SolvesExaminations(Protocol):
    """What the service needs of a solver. A Protocol so a test can pass a
    fake and never wait on real CP-SAT."""

    def solve(self, session: ExamSession, rooms: tuple[Room, ...]) -> ExamTimetable: ...


ExamSolverFactory = Callable[[], SolvesExaminations]


class ExaminationService:
    """Starts examination solves off the request thread and reports on them.

    One at a time, on a single-worker pool, for the reason `tasks/executor.py`
    gives: each solve uses many cores, and overlapping two would oversubscribe
    the machine in a way that looks like broken tooling rather than contention.
    """

    def __init__(
        self,
        store: ExamRunStore,
        instance_provider: InstanceProvider,
        solver_factory: ExamSolverFactory,
    ) -> None:
        self._store = store
        self._instance_provider = instance_provider
        self._solver_factory = solver_factory
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="optiedt-exam")

    def start(self, seed: int, deterministic_budget: float) -> tuple[ExamRunRecord, Future[None]]:
        """Record a PENDING run and queue it. Returns the Future so a test can
        wait on the solve without sleeping — the same affordance
        `RunExecutor.submit` provides."""
        record = ExamRunRecord(
            id=uuid.uuid4().hex[:12],
            state=RunState.PENDING,
            created_at=datetime.now(UTC),
            seed=seed,
            deterministic_budget=deterministic_budget,
        )
        self._store.save(record)
        return record, self._pool.submit(self._execute, record.id)

    def get(self, run_id: str) -> ExamRunRecord | None:
        return self._store.get(run_id)

    def list(self) -> tuple[ExamRunRecord, ...]:
        return self._store.list()

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)

    # ── the pipeline ───────────────────────────────────────────────────

    def _execute(self, run_id: str) -> None:
        record = self._store.get(run_id)
        if record is None:  # pragma: no cover - only if a store drops a run
            logger.error("examination run %s vanished before execution", run_id)
            return
        try:
            instance = self._instance_provider()
            session = derive_examination_session(
                instance,
                seed=record.seed,
                deterministic_budget=record.deterministic_budget,
            )
            record = replace(
                record.to(RunState.SOLVING),
                session=session,
                room_capacities={r.id: r.capacity for r in instance.rooms},
            )
            self._store.save(record)

            timetable = self._solver_factory().solve(session, instance.rooms)

            if timetable.infeasible:
                self._store.save(replace(record.to(RunState.INFEASIBLE), timetable=timetable))
                return
            self._store.save(replace(record.to(RunState.COMPLETED), timetable=timetable))
        except ExaminationNotDerivableError as exc:
            # A refusal to build the session, not a solver failure. Carried
            # verbatim: "the instance carries no students" is actionable and
            # "generation failed" is not.
            logger.info("examination run %s refused: %s", run_id, exc)
            self._fail(run_id, str(exc))
        except Exception as exc:  # the record must carry the reason, whatever it was
            logger.exception("examination run %s failed", run_id)
            self._fail(run_id, f"{type(exc).__name__}: {exc}")

    def _fail(self, run_id: str, message: str) -> None:
        current = self._store.get(run_id)
        if current is None:  # pragma: no cover
            return
        self._store.save(replace(current.to(RunState.FAILED), error=message))


__all__ = [
    "ExamRunRecord",
    "ExamRunStore",
    "ExaminationService",
    "InMemoryExamRunStore",
    "SolvesExaminations",
    "exam_solver_factory",
]
