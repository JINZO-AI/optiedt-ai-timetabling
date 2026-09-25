"""Where each session may start and which rooms it may use.

Domains apply every restriction that does not depend on other sessions: open slots, breaks,
unavailability of instructors, students and the activity, hard slot rules, room compatibility
and fixed placements. What was excluded, and why, is kept for explanations.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from optiedt.problem.atoms import Atom, atoms_of_groups, build_atoms
from optiedt.problem.model import Problem, Session

SLOT_RULES = ("avoid_slots", "earliest_start", "latest_end")


@dataclass(frozen=True, slots=True)
class SessionDomain:
    starts: tuple[int, ...]
    rooms: tuple[int, ...]
    """Rooms the search considers (compatible rooms, minus far-too-large ones)."""
    compatible_rooms: tuple[int, ...]
    start_exclusions: dict[str, int] = field(default_factory=dict)
    room_exclusions: dict[str, int] = field(default_factory=dict)


@dataclass
class Context:
    """Precomputed structure of one problem, shared by the model and the pre-checks."""

    problem: Problem
    atoms: list[Atom]
    session_atoms: list[frozenset[int]]
    atom_sessions: list[list[int]]
    blocked_instructor: list[frozenset[int]]
    blocked_atom: list[frozenset[int]]
    blocked_activity: list[frozenset[int]]
    domains: list[SessionDomain]

    def covers(self, session: Session, start: int) -> range:
        return range(start, start + session.duration)


def rule_slots(problem: Problem, rule_type: str, params: dict[str, Any]) -> frozenset[int]:
    """Slots a slot rule (avoid, earliest start, latest end) keeps free."""
    if rule_type == "avoid_slots":
        return frozenset(
            problem.slot(int(d), int(p))
            for d, p in params.get("slots", [])
            if int(d) < problem.n_days and int(p) < problem.n_periods
        )
    period = int(params["period"])
    if rule_type == "earliest_start":
        periods = range(0, period)
    else:
        periods = range(period + 1, problem.n_periods)
    return frozenset(problem.slot(d, p) for d in range(problem.n_days) for p in periods)


def build_context(problem: Problem) -> Context:
    atoms = build_atoms(problem)
    group_atoms = atoms_of_groups(atoms, len(problem.groups))
    session_atoms = [
        frozenset().union(*(group_atoms[g] for g in s.groups)) if s.groups else frozenset()
        for s in problem.sessions
    ]
    atom_sessions: list[list[int]] = [[] for _ in atoms]
    for session, members in zip(problem.sessions, session_atoms, strict=True):
        for atom in members:
            atom_sessions[atom].append(session.index)

    blocked_instructor = [set(i.unavailable) for i in problem.instructors]
    blocked_atom: list[set[int]] = [set() for _ in atoms]
    for group in problem.groups:
        for atom in group_atoms[group.index]:
            blocked_atom[atom] |= group.unavailable
    blocked_activity = [set(a.unavailable) for a in problem.activities]

    for rule in problem.rules:
        if rule.type not in SLOT_RULES or rule.enforcement != "hard":
            continue
        slots = rule_slots(problem, rule.type, rule.params)
        for instructor_id in rule.instructor_ids:
            if instructor_id in problem.instructor_index:
                blocked_instructor[problem.instructor_index[instructor_id]] |= slots
        for group_id in rule.group_ids:
            if group_id in problem.group_index:
                for atom in group_atoms[problem.group_index[group_id]]:
                    blocked_atom[atom] |= slots
        for activity_id in rule.activity_ids:
            if activity_id in problem.activity_index:
                blocked_activity[problem.activity_index[activity_id]] |= slots

    context = Context(
        problem=problem,
        atoms=atoms,
        session_atoms=session_atoms,
        atom_sessions=atom_sessions,
        blocked_instructor=[frozenset(b) for b in blocked_instructor],
        blocked_atom=[frozenset(b) for b in blocked_atom],
        blocked_activity=[frozenset(b) for b in blocked_activity],
        domains=[],
    )
    context.domains = [_domain(context, s) for s in problem.sessions]
    return context


def _domain(context: Context, session: Session) -> SessionDomain:
    problem = context.problem
    activity = problem.activities[session.activity]
    blocked = context.blocked_activity[session.activity].union(
        *(context.blocked_instructor[i] for i in session.instructors),
        *(context.blocked_atom[a] for a in context.session_atoms[session.index]),
    )
    exclusions: Counter[str] = Counter()
    starts: list[int] = []
    for day in range(problem.n_days):
        for period in range(problem.n_periods):
            reason = _start_blocker(context, session, day, period, blocked)
            if reason is None:
                starts.append(problem.slot(day, period))
            else:
                exclusions[reason] += 1

    if session.fixed_slot is not None:
        if session.fixed_slot in starts:
            starts = [session.fixed_slot]
        else:
            exclusions["the fixed placement itself is not a valid start"] += 1
            starts = []

    compatible, room_reasons = _compatible_rooms(problem, session)
    rooms = compatible
    if not activity.online and compatible:
        limit = problem.snapshot.term.room_capacity_ratio * activity.min_capacity
        pruned = tuple(r for r in compatible if problem.rooms[r].capacity <= limit)
        if pruned:
            rooms = pruned
    return SessionDomain(
        starts=tuple(starts),
        rooms=rooms,
        compatible_rooms=compatible,
        start_exclusions=dict(exclusions),
        room_exclusions=room_reasons,
    )


def _start_blocker(
    context: Context, session: Session, day: int, period: int, blocked: frozenset[int]
) -> str | None:
    problem = context.problem
    if period + session.duration > problem.n_periods:
        return "the session would run past the last period"
    for k in range(session.duration):
        slot = problem.slot(day, period + k)
        if slot not in problem.open_slots:
            return "a slot is closed"
        if k < session.duration - 1 and not problem.joins_next[period + k]:
            return "the session would run across a break"
        if slot in blocked:
            return _blocked_reason(context, session, slot)
    return None


def _blocked_reason(context: Context, session: Session, slot: int) -> str:
    problem = context.problem
    for instructor in session.instructors:
        if slot in context.blocked_instructor[instructor]:
            return f"{problem.instructors[instructor].name} is unavailable"
    if slot in context.blocked_activity[session.activity]:
        return "the activity is not allowed then"
    return "students are unavailable"


def _compatible_rooms(problem: Problem, session: Session) -> tuple[tuple[int, ...], dict[str, int]]:
    activity = problem.activities[session.activity]
    if activity.online:
        return (), {}
    reasons: Counter[str] = Counter()
    result = []
    for room in problem.rooms:
        if session.fixed_room is not None and room.index != session.fixed_room:
            reasons["not the fixed room"] += 1
            continue
        if activity.room_type_id and room.type_id != activity.room_type_id:
            reasons["wrong room type"] += 1
            continue
        if not activity.features <= room.features:
            reasons["missing a required feature"] += 1
            continue
        if room.capacity < activity.min_capacity:
            reasons["too small"] += 1
            continue
        if activity.campus is not None and room.campus != activity.campus:
            reasons["on another campus"] += 1
            continue
        if activity.building_id and room.building_id != activity.building_id:
            reasons["in another building"] += 1
            continue
        if activity.allowed_rooms and room.index not in activity.allowed_rooms:
            reasons["not an allowed room"] += 1
            continue
        result.append(room.index)
    return tuple(result), dict(reasons)
