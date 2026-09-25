"""Tiered (lexicographic) solving with progress reporting and cooperative cancellation.

Tier 0 minimizes unscheduled periods once; each objective profile then optimizes its tiers
in order from that result, every finished tier becoming a constraint for the next
(ADR 0006). Reproducible mode bounds each solve by deterministic time and divides the budget
by deterministic time spent, so the same input and seed give the same timetable on any
machine (ADR 0018).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from optiedt.problem.catalog import MAX_TIER
from optiedt.problem.solution import ObjectiveConfig, Placement
from optiedt.solver.domains import Context
from optiedt.solver.heuristic import construct
from optiedt.solver.model import ScheduleModel

logger = logging.getLogger(__name__)

TIER0_SHARE = 0.3
LOG_LINES = 400
MIN_PROFILE_SECONDS = 1.0
MIN_TIER_SECONDS = 0.5


class EngineError(RuntimeError):
    """The solver could not produce any timetable."""


@dataclass(frozen=True, slots=True)
class SolveSettings:
    mode: str = "reproducible"
    time_limit_seconds: float = 60.0
    workers: int = 0
    seed: int = 1
    deterministic_per_second: float = 1.0
    """Deterministic time units granted per requested second in reproducible mode."""


@dataclass(frozen=True, slots=True)
class ProfileSpec:
    code: str
    name: str
    config: ObjectiveConfig


@dataclass(frozen=True, slots=True)
class TierOutcome:
    tier: int
    status: str
    value: int | None
    bound: float | None
    seconds: float
    deterministic_time: float

    @property
    def proven_optimal(self) -> bool:
        return self.status == "OPTIMAL"


@dataclass
class ProfileOutcome:
    code: str
    name: str
    placements: dict[int, Placement]
    tiers: list[TierOutcome]


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    phase: str
    profile: str | None
    tier: int | None
    objective: float | None
    bound: float | None
    elapsed: float


@dataclass
class EngineResult:
    tier0: TierOutcome
    base: dict[int, Placement]
    profiles: list[ProfileOutcome]
    cancelled: bool
    reproducible: bool
    model_stats: dict[str, int]
    warnings: list[str] = field(default_factory=list)
    log_tail: list[str] = field(default_factory=list)
    wall_seconds: float = 0.0


class _Progress(cp_model.CpSolverSolutionCallback):
    def __init__(self, emit: Callable[[float, float], None], should_stop: Callable[[], bool]):
        super().__init__()
        self._emit = emit
        self._should_stop = should_stop
        self._last = 0.0

    def on_solution_callback(self) -> None:
        now = time.monotonic()
        if now - self._last >= 0.5:
            self._last = now
            self._emit(self.objective_value, self.best_objective_bound)
        if self._should_stop():
            self.stop_search()


class Engine:
    def __init__(
        self,
        context: Context,
        profiles: list[ProfileSpec],
        settings: SolveSettings,
        *,
        pins: dict[int, Placement] | None = None,
        reference: dict[int, Placement] | None = None,
        hint: dict[int, Placement] | None = None,
        on_progress: Callable[[ProgressEvent], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        self.context = context
        self.profiles = profiles
        self.settings = settings
        self.pins = pins or {}
        self.reference = reference
        self.hint = hint
        self.on_progress = on_progress or (lambda event: None)
        self.should_stop = should_stop or (lambda: False)
        self.log: deque[str] = deque(maxlen=LOG_LINES)
        self.warnings: list[str] = []
        self.cancelled = False
        self.deterministic = settings.mode == "reproducible"
        self.reproducible = self.deterministic
        self._started = 0.0
        self._deterministic_spent = 0.0

    def _spent(self) -> float:
        """Budget used so far, in requested seconds."""
        if self.deterministic:
            return self._deterministic_spent / self.settings.deterministic_per_second
        return time.monotonic() - self._started

    # ── one solve ─────────────────────────────────────────────────────

    def _solve(
        self,
        builder: ScheduleModel,
        objective: cp_model.LinearExprT,
        incumbent: dict[int, Placement],
        seconds: float,
        phase: str,
        profile: str | None,
        tier: int,
    ) -> tuple[TierOutcome, dict[int, Placement]]:
        model = builder.model
        model.minimize(objective)
        builder.add_hint(incumbent)
        solver = cp_model.CpSolver()
        params = solver.parameters
        params.num_workers = self.settings.workers
        params.random_seed = self.settings.seed
        params.log_search_progress = True
        params.log_to_stdout = False
        if self.deterministic:
            params.max_deterministic_time = seconds * self.settings.deterministic_per_second
            params.interleave_search = True
            params.max_time_in_seconds = max(5.0, seconds * 3)
        else:
            params.max_time_in_seconds = seconds
        solver.log_callback = self.log.append

        def emit(value: float, bound: float) -> None:
            self.on_progress(
                ProgressEvent(phase, profile, tier, value, bound, time.monotonic() - self._started)
            )

        stop = threading.Event()

        def watch() -> None:
            while not stop.wait(0.5):
                if self.should_stop():
                    self.cancelled = True
                    solver.stop_search()
                    return

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        started = time.monotonic()
        try:
            status = solver.solve(model, _Progress(emit, self.should_stop))
        finally:
            stop.set()
            watcher.join()
        elapsed = time.monotonic() - started
        self._deterministic_spent += solver.deterministic_time
        name = solver.status_name(status)
        if status == cp_model.MODEL_INVALID:
            raise EngineError(f"The optimization model is invalid: {model.validate()}")
        if self.deterministic and elapsed >= params.max_time_in_seconds * 0.98:
            # The wall-clock safety limit ended the search, so the result depends on the machine.
            self.reproducible = False
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            outcome = TierOutcome(
                tier,
                name,
                round(solver.objective_value),
                solver.best_objective_bound,
                elapsed,
                solver.deterministic_time,
            )
            emit(solver.objective_value, solver.best_objective_bound)
            return outcome, builder.extract(solver)
        if status == cp_model.INFEASIBLE:
            # The incumbent satisfies every constraint of this model, so this cannot happen
            # unless the model is inconsistent; keep the incumbent and say so.
            logger.error("solver reported an infeasible tier", extra={"phase": phase})
            self.warnings.append(
                f"{phase}: the solver reported this tier infeasible; the previous timetable "
                "was kept for it."
            )
        return TierOutcome(tier, name, None, None, elapsed, solver.deterministic_time), incumbent

    # ── the whole run ─────────────────────────────────────────────────

    def run(self) -> EngineResult:
        self._started = time.monotonic()
        base = ScheduleModel(self.context, pins=self.pins, reference=self.reference)
        stats = {
            "variables": len(base.model.proto.variables),
            "constraints": len(base.model.proto.constraints),
            "sessions": len(self.context.problem.sessions),
            "conflict_sets": len(base.student_resources) + len(base.instructor_resources),
        }
        hint = (
            self.hint
            if self.hint is not None
            else construct(self.context, self.settings.seed, self.pins, keep=self.reference)
        )
        stats["hint_placed"] = len(hint)
        self.on_progress(
            ProgressEvent("model_built", None, None, None, None, time.monotonic() - self._started)
        )

        total = self.settings.time_limit_seconds
        tier0_objective = base.tier_expression(ObjectiveConfig({}), 0)
        if tier0_objective is None or isinstance(tier0_objective, int):
            tier0 = TierOutcome(0, "OPTIMAL", int(tier0_objective or 0), 0.0, 0.0, 0.0)
            incumbent: dict[int, Placement] = {}
        else:
            tier0, incumbent = self._solve(
                base,
                tier0_objective,
                hint,
                max(MIN_TIER_SECONDS, total * TIER0_SHARE),
                "unscheduled",
                None,
                0,
            )
            if tier0.value is None:
                raise EngineError(
                    "No timetable was found within the time limit, not even a partial one. "
                    "Increase the time limit or check the validation report."
                )
            base.model.add(tier0_objective <= tier0.value)
        base.model.clear_hints()  # type: ignore[no-untyped-call]

        profiles: list[ProfileOutcome] = []
        for position, spec in enumerate(self.profiles):
            if self.cancelled or self.should_stop():
                self.cancelled = True
                break
            remaining = len(self.profiles) - position
            budget = max(MIN_PROFILE_SECONDS, (total - self._spent()) / remaining)
            profiles.append(self._run_profile(base, spec, incumbent, budget))
        return EngineResult(
            tier0=tier0,
            base=incumbent,
            profiles=profiles,
            cancelled=self.cancelled,
            reproducible=self.reproducible and not self.cancelled,
            model_stats=stats,
            warnings=self.warnings,
            log_tail=list(self.log),
            wall_seconds=time.monotonic() - self._started,
        )

    def _run_profile(
        self,
        base: ScheduleModel,
        spec: ProfileSpec,
        incumbent: dict[int, Placement],
        budget: float,
    ) -> ProfileOutcome:
        builder = base.fork()
        builder.reference = spec.config.reference
        tiers = [
            (tier, expr)
            for tier in range(1, MAX_TIER + 1)
            if (expr := builder.tier_expression(spec.config, tier)) is not None
            and not isinstance(expr, int)
        ]
        placements = dict(incumbent)
        outcomes: list[TierOutcome] = []
        profile_started = self._spent()
        for position, (tier, expr) in enumerate(tiers):
            if self.cancelled or self.should_stop():
                self.cancelled = True
                break
            left = budget - (self._spent() - profile_started)
            share = max(MIN_TIER_SECONDS, left / (len(tiers) - position))
            outcome, placements = self._solve(
                builder, expr, placements, share, f"{spec.code}:tier{tier}", spec.code, tier
            )
            outcomes.append(outcome)
            if outcome.value is not None:
                builder.model.add(expr <= outcome.value)
        return ProfileOutcome(spec.code, spec.name, placements, outcomes)
