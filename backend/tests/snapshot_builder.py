"""Builds problem snapshots directly, for solver and evaluator tests that need no database."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from optiedt.problem.catalog import BUILT_IN_PROFILES
from optiedt.problem.model import Problem, build_problem
from optiedt.problem.snapshot import (
    SActivity,
    SActivityType,
    SBuilding,
    SCampus,
    SCourse,
    SDay,
    SDepartment,
    SFixed,
    SGroup,
    SInstructor,
    SNamed,
    Snapshot,
    SObjectiveSetting,
    SPeriod,
    SProfile,
    SRoom,
    SRule,
    SSession,
    SSlot,
    STerm,
    session_id,
)

Slot = tuple[int, int]


def _id(prefix: str, name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"test:{prefix}:{name}"))


@dataclass
class SnapshotBuilder:
    days: int = 5
    periods: tuple[tuple[str, str], ...] = (
        ("08:30", "10:00"),
        ("10:10", "11:40"),
        ("13:00", "14:30"),
        ("14:40", "16:10"),
    )
    joins: tuple[bool, ...] | None = None
    room_capacity_ratio: float = 4.0
    closed: list[Slot] = field(default_factory=list)
    penalties: dict[Slot, int] = field(default_factory=dict)
    _campuses: list[SCampus] = field(default_factory=list)
    _buildings: list[SBuilding] = field(default_factory=list)
    _rooms: list[SRoom] = field(default_factory=list)
    _room_types: dict[str, SNamed] = field(default_factory=dict)
    _features: dict[str, SNamed] = field(default_factory=dict)
    _instructors: list[SInstructor] = field(default_factory=list)
    _groups: list[SGroup] = field(default_factory=list)
    _courses: dict[str, SCourse] = field(default_factory=dict)
    _types: dict[str, SActivityType] = field(default_factory=dict)
    _activities: list[SActivity] = field(default_factory=list)
    _rules: list[SRule] = field(default_factory=list)
    _travel: list[tuple[str, str, int]] = field(default_factory=list)
    department_id: str = field(default_factory=lambda: _id("dept", "CS"))

    def __post_init__(self) -> None:
        self.campus("MAIN")

    # ── organisation ──────────────────────────────────────────────────

    def campus(self, code: str) -> str:
        campus_id = _id("campus", code)
        self._campuses.append(SCampus(id=campus_id, code=code, name=code))
        self._buildings.append(
            SBuilding(id=_id("building", code), code=f"B-{code}", name=code, campus_id=campus_id)
        )
        return campus_id

    def travel(self, campus_a: str, campus_b: str, minutes: int) -> None:
        a, b = sorted((_id("campus", campus_a), _id("campus", campus_b)))
        self._travel.append((a, b, minutes))

    def room_type(self, code: str) -> str:
        if code not in self._room_types:
            self._room_types[code] = SNamed(id=_id("rtype", code), code=code, name=code.title())
        return self._room_types[code].id

    def feature(self, code: str) -> str:
        if code not in self._features:
            self._features[code] = SNamed(id=_id("feature", code), code=code, name=code.title())
        return self._features[code].id

    def room(
        self,
        code: str,
        capacity: int,
        room_type: str = "CLASSROOM",
        features: tuple[str, ...] = (),
        campus: str = "MAIN",
        unavailable: list[Slot] | None = None,
    ) -> str:
        room_id = _id("room", code)
        self._rooms.append(
            SRoom(
                id=room_id,
                code=code,
                name=None,
                building_id=_id("building", campus),
                campus_id=_id("campus", campus),
                type_id=self.room_type(room_type),
                capacity=capacity,
                features=sorted(self.feature(f) for f in features),
                department_id=None,
                unavailable=unavailable or [],
            )
        )
        return room_id

    # ── people ─────────────────────────────────────────────────────────

    def instructor(
        self,
        code: str,
        unavailable: list[Slot] | None = None,
        undesirable: list[Slot] | None = None,
        preferred: list[Slot] | None = None,
        active: bool = True,
        max_weekly_periods: int | None = None,
    ) -> str:
        instructor_id = _id("instructor", code)
        self._instructors.append(
            SInstructor(
                id=instructor_id,
                code=code,
                name=f"Dr {code}",
                email=None,
                department_id=self.department_id,
                max_weekly_periods=max_weekly_periods,
                active=active,
                unavailable=unavailable or [],
                undesirable=undesirable or [],
                preferred=preferred or [],
            )
        )
        return instructor_id

    def group(
        self,
        code: str,
        size: int,
        parent: str | None = None,
        partition: str = "default",
        unavailable: list[Slot] | None = None,
    ) -> str:
        group_id = _id("group", code)
        self._groups.append(
            SGroup(
                id=group_id,
                code=code,
                name=code,
                parent_id=parent,
                partition=partition,
                size=size,
                department_id=self.department_id,
                unavailable=unavailable or [],
            )
        )
        return group_id

    # ── teaching ───────────────────────────────────────────────────────

    def activity(
        self,
        course: str,
        kind: str = "LEC",
        *,
        groups: list[str],
        instructors: list[str] | None = None,
        duration: int = 1,
        sessions: int = 1,
        room_type: str | None = "CLASSROOM",
        features: tuple[str, ...] = (),
        seats: int | None = None,
        online: bool = False,
        different_days: bool = True,
        campus: str | None = None,
        allowed_rooms: list[str] | None = None,
        preferred_rooms: list[str] | None = None,
        avoided_rooms: list[str] | None = None,
        fixed: list[tuple[int, int, int, str | None]] | None = None,
        unavailable: list[Slot] | None = None,
        label: str | None = None,
    ) -> str:
        if course not in self._courses:
            self._courses[course] = SCourse(
                id=_id("course", course),
                code=course,
                title=course,
                department_id=self.department_id,
            )
        if kind not in self._types:
            self._types[kind] = SActivityType(
                id=_id("type", kind), code=kind, name=kind, color="#445566"
            )
        activity_id = _id("activity", f"{course}:{kind}:{label}:{len(self._activities)}")
        size = sum(g.size for g in self._groups if g.id in groups)
        self._activities.append(
            SActivity(
                id=activity_id,
                course_id=self._courses[course].id,
                type_id=self._types[kind].id,
                label=label,
                duration=duration,
                sessions_per_week=sessions,
                different_days=different_days and sessions > 1,
                online=online,
                room_type_id=None if online or room_type is None else self.room_type(room_type),
                features=sorted(self.feature(f) for f in features),
                min_capacity=max(seats if seats is not None else size, 1),
                campus_id=_id("campus", campus) if campus else None,
                building_id=None,
                allowed_rooms=allowed_rooms or [],
                preferred_rooms=preferred_rooms or [],
                avoided_rooms=avoided_rooms or [],
                group_ids=groups,
                instructor_ids=instructors or [],
                unavailable=unavailable or [],
                fixed=[
                    SFixed(occurrence=o, day=d, period=p, room_id=r) for o, d, p, r in (fixed or [])
                ],
            )
        )
        return activity_id

    def rule(
        self,
        rule_type: str,
        *,
        params: dict[str, Any] | None = None,
        enforcement: str = "hard",
        tier: int = 1,
        weight: int = 1,
        instructors: list[str] | None = None,
        groups: list[str] | None = None,
        activities: list[str] | None = None,
        ordered: bool = False,
    ) -> str:
        rule_id = _id("rule", f"{rule_type}:{len(self._rules)}")
        self._rules.append(
            SRule(
                id=rule_id,
                type=rule_type,
                name=rule_type,
                enforcement=enforcement,
                tier=tier,
                weight=weight,
                params=params or {},
                instructor_ids=instructors or [],
                group_ids=groups or [],
                activity_ids=activities or [],
                ordered=ordered,
            )
        )
        return rule_id

    # ── output ─────────────────────────────────────────────────────────

    def snapshot(self) -> Snapshot:
        joins = self.joins or tuple(i < len(self.periods) - 1 for i in range(len(self.periods)))
        slots = [
            SSlot(
                day=d, period=p, closed=(d, p) in self.closed, penalty=self.penalties.get((d, p), 0)
            )
            for d, p in sorted(set(self.closed) | set(self.penalties))
        ]
        sessions = [
            SSession(id=str(session_id(a.id, k)), activity_id=a.id, occurrence=k)
            for a in self._activities
            for k in range(1, a.sessions_per_week + 1)
        ]
        return Snapshot(
            term=STerm(
                id=_id("term", "T"),
                code="TEST",
                name="Test term",
                start_date="2026-09-14",
                end_date="2027-01-22",
                timezone="UTC",
                room_capacity_ratio=self.room_capacity_ratio,
            ),
            days=[SDay(index=i, weekday=i) for i in range(self.days)],
            periods=[
                SPeriod(
                    id=_id("period", str(i)),
                    index=i,
                    label=f"P{i + 1}",
                    start=start,
                    end=end,
                    joins_next=joins[i] and i < len(self.periods) - 1,
                )
                for i, (start, end) in enumerate(self.periods)
            ],
            slots=slots,
            campuses=self._campuses,
            travel_minutes=self._travel,
            buildings=self._buildings,
            room_types=list(self._room_types.values()),
            features=list(self._features.values()),
            rooms=self._rooms,
            departments=[
                SDepartment(
                    id=self.department_id, code="CS", name="Computer Science", parent_id=None
                )
            ],
            instructors=self._instructors,
            groups=self._groups,
            courses=list(self._courses.values()),
            activity_types=list(self._types.values()),
            activities=self._activities,
            sessions=sessions,
            rules=self._rules,
            profiles=[
                SProfile(
                    code=code,
                    name=name,
                    objectives={k: SObjectiveSetting(**v) for k, v in objectives.items()},
                )
                for code, name, _, objectives in BUILT_IN_PROFILES
            ],
        )

    def problem(self) -> Problem:
        return build_problem(self.snapshot())
