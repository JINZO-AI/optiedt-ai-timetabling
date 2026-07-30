"""Instance-derived lookups shared by every criterion in analysis/criteria.py.

Built once per Instance and cached by the criteria that need it, rather than
recomputed per criterion or per candidate - the hierarchy walk and the
session/slot indices below are the same regardless of which criterion or
which candidate is being scored.

This module may NOT import optiedt.solver (invariant 1, backend/.importlinter).
Everything here is plain domain data: Group.parent_group, Session fields,
Slot fields. The ancestor-or-self grouping mirrors what H12 does in
solver/constraints for the hard constraint, reimplemented independently here
because analysis/ is not allowed to import that code - see docs/open-questions.md,
C-4.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from optiedt.domain.entities import (
    GroupId,
    Room,
    RoomId,
    Session,
    SessionId,
    SlotIndex,
    TeacherId,
)
from optiedt.domain.enums import RoomType
from optiedt.domain.instance import Instance


@dataclass(frozen=True, slots=True)
class InstanceView:
    """Everything a Criterion needs from the Instance, precomputed once.

    Passed to every concrete Criterion's constructor (analysis/criteria.py) so
    the hierarchy walk, the slot->day/period map and the session indices are
    built exactly once per Instance, not once per criterion.
    """

    session_by_id: dict[SessionId, Session]
    room_by_id: dict[RoomId, Room]
    slot_day: dict[SlotIndex, int]
    slot_period: dict[SlotIndex, int]
    periods_per_day: int
    days_open: tuple[int, ...]
    """Distinct day_index values with at least one open slot."""
    lunch_period_index: int
    """The period_index whose slot start/end straddles 12:00 - S10."""
    leaf_groups: tuple[GroupId, ...]
    """Groups that are no other group's parent_group - the smallest student
    population units, used by S2, S7 and S10 so idle time / spread / lunch
    reflect what one population of students actually experiences."""
    sessions_for_leaf_group: dict[GroupId, tuple[SessionId, ...]]
    """Sessions belonging to a leaf group OR any of its ancestors (ancestor-or-self,
    the same relation H12 enforces as a hard constraint) - a TP subgroup's
    students also sit through their TD's and their promotion's sessions."""
    sessions_for_teacher: dict[TeacherId, tuple[SessionId, ...]]
    rooms_by_type: dict[RoomType, tuple[RoomId, ...]]
    open_slot_count: int


def _leaf_groups(instance: Instance) -> tuple[GroupId, ...]:
    parents = {g.parent_group for g in instance.groups if g.parent_group is not None}
    return tuple(g.id for g in instance.groups if g.id not in parents)


def _ancestor_chain(
    group_id: GroupId, parent_of: dict[GroupId, GroupId | None]
) -> tuple[GroupId, ...]:
    chain = []
    current: GroupId | None = group_id
    while current is not None:
        chain.append(current)
        current = parent_of.get(current)
    return tuple(chain)


def build_instance_view(instance: Instance) -> InstanceView:
    session_by_id = {s.id: s for s in instance.sessions}
    room_by_id = {r.id: r for r in instance.rooms}

    slot_day = {s.index: s.day_index for s in instance.slots}
    slot_period = {s.index: s.period_index for s in instance.slots}
    periods_per_day = max(slot_period.values()) + 1 if slot_period else 0
    days_open = tuple(sorted({s.day_index for s in instance.slots if s.is_open}))

    # The period whose slot straddles noon - derived from the data rather
    # than hardcoded, so a different calendar shifts this automatically.
    # One representative slot per period_index is enough: the reference
    # calendar repeats the same start/end hours on every day.
    noon_minutes = 12 * 60
    midpoint_by_period: dict[int, int] = {}
    for slot in instance.slots:
        start = slot.start_hour.hour * 60 + slot.start_hour.minute
        end = slot.end_hour.hour * 60 + slot.end_hour.minute
        midpoint_by_period.setdefault(slot.period_index, (start + end) // 2)
    lunch_period_index = min(
        midpoint_by_period, key=lambda p: abs(midpoint_by_period[p] - noon_minutes)
    )

    parent_of: dict[GroupId, GroupId | None] = {g.id: g.parent_group for g in instance.groups}
    leaf_groups = _leaf_groups(instance)

    sessions_by_group: dict[GroupId, list[SessionId]] = defaultdict(list)
    for session in instance.sessions:
        sessions_by_group[session.group].append(session.id)

    sessions_for_leaf_group: dict[GroupId, tuple[SessionId, ...]] = {}
    for leaf in leaf_groups:
        chain = _ancestor_chain(leaf, parent_of)
        sessions_for_leaf_group[leaf] = tuple(
            sid for ancestor in chain for sid in sessions_by_group.get(ancestor, ())
        )

    sessions_for_teacher: dict[TeacherId, list[SessionId]] = defaultdict(list)
    for session in instance.sessions:
        sessions_for_teacher[session.teacher].append(session.id)

    rooms_by_type: dict[RoomType, list[RoomId]] = defaultdict(list)
    for room in instance.rooms:
        rooms_by_type[room.type].append(room.id)

    return InstanceView(
        session_by_id=session_by_id,
        room_by_id=room_by_id,
        slot_day=slot_day,
        slot_period=slot_period,
        periods_per_day=periods_per_day,
        days_open=days_open,
        lunch_period_index=lunch_period_index,
        leaf_groups=leaf_groups,
        sessions_for_leaf_group=sessions_for_leaf_group,
        sessions_for_teacher={t: tuple(v) for t, v in sessions_for_teacher.items()},
        rooms_by_type={t: tuple(v) for t, v in rooms_by_type.items()},
        open_slot_count=sum(1 for s in instance.slots if s.is_open),
    )


def occupied_periods_by_day(
    session_ids: tuple[SessionId, ...],
    placement_by_session: dict[SessionId, SlotIndex],
    view: InstanceView,
) -> dict[int, set[int]]:
    """For a set of sessions and a candidate's placements, the periods each
    session occupies, grouped by day. Shared by S2 (leaf groups) and S3
    (teachers) - both are "gaps in a set of sessions' occupied periods,
    per day" once the resource-to-session mapping is chosen."""
    by_day: dict[int, set[int]] = defaultdict(set)
    for session_id in session_ids:
        start_slot = placement_by_session.get(session_id)
        if start_slot is None:
            continue
        session = view.session_by_id[session_id]
        for offset in range(session.duration_periods):
            slot = start_slot + offset
            by_day[view.slot_day[slot]].add(view.slot_period[slot])
    return by_day


def idle_periods(day_periods: dict[int, set[int]]) -> int:
    """Sum, over days with >=1 occupied period, of span - occupied_count."""
    total = 0
    for periods in day_periods.values():
        if not periods:
            continue
        span = max(periods) - min(periods) + 1
        total += span - len(periods)
    return total
