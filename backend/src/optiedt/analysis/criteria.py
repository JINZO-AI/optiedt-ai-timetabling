"""Concrete Criterion implementations for S2, S3, S4, S5, S6, S7 and S10.

Formulas and bounds are recorded in docs/open-questions.md (C-4, C-12) with
the reasoning behind each choice - this module is the implementation of that
decision, not a second place to decide it. solver/objective.py encodes the
SAME seven formulas as CP-SAT expressions independently (it may not import
this module - see that file's docstring), so a change here must be mirrored
there or the objective stops optimising for what gets displayed.

Every class caches an InstanceView (and, for S6, the per-room-type target
utilisation) at construction, because Criterion.raw_value(candidate) does not
receive the instance - only bounds(instance) does. Constructing a criterion
is therefore a per-run operation, not a per-candidate one.

⚠️ Consequence of that caching: ``bounds(instance)`` IGNORES its argument and
answers from the cached InstanceView. Passing a different instance than the
one build_criteria() was given returns the wrong bounds silently. The
argument is kept only because the Criterion Protocol declares it - a
signature that deliberately makes ADR-009's rejected reading (bounds derived
from candidates) inexpressible. Build criteria per instance, per run.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from optiedt.analysis.instance_view import (
    InstanceView,
    build_instance_view,
    idle_periods,
    occupied_periods_by_day,
)
from optiedt.analysis.interfaces import Bounds, Criterion
from optiedt.domain.entities import Candidate, ConstraintCode, RoomId, SessionId
from optiedt.domain.enums import RoomType
from optiedt.domain.instance import Instance


def _placement_slots(candidate: Candidate) -> dict[SessionId, int]:
    return {p.session: p.slot for p in candidate.placements}


@dataclass(frozen=True, slots=True)
class _IdleTimeCriterion:
    """Shared shape of S2 and S3: sum of per-day idle periods over a set of
    resources, each resource's own session set given by ``sessions_by``."""

    code: ConstraintCode
    view: InstanceView
    sessions_by: dict[str, tuple[SessionId, ...]]

    def raw_value(self, candidate: Candidate) -> float:
        placements = _placement_slots(candidate)
        total = 0
        for session_ids in self.sessions_by.values():
            by_day = occupied_periods_by_day(session_ids, placements, self.view)
            total += idle_periods(by_day)
        return float(total)

    def bounds(self, instance: object) -> Bounds:
        days_open = len(self.view.days_open)
        period_span = max(0, self.view.periods_per_day - 1)
        maximum = sum(
            min(days_open, len(session_ids)) * period_span
            for session_ids in self.sessions_by.values()
        )
        return Bounds(minimum=0.0, maximum=float(maximum))


def build_s2_student_idle_time(instance: Instance, view: InstanceView) -> _IdleTimeCriterion:
    """S2 - gaps in a leaf group's day, via the ancestor-or-self chain (a TP
    subgroup's students also sit through their TD's and promotion's sessions).
    See docs/open-questions.md, C-4."""
    return _IdleTimeCriterion(code="S2", view=view, sessions_by=dict(view.sessions_for_leaf_group))


def build_s3_teacher_idle_time(instance: Instance, view: InstanceView) -> _IdleTimeCriterion:
    """S3 - same gap formula, per teacher, no hierarchy."""
    return _IdleTimeCriterion(code="S3", view=view, sessions_by=dict(view.sessions_for_teacher))


@dataclass(frozen=True, slots=True)
class S4ExtraWorkingDay:
    """Extra days a teacher is on site beyond the minimum their load needs.

    ``ClusterBusyTimesConstraint`` names no resource; teacher was chosen over
    leaf group because S3 already penalises within-day gaps for a teacher but
    not a teacher spread thinly across many low-load days - see
    docs/open-questions.md, C-4.
    """

    view: InstanceView
    code: ConstraintCode = "S4"

    def raw_value(self, candidate: Candidate) -> float:
        placements = _placement_slots(candidate)
        total = 0
        for session_ids in self.view.sessions_for_teacher.values():
            by_day = occupied_periods_by_day(session_ids, placements, self.view)
            days_used = sum(1 for periods in by_day.values() if periods)
            total_periods = sum(
                self.view.session_by_id[sid].duration_periods for sid in session_ids
            )
            min_days = math.ceil(total_periods / self.view.periods_per_day) if total_periods else 0
            total += max(0, days_used - min_days)
        return float(total)

    def bounds(self, instance: object) -> Bounds:
        days_open = len(self.view.days_open)
        maximum = 0
        for session_ids in self.view.sessions_for_teacher.values():
            total_periods = sum(
                self.view.session_by_id[sid].duration_periods for sid in session_ids
            )
            if total_periods == 0:
                continue
            min_days = math.ceil(total_periods / self.view.periods_per_day)
            maximum += max(0, days_open - min_days)
        return Bounds(minimum=0.0, maximum=float(maximum))


@dataclass(frozen=True, slots=True)
class S5TeacherPreference:
    """Proxy for a genuine preferred-window declaration (C-12, option b):
    the instance carries no preference data, so this counts sessions occupying
    period_index 0 or periods_per_day - 1 - a standard, teacher-agnostic
    convention, not a definition of any one teacher's actual preference.

    Precisely: the FIRST and LAST period INDEX of the grid, not the first and
    last OPEN period of each particular day. On the reference instance
    Saturday closes after period 2, so a Saturday session ending the day at
    period 2 is not counted while a Saturday period-0 session is. That is a
    known imprecision of the proxy, left as-is deliberately: making it
    per-day-aware would refine a placeholder whose whole purpose is to be
    replaced by real preference data (C-12 option (a)), and would have to be
    mirrored in solver/objective.py to keep the two layers agreeing.

    The alternative tested and rejected (generalising a teacher's declared
    UNAVAILABLE periods across the week) degenerates on this instance: most
    teachers' unavailability already spans nearly every period index, so it
    would flag almost every session regardless of placement. See
    docs/open-questions.md, C-12.
    """

    view: InstanceView
    code: ConstraintCode = "S5"

    def raw_value(self, candidate: Candidate) -> float:
        placements = _placement_slots(candidate)
        edge = self.view.periods_per_day - 1
        total = 0
        for session_id, start_slot in placements.items():
            session = self.view.session_by_id[session_id]
            periods = {
                self.view.slot_period[start_slot + offset]
                for offset in range(session.duration_periods)
            }
            if 0 in periods or edge in periods:
                total += 1
        return float(total)

    def bounds(self, instance: object) -> Bounds:
        return Bounds(minimum=0.0, maximum=float(len(self.view.session_by_id)))


@dataclass(frozen=True, slots=True)
class S6RoomEfficiency:
    """Deviation from a room type's own average utilisation - not
    over-capacity, which H5 already forbids (the catalogue's "dead half",
    see docs/open-questions.md, C-4)."""

    view: InstanceView
    target_by_type: dict[RoomType, float]
    code: ConstraintCode = "S6"

    def raw_value(self, candidate: Candidate) -> float:
        occupied_by_room: dict[RoomId, int] = defaultdict(int)
        for placement in candidate.placements:
            session = self.view.session_by_id[placement.session]
            occupied_by_room[placement.room] += session.duration_periods

        total = 0.0
        for room_id, room in self.view.room_by_id.items():
            utilisation = occupied_by_room.get(room_id, 0) / self.view.open_slot_count
            target = self.target_by_type.get(room.type, 0.0)
            total += abs(utilisation - target)
        return total

    def bounds(self, instance: object) -> Bounds:
        maximum = sum(
            max(
                self.target_by_type.get(room.type, 0.0),
                1.0 - self.target_by_type.get(room.type, 0.0),
            )
            for room in self.view.room_by_id.values()
        )
        return Bounds(minimum=0.0, maximum=float(maximum))


def build_s6_room_efficiency(instance: Instance, view: InstanceView) -> S6RoomEfficiency:
    demand_by_type: dict[RoomType, int] = defaultdict(int)
    for session in instance.sessions:
        demand_by_type[session.required_room_type] += session.duration_periods

    target_by_type: dict[RoomType, float] = {}
    for room_type, room_ids in view.rooms_by_type.items():
        capacity = len(room_ids) * view.open_slot_count
        target_by_type[room_type] = demand_by_type.get(room_type, 0) / capacity if capacity else 0.0

    return S6RoomEfficiency(view=view, target_by_type=target_by_type)


@dataclass(frozen=True, slots=True)
class S7SubjectSpread:
    """A leaf group seeing more than one session of the same course on the
    same day - via ancestor-or-self, so a CM (promotion), a TD (parent) and a
    TP (own) of the same course all reaching one leaf group on one day counts
    as two excess sessions. See docs/open-questions.md, C-4 for why this
    reading rather than ITC-2007's course-repetition one applies here."""

    view: InstanceView
    code: ConstraintCode = "S7"

    def raw_value(self, candidate: Candidate) -> float:
        placements = _placement_slots(candidate)
        total = 0
        for session_ids in self.view.sessions_by_leaf_group_and_course.values():
            per_day: dict[int, int] = defaultdict(int)
            for sid in session_ids:
                start_slot = placements.get(sid)
                if start_slot is None:
                    continue
                per_day[self.view.slot_day[start_slot]] += 1
            total += sum(max(0, count - 1) for count in per_day.values())
        return float(total)

    def bounds(self, instance: object) -> Bounds:
        maximum = sum(
            max(0, len(session_ids) - 1)
            for session_ids in self.view.sessions_by_leaf_group_and_course.values()
        )
        return Bounds(minimum=0.0, maximum=float(maximum))


@dataclass(frozen=True, slots=True)
class S10LunchBreak:
    """Weight 0 by default - measured and displayed, never scored - but still
    a real sub-score, since dominance considers every criterion regardless of
    weight (docs/scoring-and-explanation.md)."""

    view: InstanceView
    code: ConstraintCode = "S10"

    def raw_value(self, candidate: Candidate) -> float:
        placements = _placement_slots(candidate)
        total = 0
        for session_ids in self.view.sessions_for_leaf_group.values():
            by_day = occupied_periods_by_day(session_ids, placements, self.view)
            total += sum(
                1 for periods in by_day.values() if self.view.lunch_period_index in periods
            )
        return float(total)

    def bounds(self, instance: object) -> Bounds:
        maximum = len(self.view.leaf_groups) * len(self.view.days_open)
        return Bounds(minimum=0.0, maximum=float(maximum))


def build_criteria(instance: Instance) -> tuple[Criterion, ...]:
    """The seven Criterion objects for one instance, sharing one InstanceView.

    Construct once per run (bounds are instance-derived and stable across
    every candidate of that run, per ADR-009) and reuse across candidates.
    """
    view = build_instance_view(instance)
    return (
        build_s2_student_idle_time(instance, view),
        build_s3_teacher_idle_time(instance, view),
        S4ExtraWorkingDay(view=view),
        S5TeacherPreference(view=view),
        build_s6_room_efficiency(instance, view),
        S7SubjectSpread(view=view),
        S10LunchBreak(view=view),
    )
