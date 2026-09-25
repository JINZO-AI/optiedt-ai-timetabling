"""What the worker's child process does: solve one run from a self-contained payload.

The payload holds the snapshot and the run configuration; the result is plain JSON with
sessions, rooms and other records named by their identifiers. Nothing here touches the
database, so whatever happens inside the solver, only this process is affected.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from typing import Any

from optiedt.problem.encoding import Codec
from optiedt.problem.model import Problem, build_problem
from optiedt.problem.snapshot import Snapshot
from optiedt.problem.solution import ObjectiveConfig
from optiedt.solver.domains import build_context
from optiedt.solver.engine import Engine, EngineResult, ProfileSpec, ProgressEvent, SolveSettings
from optiedt.solver.model import invalid_pins
from optiedt.solver.relaxation import Change, Relaxation, RelaxationResult


class RunError(Exception):
    """The run cannot proceed for a reason the requester can act on."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def execute(
    payload: Mapping[str, Any],
    emit: Callable[[dict[str, Any]], None],
    should_stop: Callable[[], bool],
) -> dict[str, Any]:
    config = payload["config"]
    problem = build_problem(Snapshot.model_validate(payload["snapshot"]))
    context = build_context(problem)
    index = Codec(problem)
    settings = SolveSettings(
        mode=config["mode"],
        time_limit_seconds=float(config["time_limit_seconds"]),
        workers=int(config.get("workers", 0)),
        seed=int(config["seed"]),
    )

    def progress(event: ProgressEvent) -> None:
        emit(dataclasses.asdict(event))

    hint = index.placements(config.get("hint")) or None
    if config["kind"] == "relaxation":
        relaxation = Relaxation(
            context, settings, hint=hint, on_progress=progress, should_stop=should_stop
        )
        return _relaxation_json(index, relaxation.run())

    pins = index.placements(config.get("pins"))
    problems = invalid_pins(context, pins)
    if problems:
        raise RunError(
            "invalid_pin",
            "Some sessions that must stay in place no longer can: "
            + " ".join(problems[:5])
            + (f" ({len(problems) - 5} more)" if len(problems) > 5 else ""),
        )
    reference = index.placements(config.get("reference")) or None
    specs = [
        ProfileSpec(
            profile["code"],
            profile["name"],
            ObjectiveConfig(
                {code: (int(t), int(w)) for code, (t, w) in profile["objectives"].items()},
                reference,
            ),
        )
        for profile in config["profiles"]
    ]
    engine = Engine(
        context,
        specs,
        settings,
        pins=pins,
        absent=index.sessions(config.get("absent", [])),
        reference=reference,
        hint=hint,
        on_progress=progress,
        should_stop=should_stop,
    )
    return _engine_json(index, engine.run())


def _engine_json(index: Codec, result: EngineResult) -> dict[str, Any]:
    return {
        "kind": "engine",
        "tier0": dataclasses.asdict(result.tier0),
        "base": index.encode(result.base),
        "profiles": [
            {
                "code": outcome.code,
                "name": outcome.name,
                "placements": index.encode(outcome.placements),
                "tiers": [dataclasses.asdict(tier) for tier in outcome.tiers],
            }
            for outcome in result.profiles
        ],
        "cancelled": result.cancelled,
        "reproducible": result.reproducible,
        "model_stats": result.model_stats,
        "warnings": result.warnings,
        "log_tail": result.log_tail,
        "wall_seconds": round(result.wall_seconds, 3),
    }


SUBJECT_KINDS = {
    "instructor_unavailable": "instructor",
    "students_unavailable": "group",
    "activity_unavailable": "activity",
    "different_days": "activity",
    "slot_rule": "rule",
    "rule": "rule",
    "fixed_moved": "session",
    "room_type": "room",
    "room_features": "room",
    "room_capacity": "room",
    "room_location": "room",
    "room_not_allowed": "room",
    "oversized_room": "room",
}


def _subject_id(p: Problem, change: Change) -> str | None:
    kind = SUBJECT_KINDS.get(change.kind)
    if kind is None or change.subject is None:
        return None
    records: dict[str, Any] = {
        "instructor": p.instructors,
        "group": p.groups,
        "activity": p.activities,
        "rule": p.rules,
        "session": p.sessions,
        "room": p.rooms,
    }
    return str(records[kind][change.subject].id)


def _relaxation_json(index: Codec, result: RelaxationResult) -> dict[str, Any]:
    p = index.p
    return {
        "kind": "relaxation",
        "complete": result.complete,
        "unscheduled": [p.sessions[s].id for s in result.unscheduled],
        "total_cost": result.total_cost,
        "changes": [
            {
                "kind": change.kind,
                "cost": change.cost,
                "units": change.units,
                "sessions": [p.sessions[s].id for s in change.sessions],
                "slots": [index.slot(u) for u in change.slots],
                "subject_kind": SUBJECT_KINDS.get(change.kind),
                "subject_id": _subject_id(p, change),
                "message": change.message,
            }
            for change in result.changes
        ],
        "placements": index.encode(result.placements),
        "phases": [dataclasses.asdict(phase) for phase in result.phases],
        "cancelled": result.cancelled,
        "warnings": result.warnings,
        "log_tail": result.log_tail,
    }
