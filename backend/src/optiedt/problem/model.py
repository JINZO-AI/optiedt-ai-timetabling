"""Typed, index-based view of a snapshot, shared by the solver and the evaluator.

Slots are integers ``t = day * n_periods + period``. This module only parses and indexes; it
decides nothing about feasibility or quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from functools import cached_property

from optiedt.problem.snapshot import SActivity, Snapshot, SRule


def _hhmm(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


@dataclass(frozen=True, slots=True)
class Room:
    index: int
    id: str
    code: str
    name: str | None
    capacity: int
    type_id: str
    features: frozenset[str]
    campus: int
    building_id: str
    department_id: str | None
    unavailable: frozenset[int]


@dataclass(frozen=True, slots=True)
class Instructor:
    index: int
    id: str
    code: str
    name: str
    department_id: str
    max_weekly_periods: int | None
    active: bool
    unavailable: frozenset[int]
    undesirable: frozenset[int]
    preferred: frozenset[int]


@dataclass(frozen=True, slots=True)
class Group:
    index: int
    id: str
    code: str
    name: str
    parent: int | None
    partition: str
    size: int
    department_id: str | None
    unavailable: frozenset[int]
    children: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Activity:
    index: int
    id: str
    course_id: str
    course_code: str
    course_title: str
    department_id: str
    type_code: str
    type_name: str
    label: str | None
    duration: int
    sessions: tuple[int, ...]
    different_days: bool
    online: bool
    room_type_id: str | None
    features: frozenset[str]
    min_capacity: int
    campus: int | None
    building_id: str | None
    allowed_rooms: frozenset[int]
    preferred_rooms: frozenset[int]
    avoided_rooms: frozenset[int]
    groups: tuple[int, ...]
    instructors: tuple[int, ...]
    unavailable: frozenset[int]

    @property
    def title(self) -> str:
        base = f"{self.course_code} {self.type_code}"
        return f"{base} · {self.label}" if self.label else base


@dataclass(frozen=True, slots=True)
class Session:
    index: int
    id: str
    activity: int
    occurrence: int
    duration: int
    groups: tuple[int, ...]
    instructors: tuple[int, ...]
    fixed_slot: int | None
    fixed_room: int | None


@dataclass
class Problem:
    snapshot: Snapshot
    n_days: int
    n_periods: int
    open_slots: frozenset[int]
    joins_next: tuple[bool, ...]
    penalty: dict[int, int]
    slot_times: dict[int, tuple[time, time]]
    rooms: tuple[Room, ...]
    instructors: tuple[Instructor, ...]
    groups: tuple[Group, ...]
    activities: tuple[Activity, ...]
    sessions: tuple[Session, ...]
    rules: tuple[SRule, ...]
    campus_count: int
    travel_minutes: dict[tuple[int, int], int]
    room_index: dict[str, int] = field(default_factory=dict)
    instructor_index: dict[str, int] = field(default_factory=dict)
    group_index: dict[str, int] = field(default_factory=dict)
    activity_index: dict[str, int] = field(default_factory=dict)
    session_index: dict[str, int] = field(default_factory=dict)

    # ── slots ─────────────────────────────────────────────────────────

    @property
    def n_slots(self) -> int:
        return self.n_days * self.n_periods

    def slot(self, day: int, period: int) -> int:
        return day * self.n_periods + period

    def day_of(self, slot: int) -> int:
        return slot // self.n_periods

    def period_of(self, slot: int) -> int:
        return slot % self.n_periods

    def day_slots(self, day: int) -> range:
        return range(day * self.n_periods, (day + 1) * self.n_periods)

    def slot_label(self, slot: int) -> str:
        day = self.snapshot.days[self.day_of(slot)]
        period = self.snapshot.periods[self.period_of(slot)]
        start, _ = self.slot_times[slot]
        return f"{_WEEKDAY_NAMES[day.weekday]} {period.label} ({start:%H:%M})"

    def minutes_between(self, slot: int) -> int | None:
        """Minutes from the end of ``slot`` to the start of the next period the same day."""
        if self.period_of(slot) + 1 >= self.n_periods:
            return None
        _, end = self.slot_times[slot]
        start, _ = self.slot_times[slot + 1]
        return (start.hour * 60 + start.minute) - (end.hour * 60 + end.minute)

    def total_periods(self, session: Session) -> int:
        return session.duration

    @cached_property
    def instructor_load(self) -> dict[int, int]:
        load: dict[int, int] = {}
        for session in self.sessions:
            for instructor in session.instructors:
                load[instructor] = load.get(instructor, 0) + session.duration
        return load

    def describe_session(self, session: Session) -> str:
        activity = self.activities[session.activity]
        groups = ", ".join(self.groups[g].code for g in activity.groups)
        suffix = f" #{session.occurrence}" if len(activity.sessions) > 1 else ""
        return f"{activity.title} ({groups}){suffix}"


_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def build_problem(snapshot: Snapshot) -> Problem:
    n_days = len(snapshot.days)
    n_periods = len(snapshot.periods)

    def to_slots(pairs: list[tuple[int, int]]) -> frozenset[int]:
        return frozenset(d * n_periods + p for d, p in pairs if d < n_days and p < n_periods)

    closed = {(s.day, s.period) for s in snapshot.slots if s.closed}
    open_slots = frozenset(
        d * n_periods + p for d in range(n_days) for p in range(n_periods) if (d, p) not in closed
    )
    penalty = {s.day * n_periods + s.period: s.penalty for s in snapshot.slots if s.penalty}
    overrides = {
        (s.day, s.period): (_hhmm(s.start), _hhmm(s.end))
        for s in snapshot.slots
        if s.start and s.end
    }
    slot_times = {
        d * n_periods + p.index: overrides.get((d, p.index), (_hhmm(p.start), _hhmm(p.end)))
        for d in range(n_days)
        for p in snapshot.periods
    }

    campus_index = {c.id: i for i, c in enumerate(snapshot.campuses)}
    travel: dict[tuple[int, int], int] = {}
    for a, b, minutes in snapshot.travel_minutes:
        if a in campus_index and b in campus_index:
            travel[(campus_index[a], campus_index[b])] = minutes
            travel[(campus_index[b], campus_index[a])] = minutes

    rooms = tuple(
        Room(
            index=i,
            id=r.id,
            code=r.code,
            name=r.name,
            capacity=r.capacity,
            type_id=r.type_id,
            features=frozenset(r.features),
            campus=campus_index[r.campus_id],
            building_id=r.building_id,
            department_id=r.department_id,
            unavailable=to_slots(r.unavailable),
        )
        for i, r in enumerate(snapshot.rooms)
    )
    room_index = {r.id: r.index for r in rooms}

    instructors = tuple(
        Instructor(
            index=i,
            id=x.id,
            code=x.code,
            name=x.name,
            department_id=x.department_id,
            max_weekly_periods=x.max_weekly_periods,
            active=x.active,
            unavailable=to_slots(x.unavailable),
            undesirable=to_slots(x.undesirable),
            preferred=to_slots(x.preferred),
        )
        for i, x in enumerate(snapshot.instructors)
    )
    instructor_index = {x.id: x.index for x in instructors}

    group_index = {g.id: i for i, g in enumerate(snapshot.groups)}
    children: dict[int, list[int]] = {}
    for i, g in enumerate(snapshot.groups):
        if g.parent_id is not None and g.parent_id in group_index:
            children.setdefault(group_index[g.parent_id], []).append(i)
    groups = tuple(
        Group(
            index=i,
            id=g.id,
            code=g.code,
            name=g.name,
            parent=group_index.get(g.parent_id) if g.parent_id else None,
            partition=g.partition,
            size=g.size,
            department_id=g.department_id,
            unavailable=to_slots(g.unavailable),
            children=tuple(children.get(i, ())),
        )
        for i, g in enumerate(snapshot.groups)
    )

    courses = {c.id: c for c in snapshot.courses}
    types = {t.id: t for t in snapshot.activity_types}
    sessions_by_activity: dict[str, list[int]] = {}
    for index, session in enumerate(snapshot.sessions):
        sessions_by_activity.setdefault(session.activity_id, []).append(index)

    def activity(i: int, a: SActivity) -> Activity:
        course = courses[a.course_id]
        kind = types[a.type_id]
        return Activity(
            index=i,
            id=a.id,
            course_id=a.course_id,
            course_code=course.code,
            course_title=course.title,
            department_id=course.department_id,
            type_code=kind.code,
            type_name=kind.name,
            label=a.label,
            duration=a.duration,
            sessions=tuple(sessions_by_activity.get(a.id, ())),
            different_days=a.different_days,
            online=a.online,
            room_type_id=a.room_type_id,
            features=frozenset(a.features),
            min_capacity=a.min_capacity,
            campus=campus_index.get(a.campus_id) if a.campus_id else None,
            building_id=a.building_id,
            allowed_rooms=frozenset(room_index[r] for r in a.allowed_rooms if r in room_index),
            preferred_rooms=frozenset(room_index[r] for r in a.preferred_rooms if r in room_index),
            avoided_rooms=frozenset(room_index[r] for r in a.avoided_rooms if r in room_index),
            groups=tuple(group_index[g] for g in a.group_ids if g in group_index),
            instructors=tuple(
                instructor_index[x] for x in a.instructor_ids if x in instructor_index
            ),
            unavailable=to_slots(a.unavailable),
        )

    activities = tuple(activity(i, a) for i, a in enumerate(snapshot.activities))
    activity_index = {a.id: a.index for a in activities}

    fixed_by_key = {(a.id, f.occurrence): f for a in snapshot.activities for f in a.fixed}
    sessions = []
    for index, s in enumerate(snapshot.sessions):
        parent = activities[activity_index[s.activity_id]]
        fixed = fixed_by_key.get((s.activity_id, s.occurrence))
        sessions.append(
            Session(
                index=index,
                id=s.id,
                activity=parent.index,
                occurrence=s.occurrence,
                duration=parent.duration,
                groups=parent.groups,
                instructors=parent.instructors,
                fixed_slot=fixed.day * n_periods + fixed.period if fixed else None,
                fixed_room=room_index.get(fixed.room_id) if fixed and fixed.room_id else None,
            )
        )

    return Problem(
        snapshot=snapshot,
        n_days=n_days,
        n_periods=n_periods,
        open_slots=open_slots,
        joins_next=tuple(p.joins_next for p in snapshot.periods),
        penalty=penalty,
        slot_times=slot_times,
        rooms=rooms,
        instructors=instructors,
        groups=groups,
        activities=activities,
        sessions=tuple(sessions),
        rules=tuple(snapshot.rules),
        campus_count=len(snapshot.campuses),
        travel_minutes=travel,
        room_index=room_index,
        instructor_index=instructor_index,
        group_index=group_index,
        activity_index=activity_index,
        session_index={s.id: s.index for s in sessions},
    )
