"""Tiered (lexicographic) solving with progress reporting and cooperative cancellation.

Tier 0 minimizes unscheduled periods once; each objective profile then optimizes its tiers
in order from that result, every finished tier becoming a constraint for the next
(ADR 0006). Reproducible mode bounds each solve by deterministic time and divides the budget
by deterministic time spent, so the same input and seed give the same timetable on any
machine (ADR 0018).
"""

from __future__ import annotations

import dataclasses
import logging
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from optiedt.problem.catalog import MAX_TIER
from optiedt.problem.solution import ObjectiveConfig, Placement
from optiedt.solver.domains import Context
from optiedt.solver.heuristic import construct
from optiedt.solver.model import LinearExpr, ScheduleModel

logger = logging.getLogger(__name__)

TIER0_SHARE = 0.3
WIDEN_SHARE = 0.1
LOG_LINES = 400
MIN_PROFILE_SECONDS = 1.0
MIN_TIER_SECONDS = 0.5
# In reproducible (interleaved) search every batch waits for its slowest task, and the first
# task of an LP-based worker on a faculty-sized model takes many deterministic seconds. The
# reproducible portfolio therefore keeps the cheap full-problem workers and the neighbourhood
# (LNS) workers only; measured on a 195-session instance it reaches a third of the objective
# value the default portfolio reaches in the same deterministic time (ADR 0018).
REPRODUCIBLE_IGNORED_SUBSOLVERS = (
    "default_lp",
    "fixed",
    "max_lp",
    "max_lp_sym",
    "quick_restart",
    "reduced_costs",
    "lb_tree_search",
    "probing*",
    "objective_lb_search*",
)
REPRODUCIBLE_BATCH_SIZE = 4


class EngineError(RuntimeError):
    """The solver could not produce any timetable."""


@dataclass(frozen=True, slots=True)
class SolveSettings:
    mode: str = "fastest"
    """``fastest`` races the workers against the clock; ``reproducible`` gives the same
    timetable for the same snapshot, settings and seed on any machine (ADR 0018)."""
    time_limit_seconds: float = 60.0
    workers: int = 0
    seed: int = 1
    deterministic_per_second: float = 0.3
    """Deterministic time granted per requested second in reproducible mode: about one
    wall-clock second each on a four-core machine (measured, ADR 0018)."""


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
    """Reports improving solutions, at most twice a second.

    It never stops the search itself: OR-Tools 9.15 aborts the process
    (``solution->size() == postsolve_mapping.size()``) when ``stop_search`` is called from
    the callback of a solution found while loading a complete hint. Cancellation goes
    through the watcher thread in ``Engine._solve`` instead.
    """

    def __init__(self, emit: Callable[[float, float], None]):
        super().__init__()
        self._emit = emit
        self._last = 0.0

    def on_solution_callback(self) -> None:
        now = time.monotonic()
        if now - self._last >= 0.5:
            self._last = now
            self._emit(self.objective_value, self.best_objective_bound)


@dataclass
class Solve:
    """What one search produced."""

    outcome: TierOutcome
    placements: dict[int, Placement]
    measured: dict[str, int]
    """Values of the expressions passed as ``measure``, when the search found a solution."""


class Runner:
    """Runs one CP-SAT search at a time: warm start, parameters, progress, cancellation,
    budget accounting and the solver log."""

    def __init__(
        self,
        settings: SolveSettings,
        on_progress: Callable[[ProgressEvent], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        self.settings = settings
        self.on_progress = on_progress or (lambda event: None)
        self.should_stop = should_stop or (lambda: False)
        self.log: deque[str] = deque(maxlen=LOG_LINES)
        self.warnings: list[str] = []
        self.cancelled = False
        self.deterministic = settings.mode == "reproducible"
        self.reproducible = self.deterministic
        self.started = time.monotonic()
        self._deterministic_spent = 0.0

    def spent(self) -> float:
        """Budget used so far, in requested seconds."""
        if self.deterministic:
            return self._deterministic_spent / self.settings.deterministic_per_second
        return time.monotonic() - self.started

    def stop_requested(self) -> bool:
        if not self.cancelled and self.should_stop():
            self.cancelled = True
        return self.cancelled

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def event(
        self,
        phase: str,
        profile: str | None = None,
        tier: int | None = None,
        objective: float | None = None,
        bound: float | None = None,
    ) -> None:
        self.on_progress(ProgressEvent(phase, profile, tier, objective, bound, self.elapsed()))

    def solve(
        self,
        builder: ScheduleModel,
        objective: cp_model.LinearExprT,
        incumbent: dict[int, Placement],
        seconds: float,
        phase: str,
        profile: str | None,
        tier: int,
        measure: Mapping[str, LinearExpr] | None = None,
    ) -> Solve:
        started = time.monotonic()
        model = builder.model
        model.minimize(objective)
        values, completion_time = builder.assignment(incumbent)
        self._deterministic_spent += completion_time
        if values is not None:
            builder.add_full_hint(values)
        else:
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
            params.interleave_batch_size = REPRODUCIBLE_BATCH_SIZE
            params.ignore_subsolvers.extend(REPRODUCIBLE_IGNORED_SUBSOLVERS)
            params.max_time_in_seconds = max(5.0, seconds * 3)
        else:
            params.max_time_in_seconds = seconds
        solver.log_callback = self.log.append

        def emit(value: float, bound: float) -> None:
            self.event(phase, profile, tier, value, bound)

        stop = threading.Event()

        def watch() -> None:
            while not stop.wait(0.5):
                if self.should_stop():
                    self.cancelled = True
                    solver.stop_search()
                    return

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        try:
            status = solver.solve(model, _Progress(emit))
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
            measured = {key: int(solver.value(expr)) for key, expr in (measure or {}).items()}
            return Solve(outcome, builder.extract(solver), measured)
        if status == cp_model.INFEASIBLE:
            # The incumbent satisfies every constraint of this model, so this cannot happen
            # unless the model is inconsistent; keep the incumbent and say so.
            logger.error("solver reported an infeasible tier", extra={"phase": phase})
            self.warnings.append(
                f"{phase}: the solver reported this tier infeasible; the previous timetable "
                "was kept for it."
            )
        outcome = TierOutcome(tier, name, None, None, elapsed, solver.deterministic_time)
        return Solve(outcome, incumbent, {})


class Engine:
    def __init__(
        self,
        context: Context,
        profiles: list[ProfileSpec],
        settings: SolveSettings,
        *,
        pins: dict[int, Placement] | None = None,
        absent: frozenset[int] = frozenset(),
        reference: dict[int, Placement] | None = None,
        hint: dict[int, Placement] | None = None,
        on_progress: Callable[[ProgressEvent], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        self.context = context
        self.profiles = profiles
        self.settings = settings
        self.pins = pins or {}
        self.absent = absent
        self.reference = reference
        self.hint = hint
        self.runner = Runner(settings, on_progress, should_stop)

    def run(self) -> EngineResult:
        runner = self.runner
        runner.started = time.monotonic()
        base = ScheduleModel(
            self.context, pins=self.pins, absent=self.absent, reference=self.reference
        )
        stats = {
            "variables": len(base.model.proto.variables),
            "constraints": len(base.model.proto.constraints),
            "sessions": len(self.context.problem.sessions),
            "conflict_sets": len(base.student_resources) + len(base.instructor_resources),
        }
        hint = (
            self.hint
            if self.hint is not None
            else construct(
                self.context, self.settings.seed, self.pins, keep=self.reference, absent=self.absent
            )
        )
        stats["hint_placed"] = len(hint)
        runner.event("model_built")

        total = self.settings.time_limit_seconds
        tier0_objective = base.tier_expression(ObjectiveConfig({}), 0)
        incumbent: dict[int, Placement] = {}
        if tier0_objective is None or isinstance(tier0_objective, int):
            tier0 = TierOutcome(0, "OPTIMAL", int(tier0_objective or 0), 0.0, 0.0, 0.0)
        elif runner.stop_requested():
            tier0 = TierOutcome(0, "UNKNOWN", None, None, 0.0, 0.0)
        else:
            first = runner.solve(
                base,
                tier0_objective,
                hint,
                max(MIN_TIER_SECONDS, total * TIER0_SHARE),
                "unscheduled",
                None,
                0,
            )
            tier0, incumbent = first.outcome, first.placements
            widened = _widened(self.context, incumbent) if tier0.value else None
            if widened is not None and not runner.stop_requested():
                # Rooms far larger than needed were left out of the search; for activities
                # left unscheduled a large room is better than no room.
                context, activities = widened
                stats["widened_activities"] = activities
                base = ScheduleModel(
                    context, pins=self.pins, absent=self.absent, reference=self.reference
                )
                tier0_objective = base.tier_expression(ObjectiveConfig({}), 0)
                if tier0_objective is not None and not isinstance(tier0_objective, int):
                    retry = runner.solve(
                        base,
                        tier0_objective,
                        incumbent,
                        max(MIN_TIER_SECONDS, total * WIDEN_SHARE),
                        "unscheduled",
                        None,
                        0,
                    )
                    if retry.outcome.value is not None:
                        tier0, incumbent = retry.outcome, retry.placements
            if tier0.value is None:
                if not runner.cancelled:
                    raise EngineError(
                        "No timetable was found within the time limit, not even a partial one. "
                        "Increase the time limit or check the validation report."
                    )
            elif tier0_objective is not None and not isinstance(tier0_objective, int):
                base.model.add(tier0_objective <= tier0.value)
        base.model.clear_hints()  # type: ignore[no-untyped-call]

        profiles: list[ProfileOutcome] = []
        for position, spec in enumerate(self.profiles):
            if runner.stop_requested():
                break
            remaining = len(self.profiles) - position
            budget = max(MIN_PROFILE_SECONDS, (total - runner.spent()) / remaining)
            profiles.append(self._run_profile(base, spec, incumbent, budget))
        return EngineResult(
            tier0=tier0,
            base=incumbent,
            profiles=profiles,
            cancelled=runner.cancelled,
            reproducible=runner.reproducible and not runner.cancelled,
            model_stats=stats,
            warnings=runner.warnings,
            log_tail=list(runner.log),
            wall_seconds=runner.elapsed(),
        )

    def _run_profile(
        self,
        base: ScheduleModel,
        spec: ProfileSpec,
        incumbent: dict[int, Placement],
        budget: float,
    ) -> ProfileOutcome:
        runner = self.runner
        builder = base.fork()
        builder.reference = spec.config.reference
        # A tier's terms are built when it is solved, so earlier tiers search a smaller model.
        tiers = [tier for tier in range(1, MAX_TIER + 1) if builder.has_terms(spec.config, tier)]
        placements = dict(incumbent)
        outcomes: list[TierOutcome] = []
        profile_started = runner.spent()
        for position, tier in enumerate(tiers):
            if runner.stop_requested():
                break
            expr = builder.tier_expression(spec.config, tier)
            if expr is None or isinstance(expr, int):
                continue
            left = budget - (runner.spent() - profile_started)
            share = max(MIN_TIER_SECONDS, left / (len(tiers) - position))
            result = runner.solve(
                builder, expr, placements, share, f"{spec.code}:tier{tier}", spec.code, tier
            )
            outcomes.append(result.outcome)
            placements = result.placements
            if result.outcome.value is not None:
                builder.model.add(expr <= result.outcome.value)
        return ProfileOutcome(spec.code, spec.name, placements, outcomes)


def _widened(context: Context, placements: dict[int, Placement]) -> tuple[Context, int] | None:
    """The context with every compatible room open to activities that have an unscheduled
    session and rooms the search skipped as far too large; None when there are none.

    Whole activities are widened, so their occurrences stay interchangeable.
    """
    p = context.problem
    activities = {
        session.activity
        for session, domain in zip(p.sessions, context.domains, strict=True)
        if session.index not in placements and len(domain.rooms) < len(domain.compatible_rooms)
    }
    if not activities:
        return None
    domains = [
        dataclasses.replace(domain, rooms=domain.compatible_rooms)
        if session.activity in activities
        else domain
        for session, domain in zip(p.sessions, context.domains, strict=True)
    ]
    return dataclasses.replace(context, domains=domains), len(activities)
