"""A fast greedy timetable used as the solver's starting point.

Pinned placements come first, then every placement of ``keep`` (the reference timetable of a
repair) that is still valid on its own and clashes with nothing kept so far. The remaining
sessions go in order of fewest options; each takes the first start and smallest suitable room
that clash with nothing placed so far. Hard rules beyond the structural ones are left to the
solver, which repairs the hint where it has to.
"""

from __future__ import annotations

import random

from optiedt.problem.solution import Placement
from optiedt.solver.domains import Context


def construct(
    context: Context,
    seed: int,
    pins: dict[int, Placement] | None = None,
    keep: dict[int, Placement] | None = None,
) -> dict[int, Placement]:
    p = context.problem
    rng = random.Random(seed)  # noqa: S311 - reproducible tie-breaking, not security
    instructor_busy = [0] * len(p.instructors)
    atom_busy = [0] * len(context.atoms)
    room_busy = [sum(1 << u for u in room.unavailable) for room in p.rooms]
    activity_days: list[set[int]] = [set() for _ in p.activities]
    starts = [frozenset(domain.starts) for domain in context.domains]
    placements: dict[int, Placement] = {}

    def mask(start: int, duration: int) -> int:
        return ((1 << duration) - 1) << start

    def people_busy(s: int) -> int:
        busy = 0
        for i in p.sessions[s].instructors:
            busy |= instructor_busy[i]
        for a in context.session_atoms[s]:
            busy |= atom_busy[a]
        return busy

    def occupy(s: int, placement: Placement) -> None:
        session = p.sessions[s]
        bits = mask(placement.slot, session.duration)
        for i in session.instructors:
            instructor_busy[i] |= bits
        for a in context.session_atoms[s]:
            atom_busy[a] |= bits
        if placement.room is not None:
            room_busy[placement.room] |= bits
        activity_days[session.activity].add(p.day_of(placement.slot))
        placements[s] = placement

    def fits(s: int, placement: Placement) -> bool:
        session = p.sessions[s]
        activity = p.activities[session.activity]
        if placement.slot not in starts[s]:
            return False
        bits = mask(placement.slot, session.duration)
        if people_busy(s) & bits:
            return False
        if activity.different_days and p.day_of(placement.slot) in activity_days[session.activity]:
            return False
        if activity.online:
            return placement.room is None
        return (
            placement.room is not None
            and placement.room in context.domains[s].compatible_rooms
            and not room_busy[placement.room] & bits
        )

    for s, placement in (pins or {}).items():
        occupy(s, placement)
    for s, placement in sorted((keep or {}).items()):
        if s not in placements and 0 <= s < len(p.sessions) and fits(s, placement):
            occupy(s, placement)

    def difficulty(s: int) -> tuple[int, int, int, float]:
        domain = context.domains[s]
        options = len(domain.starts) * max(1, len(domain.rooms))
        activity = p.activities[p.sessions[s].activity]
        return (options, -p.sessions[s].duration, -activity.min_capacity, rng.random())

    order = sorted((s.index for s in p.sessions if s.index not in placements), key=difficulty)
    for s in order:
        session = p.sessions[s]
        domain = context.domains[s]
        activity = p.activities[session.activity]
        people = people_busy(s)
        rooms = sorted(domain.rooms, key=lambda r: (p.rooms[r].capacity, r))
        candidates = list(domain.starts)
        rng.shuffle(candidates)
        candidates.sort(key=lambda t: p.day_of(t) in activity_days[session.activity])
        for start in candidates:
            bits = mask(start, session.duration)
            if people & bits:
                continue
            if activity.different_days and p.day_of(start) in activity_days[session.activity]:
                continue
            if activity.online:
                occupy(s, Placement(start, None))
                break
            room = next((r for r in rooms if not room_busy[r] & bits), None)
            if room is not None:
                occupy(s, Placement(start, room))
                break
    return placements
