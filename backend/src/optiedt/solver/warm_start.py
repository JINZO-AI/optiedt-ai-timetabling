"""A constructive greedy warm-start for CP-SAT (C-13, docs/open-questions.md).

Neither the per-room encoding nor the cumulative reformulation resolved the
room-assignment search difficulty alone (docs/status.md, 2026-07-30): both
returned UNKNOWN after minutes of tuned search on the real instance. CP-SAT
is typically far faster at VERIFYING a supplied candidate assignment than
at FINDING one from an empty state, so this builds one full, hard-constraint
-respecting timetable by hand - a classical constructive scheduling
heuristic, not a solver - and engine.py feeds it to CP-SAT via
model.add_hint() before searching.

This is a heuristic, not a guarantee, and on the reference instance it does
NOT reach a complete placement: pure most-constrained-variable-first (MRV)
ordering gets stuck after only 26 of 218 sessions, and thousands of
randomised restarts plateau around 190/218 (measured 2026-07-30). A
first-fit greedy with no backtracking simply isn't clever enough to finish
this particular near-critical instance. Rather than discard that, this
returns the BEST PARTIAL placement found across all attempts - a hint that
covers most sessions is still a real head start for CP-SAT, which only
then has to search over the uncovered remainder rather than the whole
schedule from nothing. Never treat a partial (or even a failed) result as
evidence about the instance's true feasibility - only CP-SAT's own
INFEASIBLE status means that; this is a construction heuristic, not a
decision procedure. It reuses variables.py's own domain-computation
helpers (valid_starts, candidate_rooms_for_session, ...) rather than
recomputing H4/H5/H6/H8/H9 pruning logic a second time.

The construction order is most-constrained-variable-first (MRV, "fail
first") on the first attempt, then a bounded number of randomised
restarts, each seeded deterministically from its own attempt index (so the
whole process stays reproducible for a fixed instance and seed - ADR-011).
Room choice within an attempt is first-fit among candidates in a fixed
canonical order - a least-loaded selection was tried and measured worse
(175/218 best vs. 192/218 for first-fit, same restart budget), so it was
not kept.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from optiedt.domain.entities import GroupId, RoomId, Session, SessionId, SlotIndex
from optiedt.domain.instance import Instance
from optiedt.solver.interfaces import SolverInput
from optiedt.solver.variables import (
    candidate_rooms_for_session,
    day_of,
    open_slot_map,
    unavailable_by_teacher,
    valid_starts,
)


@dataclass(frozen=True, slots=True)
class WarmStart:
    """A hard-constraint-respecting placement for SOME OR ALL sessions.

    ``covered`` sessions are exactly the keys present in both ``start`` and
    ``room`` - callers must only hint those, never assume every session in
    the instance is present."""

    start: dict[SessionId, SlotIndex]
    room: dict[SessionId, RoomId]

    @property
    def covered(self) -> frozenset[SessionId]:
        return frozenset(self.start)


def _group_relatives(instance: Instance) -> dict[GroupId, frozenset[GroupId]]:
    """For H12: every group's self + ancestors + descendants - the full set
    of groups whose sessions could conflict with a session on this group.
    H12's relation is ancestor-or-self, checked symmetrically across the
    whole forest (solver/constraints/overlap.py's H12), so from any single
    group's point of view it must be checked against ancestors AND
    descendants, not ancestors alone."""
    parent_of = {g.id: g.parent_group for g in instance.groups}
    children_of: dict[GroupId, list[GroupId]] = {g.id: [] for g in instance.groups}
    for g in instance.groups:
        if g.parent_group is not None:
            children_of.setdefault(g.parent_group, []).append(g.id)

    def ancestors(group_id: GroupId) -> set[GroupId]:
        result: set[GroupId] = set()
        current = parent_of.get(group_id)
        while current is not None:
            result.add(current)
            current = parent_of.get(current)
        return result

    def descendants(group_id: GroupId) -> set[GroupId]:
        result: set[GroupId] = set()
        stack = list(children_of.get(group_id, ()))
        while stack:
            g = stack.pop()
            result.add(g)
            stack.extend(children_of.get(g, ()))
        return result

    return {g.id: frozenset({g.id} | ancestors(g.id) | descendants(g.id)) for g in instance.groups}


def _session_domains(
    request: SolverInput,
) -> dict[SessionId, tuple[list[SlotIndex], tuple[RoomId, ...]]]:
    instance = request.instance
    all_slots = sorted(s.index for s in instance.slots)
    is_open = open_slot_map(instance)
    day_by_slot = day_of(instance)
    unavailable_map = unavailable_by_teacher(instance)
    group_size_by_id = {g.id: g.size for g in instance.groups}

    excluded_starts_by_session: dict[SessionId, set[SlotIndex]] = {}
    excluded_rooms_by_session: dict[SessionId, set[RoomId]] = {}
    for session_id, slot_index in request.excluded_slots:
        excluded_starts_by_session.setdefault(session_id, set()).add(slot_index)
    for session_id, room_id in request.excluded_rooms:
        excluded_rooms_by_session.setdefault(session_id, set()).add(room_id)

    domains: dict[SessionId, tuple[list[SlotIndex], tuple[RoomId, ...]]] = {}
    for session in instance.sessions:
        starts = valid_starts(
            session,
            all_slots,
            is_open,
            day_by_slot,
            unavailable_map.get(session.teacher, frozenset()),
            frozenset(excluded_starts_by_session.get(session.id, ())),
        )
        rooms = candidate_rooms_for_session(
            session,
            instance,
            group_size_by_id,
            frozenset(excluded_rooms_by_session.get(session.id, ())),
        )
        domains[session.id] = (starts, rooms)
    return domains


def _attempt(
    order: list[Session],
    domains: dict[SessionId, tuple[list[SlotIndex], tuple[RoomId, ...]]],
    relatives: dict[GroupId, frozenset[GroupId]],
) -> WarmStart:
    """Greedy, no backtracking: places sessions in ``order`` until either
    all are placed or one gets stuck. Always returns whatever it managed -
    a full WarmStart if every session was placed, a partial one otherwise.
    Never raises and never signals failure by itself; build_warm_start
    compares coverage across attempts to pick the best one."""
    start: dict[SessionId, SlotIndex] = {}
    room: dict[SessionId, RoomId] = {}
    teacher_busy: dict[str, set[int]] = {}
    group_busy: dict[GroupId, set[int]] = {}
    room_busy: dict[RoomId, set[int]] = {}

    for session in order:
        starts, rooms = domains[session.id]
        span_len = session.duration_periods
        relative_groups = relatives[session.group]
        placed = False

        for slot in starts:
            span = set(range(slot, slot + span_len))
            if not teacher_busy.get(session.teacher, set()).isdisjoint(span):
                continue
            if any(not group_busy.get(g, set()).isdisjoint(span) for g in relative_groups):
                continue
            for room_id in rooms:
                if room_busy.get(room_id, set()).isdisjoint(span):
                    start[session.id] = slot
                    room[session.id] = room_id
                    teacher_busy.setdefault(session.teacher, set()).update(span)
                    group_busy.setdefault(session.group, set()).update(span)
                    room_busy.setdefault(room_id, set()).update(span)
                    placed = True
                    break
            if placed:
                break

        if not placed:
            break

    return WarmStart(start=start, room=room)


def build_warm_start(request: SolverInput, attempts: int = 3000) -> WarmStart:
    """Try MRV order first, then a bounded number of deterministic random
    restarts, keeping whichever attempt covers the most sessions. Stops
    early if an attempt covers every session. Measured on the reference
    instance (2026-07-30): MRV alone covers only 26/218; thousands of
    random restarts plateau around 190/218 - a complete placement is not
    reached, but the best partial result is still returned and is still
    worth hinting to CP-SAT (see the module docstring)."""
    domains = _session_domains(request)
    relatives = _group_relatives(request.instance)
    sessions = list(request.instance.sessions)
    total = len(sessions)

    def domain_size(session: Session) -> int:
        starts, rooms = domains[session.id]
        return len(starts) * max(len(rooms), 1)

    mrv_order = sorted(sessions, key=lambda s: (domain_size(s), s.id))
    best = _attempt(mrv_order, domains, relatives)
    if len(best.covered) == total:
        return best

    for attempt_index in range(1, attempts):
        rng = random.Random(f"{request.seed}-{attempt_index}")
        shuffled = list(sessions)
        rng.shuffle(shuffled)
        candidate = _attempt(shuffled, domains, relatives)
        if len(candidate.covered) > len(best.covered):
            best = candidate
        if len(best.covered) == total:
            break

    return best
