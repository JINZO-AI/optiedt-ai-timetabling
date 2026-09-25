from __future__ import annotations

from collections.abc import Callable

from optiedt.evaluation.evaluator import Evaluator
from optiedt.evaluation.types import Evaluation
from optiedt.problem.model import Problem
from optiedt.problem.solution import ObjectiveConfig, Placement
from optiedt.solver.domains import build_context
from optiedt.solver.engine import Engine, EngineResult, ProfileSpec, SolveSettings


def config(
    problem: Problem, code: str = "balanced", reference: dict[int, Placement] | None = None
) -> ObjectiveConfig:
    profile = next(p for p in problem.snapshot.profiles if p.code == code)
    return ObjectiveConfig.from_profile(profile, reference)


def solve(
    problem: Problem,
    profiles: tuple[str, ...] = ("balanced",),
    *,
    seconds: float = 5.0,
    pins: dict[int, Placement] | None = None,
    reference: dict[int, Placement] | None = None,
    mode: str = "reproducible",
    should_stop: Callable[[], bool] | None = None,
) -> EngineResult:
    specs = [ProfileSpec(code, code, config(problem, code, reference)) for code in profiles]
    engine = Engine(
        build_context(problem),
        specs,
        SolveSettings(mode=mode, time_limit_seconds=seconds, workers=4, seed=7),
        pins=pins,
        reference=reference,
        should_stop=should_stop,
    )
    return engine.run()


def remap(old: Problem, new: Problem, placements: dict[int, Placement]) -> dict[int, Placement]:
    """Placements of ``old`` expressed in the indices of ``new``, matched by identifiers."""
    session_index = {session.id: session.index for session in new.sessions}
    result = {}
    for s, placement in placements.items():
        target = session_index.get(old.sessions[s].id)
        if target is None:
            continue
        room = None
        if placement.room is not None:
            room = new.room_index.get(old.rooms[placement.room].id)
        result[target] = Placement(placement.slot, room)
    return result


def evaluate(
    problem: Problem,
    placements: dict[int, Placement],
    code: str = "balanced",
    reference: dict[int, Placement] | None = None,
) -> Evaluation:
    return Evaluator(problem, config(problem, code, reference)).evaluate(placements)
