"""Why a session is not in the timetable, and where it could still go.

Every start window the session could physically use (it fits in the day and does not run
across a break) is checked against the rest of the timetable with the evaluator's own rules,
and whatever rules each window out is counted. Nothing here uses the solver (ADR 0009).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from optiedt.evaluation.evaluator import SLOT_RULES, Evaluator
from optiedt.evaluation.suggest import STATIC_ROOM_CODES, candidate_rooms
from optiedt.evaluation.types import Placement, Violation
from optiedt.problem.model import Problem

TIME_CODES = frozenset(
    {"slot_closed", "instructor_unavailable", "students_unavailable", "activity_unavailable"}
)
BUSY_CODES = frozenset({"instructor_conflict", "student_conflict", "same_day_occurrences"})
ROOM_BUSY_CODES = frozenset({"room_conflict", "room_unavailable"})


@dataclass(frozen=True, slots=True)
class Obstacle:
    """Something that rules out some of a session's start windows."""

    code: str
    """A violation code, or ``rooms_busy`` when every suitable room is taken."""
    subject: int | None
    rule_id: str | None
    windows: int
    sessions: tuple[int, ...]
    """Other sessions involved: those holding the instructor, the students or the rooms."""
    message: str


@dataclass(frozen=True, slots=True)
class Explanation:
    session: int
    windows: int
    """Start windows that fit in the day without running across a break."""
    rooms: int
    """Rooms suitable for the session (type, features, size, location); 0 if online."""
    free: tuple[Placement, ...]
    """Places where the session fits now, if any (at most ``max_free``)."""
    obstacles: tuple[Obstacle, ...]
    """What rules out the other windows, most frequent first."""
    room_problems: dict[str, int]
    """When no room suits the session: how many rooms fail each requirement."""
    summary: str


def explain(
    evaluator: Evaluator,
    placements: Mapping[int, Placement],
    s: int,
    *,
    max_free: int = 5,
) -> Explanation:
    p = evaluator.p
    session = p.sessions[s]
    online = p.activities[session.activity].online
    others = {k: v for k, v in placements.items() if k != s}
    context = evaluator.move_context(others, s)
    rooms = candidate_rooms(evaluator, s)
    windows = [
        t
        for t in range(p.n_slots)
        if p.period_of(t) + session.duration <= p.n_periods
        and all(p.joins_next[p.period_of(t) + k] for k in range(session.duration - 1))
    ]
    hits: dict[tuple[str, int | None, str | None], set[int]] = defaultdict(set)
    involved: dict[tuple[str, int | None, str | None], set[int]] = defaultdict(set)
    free: list[Placement] = []

    def note(
        key: tuple[str, int | None, str | None], window: int, sessions: tuple[int, ...]
    ) -> None:
        hits[key].add(window)
        involved[key].update(x for x in sessions if x != s)

    for t in windows:
        probe = Placement(t, rooms[0] if rooms else None)
        timing = [v for v in evaluator.placement_violations(s, probe) if _about_time(v)]
        if timing:
            for v in timing:
                note(_key(v), t, v.sessions)
            continue
        if not rooms:
            continue
        blocked_rooms: list[Violation] = []
        for room in rooms:
            violations = context.evaluate(Placement(t, room)).violations
            if not violations:
                if len(free) < max_free:
                    free.append(Placement(t, room))
                break
            people = [v for v in violations if v.code in BUSY_CODES or _is_rule(v)]
            if people:
                for v in people:
                    note(_key(v), t, v.sessions)
                break  # the same people are busy whichever room is chosen
            blocked_rooms += [v for v in violations if v.code in ROOM_BUSY_CODES]
        else:
            note(("rooms_busy", None, None), t, tuple(x for v in blocked_rooms for x in v.sessions))

    obstacles = sorted(
        (
            Obstacle(
                code,
                subject,
                rule_id,
                len(hits[(code, subject, rule_id)]),
                tuple(sorted(involved[(code, subject, rule_id)])),
                _describe(p, code, subject, rule_id, len(hits[(code, subject, rule_id)])),
            )
            for code, subject, rule_id in hits
        ),
        key=lambda o: (-o.windows, o.code, o.subject or 0),
    )
    room_problems: dict[str, int] = {}
    if not rooms and not online:
        room_problems = _room_problems(evaluator, s)
    return Explanation(
        session=s,
        windows=len(windows),
        rooms=0 if online else len(rooms),
        free=tuple(free),
        obstacles=tuple(obstacles),
        room_problems=room_problems,
        summary=_summary(p, s, len(windows), free, obstacles, room_problems, online or bool(rooms)),
    )


def _about_time(v: Violation) -> bool:
    if v.code in TIME_CODES:
        return True
    if v.code == "fixed_moved":
        return v.subject is None  # a fixed slot; a fixed room carries the room as subject
    return v.code.startswith("rule:") and _is_slot_rule(v.code)


def _is_slot_rule(code: str) -> bool:
    return code.removeprefix("rule:") in SLOT_RULES


def _is_rule(v: Violation) -> bool:
    return v.code.startswith("rule:") and not _is_slot_rule(v.code)


def _key(v: Violation) -> tuple[str, int | None, str | None]:
    if v.code.startswith("rule:"):
        return (v.code, None, v.rule_id)
    if v.code in ("student_conflict", "same_day_occurrences"):
        return (v.code, None, None)
    return (v.code, v.subject, None)


def _room_problems(evaluator: Evaluator, s: int) -> dict[str, int]:
    p = evaluator.p
    probe_slot = min(p.open_slots, default=0)
    counts: Counter[str] = Counter()
    for room in p.rooms:
        for v in evaluator.placement_violations(s, Placement(probe_slot, room.index)):
            if v.code in STATIC_ROOM_CODES:
                counts[v.code] += 1
    return dict(counts)


def _describe(p: Problem, code: str, subject: int | None, rule_id: str | None, windows: int) -> str:
    rule = next((r for r in p.rules if r.id == rule_id), None)
    if code == "slot_closed":
        text = "the institution has closed the slot"
    elif code == "instructor_unavailable" and subject is not None:
        text = f"{p.instructors[subject].name} is unavailable"
    elif code == "students_unavailable" and subject is not None:
        text = f"students of {p.groups[subject].code} are unavailable"
    elif code == "activity_unavailable":
        text = "the activity is not allowed then"
    elif code == "fixed_moved":
        text = "the session is fixed at another time"
    elif code == "instructor_conflict" and subject is not None:
        text = f"{p.instructors[subject].name} teaches another session"
    elif code == "student_conflict":
        text = "its students attend another session"
    elif code == "same_day_occurrences":
        text = "another occurrence is already on that day"
    elif code == "rooms_busy":
        text = "every suitable room is taken or closed"
    elif rule is not None and _is_slot_rule(code):
        text = f"rule '{rule.name}' keeps the periods free"
    elif rule is not None:
        text = f"rule '{rule.name}' would be broken"
    else:
        text = code
    return f"{text} ({windows} window{'s' if windows != 1 else ''})"


def _summary(
    p: Problem,
    s: int,
    windows: int,
    free: list[Placement],
    obstacles: list[Obstacle],
    room_problems: dict[str, int],
    has_room: bool,
) -> str:
    label = p.describe_session(p.sessions[s])
    if not has_room:
        reasons = ", ".join(
            f"{count} fail on {code.replace('_', ' ')}" for code, count in room_problems.items()
        )
        return f"{label} has no suitable room: of {len(p.rooms)} rooms, {reasons}."
    if free:
        first = free[0]
        where = f" in {p.rooms[first.room].code}" if first.room is not None else ""
        return f"{label} fits now, for example at {p.slot_label(first.slot)}{where}."
    if not windows:
        return f"{label} is longer than any run of periods without a break."
    reasons = "; ".join(o.message for o in obstacles[:4])
    more = f"; and {len(obstacles) - 4} other reason(s)" if len(obstacles) > 4 else ""
    return f"{label} fits nowhere. Of {windows} possible start windows: {reasons}{more}."
