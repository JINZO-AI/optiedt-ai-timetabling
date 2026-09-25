"""Ranked places for one session: valid options by quality, blocked options with reasons."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from optiedt.evaluation.evaluator import Evaluator
from optiedt.evaluation.types import Placement, Violation

STATIC_ROOM_CODES = frozenset(
    {"room_type", "room_features", "room_capacity", "campus", "building", "room_not_allowed"}
)


@dataclass(frozen=True, slots=True)
class Option:
    placement: Placement
    violations: tuple[Violation, ...]
    tier_deltas: tuple[int, ...]
    objective_deltas: dict[str, int]
    is_current: bool

    @property
    def feasible(self) -> bool:
        return not self.violations


def candidate_rooms(evaluator: Evaluator, s: int) -> list[int | None]:
    """Rooms whose type, features, capacity and location suit the session."""
    p = evaluator.p
    session = p.sessions[s]
    if p.activities[session.activity].online:
        return [None]
    probe_slot = next(iter(sorted(p.open_slots)), 0)
    rooms: list[int | None] = []
    for room in p.rooms:
        found = evaluator.placement_violations(s, Placement(probe_slot, room.index))
        if not any(v.code in STATIC_ROOM_CODES for v in found):
            rooms.append(room.index)
    return rooms


def options_for(
    evaluator: Evaluator,
    placements: Mapping[int, Placement],
    s: int,
    *,
    slots: list[int] | None = None,
) -> list[Option]:
    """Every combination of start slot and suitable room, evaluated against the rest."""
    p = evaluator.p
    session = p.sessions[s]
    context = evaluator.move_context(placements, s)
    current = placements.get(s)
    starts = (
        slots
        if slots is not None
        else [t for t in range(p.n_slots) if p.period_of(t) + session.duration <= p.n_periods]
    )
    results = []
    for room in candidate_rooms(evaluator, s):
        for slot in starts:
            placement = Placement(slot, room)
            outcome = context.evaluate(placement)
            results.append(
                Option(
                    placement=placement,
                    violations=tuple(outcome.violations),
                    tier_deltas=tuple(outcome.tier_deltas),
                    objective_deltas=outcome.objective_deltas,
                    is_current=placement == current,
                )
            )
    return results


def rank(options: list[Option]) -> tuple[list[Option], list[Option]]:
    """Valid options best first (lexicographic tier change); blocked ones fewest problems first."""
    valid = sorted(
        (o for o in options if o.feasible),
        key=lambda o: (o.tier_deltas, o.objective_deltas.get("room_fit", 0), o.placement.slot),
    )
    blocked = sorted(
        (o for o in options if not o.feasible),
        key=lambda o: (len(o.violations), o.placement.slot, o.placement.room or -1),
    )
    return valid, blocked
