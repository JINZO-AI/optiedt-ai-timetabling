"""Necessary conditions for a complete timetable, checked before solving.

Every ``error`` below proves that no complete timetable exists; every ``warning`` flags a
resource so tight that the solver may leave sessions unplaced. The messages name resources
and quantities so the fix is evident.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from optiedt.problem.issues import Issue
from optiedt.problem.model import Problem
from optiedt.solver.domains import Context

TIGHT_UTILISATION = 0.9


def _reasons(counts: dict[str, int]) -> str:
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    return "; ".join(f"{reason} ({count})" for reason, count in ordered)


def precheck(context: Context) -> list[Issue]:
    issues: list[Issue] = []
    issues += _empty_domains(context)
    issues += _instructor_load(context)
    issues += _student_load(context)
    issues += _room_pools(context)
    issues += _fixed_collisions(context)
    issues += _different_days(context)
    issues += _hard_rule_loads(context)
    return sorted(issues, key=lambda i: (i.severity != "error", i.code, i.message))


def _empty_domains(context: Context) -> list[Issue]:
    problem = context.problem
    issues = []
    for session, domain in zip(problem.sessions, context.domains, strict=True):
        activity = problem.activities[session.activity]
        label = problem.describe_session(session)
        if not domain.starts:
            issues.append(
                Issue(
                    "error",
                    "no_valid_start",
                    f"{label}: no {session.duration}-period window is possible "
                    f"({_reasons(domain.start_exclusions)}).",
                    "activity",
                    (activity.id,),
                )
            )
        if not activity.online and not domain.compatible_rooms:
            issues.append(
                Issue(
                    "error",
                    "no_compatible_room",
                    f"{label}: no room fits — needs {activity.min_capacity} seats"
                    + (
                        f" of type {_type_name(problem, activity.room_type_id)}"
                        if activity.room_type_id
                        else ""
                    )
                    + f" ({_reasons(domain.room_exclusions)}).",
                    "activity",
                    (activity.id,),
                    {"seats": activity.min_capacity},
                )
            )
    return issues


def _type_name(problem: Problem, type_id: str | None) -> str:
    for room_type in problem.snapshot.room_types:
        if room_type.id == type_id:
            return room_type.name
    return "unknown"


def _instructor_load(context: Context) -> list[Issue]:
    problem = context.problem
    issues = []
    for instructor in problem.instructors:
        load = problem.instructor_load.get(instructor.index, 0)
        if not load:
            continue
        available = len(problem.open_slots - context.blocked_instructor[instructor.index])
        if load > available:
            issues.append(
                Issue(
                    "error",
                    "instructor_overbooked",
                    f"{instructor.name} must teach {load} periods but is available for only "
                    f"{available} open periods.",
                    "instructor",
                    (instructor.id,),
                    {"load": load, "available": available},
                )
            )
        elif available and load / available > TIGHT_UTILISATION:
            issues.append(
                Issue(
                    "warning",
                    "instructor_tight",
                    f"{instructor.name} teaches {load} of {available} available periods.",
                    "instructor",
                    (instructor.id,),
                    {"load": load, "available": available},
                )
            )
    return issues


def _student_load(context: Context) -> list[Issue]:
    problem = context.problem
    issues = []
    reported: set[tuple[int, ...]] = set()
    for atom, sessions in zip(context.atoms, context.atom_sessions, strict=True):
        need = sum(problem.sessions[s].duration for s in sessions)
        if not need:
            continue
        available = len(problem.open_slots - context.blocked_atom[atom.index])
        if need <= available:
            continue
        key = tuple(sorted(atom.groups))
        if key in reported:
            continue
        reported.add(key)
        groups = " / ".join(
            problem.groups[g].code
            for g in sorted(atom.groups, key=lambda g: problem.groups[g].code)
        )
        issues.append(
            Issue(
                "error",
                "students_overbooked",
                f"Students of {groups} need {need} periods of teaching but only {available} "
                "open periods are available to them.",
                "group",
                tuple(problem.groups[g].id for g in sorted(atom.groups)),
                {"need": need, "available": available},
            )
        )
    return issues


def _room_pools(context: Context) -> list[Issue]:
    """Sessions whose compatible rooms all lie in a pool cannot exceed the pool's capacity."""
    problem = context.problem
    pools: dict[frozenset[int], list[int]] = defaultdict(list)
    for session, domain in zip(problem.sessions, context.domains, strict=True):
        if domain.compatible_rooms:
            pools[frozenset(domain.compatible_rooms)].append(session.index)
    free_slots = {
        room.index: [s for s in sorted(problem.open_slots) if s not in room.unavailable]
        for room in problem.rooms
    }

    def windows(room: int, length: int) -> int:
        """Disjoint windows of ``length`` joinable open periods the room offers in a week."""
        free = set(free_slots[room])
        count = 0
        for day in range(problem.n_days):
            run = 0
            for period in range(problem.n_periods):
                slot = problem.slot(day, period)
                if slot in free:
                    run += 1
                    breaks = not problem.joins_next[period] or period == problem.n_periods - 1
                    if breaks:
                        count += run // length
                        run = 0
                else:
                    count += run // length
                    run = 0
            count += run // length
        return count

    issues = []
    for pool in sorted(pools, key=len):
        members = [s for other, sessions in pools.items() if other <= pool for s in sessions]
        demand = sum(problem.sessions[s].duration for s in members)
        supply = sum(len(free_slots[r]) for r in pool)
        rooms = ", ".join(sorted(problem.rooms[r].code for r in pool)[:6])
        more = f" and {len(pool) - 6} more" if len(pool) > 6 else ""
        if demand > supply:
            issues.append(
                Issue(
                    "error",
                    "rooms_overbooked",
                    f"{len(members)} sessions can only use {rooms}{more}: they need {demand} "
                    f"room-periods, these rooms offer {supply}.",
                    "room",
                    tuple(problem.rooms[r].id for r in pool),
                    {"demand": demand, "supply": supply},
                )
            )
            continue
        for length in sorted(
            {problem.sessions[s].duration for s in members if problem.sessions[s].duration > 1}
        ):
            needing = sum(1 for s in members if problem.sessions[s].duration >= length)
            offered = sum(windows(r, length) for r in pool)
            if needing > offered:
                issues.append(
                    Issue(
                        "error",
                        "room_windows_short",
                        f"{needing} sessions of {length}+ periods can only use {rooms}{more}, "
                        f"which offer {offered} uninterrupted {length}-period windows.",
                        "room",
                        tuple(problem.rooms[r].id for r in pool),
                        {"sessions": needing, "windows": offered},
                    )
                )
        if supply and demand / supply > TIGHT_UTILISATION:
            issues.append(
                Issue(
                    "warning",
                    "rooms_tight",
                    f"{rooms}{more}: {demand} of {supply} room-periods are needed "
                    f"({demand / supply:.0%}).",
                    "room",
                    tuple(problem.rooms[r].id for r in pool),
                    {"demand": demand, "supply": supply},
                )
            )
    return issues


def _fixed_collisions(context: Context) -> list[Issue]:
    problem = context.problem
    fixed = [
        (s, s.fixed_slot)
        for s in problem.sessions
        if s.fixed_slot is not None and context.domains[s.index].starts
    ]
    issues = []
    for (a, start_a), (b, start_b) in combinations(fixed, 2):
        span_a = set(range(start_a, start_a + a.duration))
        span_b = set(range(start_b, start_b + b.duration))
        if not span_a & span_b:
            continue
        shared = []
        if set(a.instructors) & set(b.instructors):
            shared.append("an instructor")
        if context.session_atoms[a.index] & context.session_atoms[b.index]:
            shared.append("students")
        if a.fixed_room is not None and a.fixed_room == b.fixed_room:
            shared.append(f"room {problem.rooms[a.fixed_room].code}")
        if shared:
            issues.append(
                Issue(
                    "error",
                    "fixed_collision",
                    f"{problem.describe_session(a)} and {problem.describe_session(b)} are both "
                    f"fixed at {problem.slot_label(start_a)} and share {' and '.join(shared)}.",
                    "activity",
                    (problem.activities[a.activity].id, problem.activities[b.activity].id),
                )
            )
    return issues


def _different_days(context: Context) -> list[Issue]:
    problem = context.problem
    issues = []
    for activity in problem.activities:
        if not activity.different_days or len(activity.sessions) < 2:
            continue
        days = {
            problem.day_of(start) for s in activity.sessions for start in context.domains[s].starts
        }
        if len(days) < len(activity.sessions):
            issues.append(
                Issue(
                    "error",
                    "not_enough_days",
                    f"{activity.title}: {len(activity.sessions)} sessions must be on different "
                    f"days, but only {len(days)} day(s) are possible.",
                    "activity",
                    (activity.id,),
                )
            )
    return issues


def _hard_rule_loads(context: Context) -> list[Issue]:
    problem = context.problem
    issues = []
    for rule in problem.rules:
        if rule.enforcement != "hard" or rule.type not in (
            "max_days_per_week",
            "max_periods_per_day",
        ):
            continue
        limit = int(rule.params["limit"])
        for instructor_id in rule.instructor_ids:
            index = problem.instructor_index.get(instructor_id)
            if index is None:
                continue
            load = problem.instructor_load.get(index, 0)
            if rule.type == "max_days_per_week":
                capacity = limit * problem.n_periods
                description = f"at most {limit} day(s) of {problem.n_periods} periods"
            else:
                capacity = limit * problem.n_days
                description = f"at most {limit} period(s) on each of {problem.n_days} days"
            if load > capacity:
                name = problem.instructors[index].name
                issues.append(
                    Issue(
                        "error",
                        "rule_below_load",
                        f"Rule '{rule.name}': {name} may teach {description} "
                        f"({capacity} periods) but must teach {load}.",
                        "constraint_rule",
                        (rule.id,),
                        {"load": load, "capacity": capacity},
                    )
                )
    return issues
