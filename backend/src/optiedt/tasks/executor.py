"""The background run executor.

In-process, not behind a message broker. A broker would add a component to
install, secure and monitor for a load of a few generations per semester on one
server (ADR-005) - a decision recorded so it can be revisited if several
departments ever generate at once, which is the condition that would change the
answer.

⚠️ **One solve at a time, enforced by a single-worker pool.** Two reasons, and
the second is the one that bites:

1. `docs/architecture.md` stage 2 requires the profiles to be solved one after
   the other, not concurrently. `generate_portfolio` already does that within a
   run; this keeps it true ACROSS runs.
2. Each solve uses every CPU core (`solver_workers = 0`). Overlapping two runs
   would oversubscribe the machine badly enough to make unrelated shell
   commands stall for minutes - a failure that looks exactly like broken
   tooling rather than like contention (CLAUDE.md, "Three traps").
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace

from optiedt.domain.enums import RunState
from optiedt.domain.instance import Instance
from optiedt.services.portfolio import PortfolioRequest, generate_portfolio
from optiedt.services.runs import TERMINAL_STATES, RunRecord, RunStore
from optiedt.solver.engine import CpSatSolver
from optiedt.solver.interfaces import Solver

logger = logging.getLogger(__name__)

InstanceProvider = Callable[[], Instance]
SolverFactory = Callable[[], Solver]


def cp_sat_factory(workers: int, wall_clock_ceiling_seconds: float) -> SolverFactory:
    """The production solver, configured from settings.

    Lives here rather than in `optiedt.api` because the API layer may not
    import the solver — `.importlinter`'s `api-cannot-reach-the-solver`, which
    exists so a router cannot launch a solve inside a request handler. The API
    asks `tasks` for an executor and never names CP-SAT.

    Built per solve, not shared: `CpSatSolver` is a frozen dataclass carrying
    configuration only, so constructing it at that moment means a settings
    change takes effect without a restart.
    """

    def build() -> Solver:
        return CpSatSolver(
            workers=workers,
            wall_clock_ceiling_seconds=wall_clock_ceiling_seconds,
        )

    return build


class RunExecutor:
    """Moves a run through its states, off the request thread."""

    def __init__(
        self,
        store: RunStore,
        instance_provider: InstanceProvider,
        solver_factory: SolverFactory,
    ) -> None:
        self._store = store
        self._instance_provider = instance_provider
        self._solver_factory = solver_factory
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="optiedt-run")

    def submit(self, run_id: str) -> Future[None]:
        """Queue a run. Returns the Future so a test can wait without sleeping."""
        return self._pool.submit(self._execute, run_id)

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)

    # ── the pipeline ───────────────────────────────────────────────────

    def _execute(self, run_id: str) -> None:
        record = self._store.get(run_id)
        if record is None:  # pragma: no cover - only if a store drops a run
            logger.error("run %s vanished before execution", run_id)
            return
        try:
            record = self._preanalyse(record)
            self._solve(record)
        except Exception as exc:  # the record must carry the reason, whatever it was
            logger.exception("run %s failed", run_id)
            self._fail(run_id, exc)

    def _preanalyse(self, record: RunRecord) -> RunRecord:
        """Stage 1. Runs no checks yet - see services/runs.py.

        The state is entered so the lifecycle is honest about where a run is,
        and the check list stays EMPTY rather than being filled with passes
        nobody computed. FR-12 fills it in Phase 5.
        """
        record = record.to(RunState.PREANALYSIS)
        self._store.save(record)
        return record

    def _solve(self, record: RunRecord) -> RunRecord:
        record = record.to(RunState.SOLVING)
        self._store.save(record)

        report = generate_portfolio(
            PortfolioRequest(
                instance=self._instance_provider(),
                run=record.run.id,
                seed=record.run.seed,
                deterministic_budget=record.run.deterministic_budget,
                scoring_weights=dict(record.weights),
                candidate_id_prefix=f"{record.run.id}-cand",
            ),
            self._solver_factory(),
        )

        record = replace(
            record,
            duplicates_removed=report.duplicates_removed,
            deterministic_time_used=report.deterministic_time_used,
            wall_clock_seconds=report.wall_clock_seconds,
        )

        if report.infeasible:
            # Stops here. DIAGNOSING is Phase 5; entering it would report a
            # conflict set nobody computed.
            record = record.to(RunState.INFEASIBLE)
            self._store.save(record)
            return record

        record = replace(record.to(RunState.SCORING), candidates=report.result.candidates)
        self._store.save(record)

        record = record.to(RunState.COMPLETED)
        self._store.save(record)
        return record

    def _fail(self, run_id: str, exc: Exception) -> None:
        """Record the reason on whatever revision the store now holds.

        Re-read rather than reuse the local record: the pipeline saves as it
        goes, so the store's copy is the later one, and overwriting it with a
        stale local would discard the timings already recorded.
        """
        current = self._store.get(run_id)
        if current is None or current.state in TERMINAL_STATES:  # pragma: no cover
            return
        message = f"{type(exc).__name__}: {exc}"
        if current.state is RunState.INFEASIBLE:
            # INFEASIBLE is not a failure and may only lead to DIAGNOSING.
            # Keep the state, carry the reason.
            self._store.save(replace(current, error=message))
            return
        self._store.save(replace(current.to(RunState.FAILED), error=message))
