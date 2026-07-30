"""The soft-criteria objective: minimise sum(weight_i * violations_i).

Encodes the SAME seven formulas analysis/criteria.py scores candidates
against after the fact (S2, S3, S4, S5, S6, S7, S10 - see
docs/open-questions.md, C-4, for the formulas and the reasoning behind each
one), but as CP-SAT linear expressions over decision variables rather than
arithmetic over a realized Candidate's placements.

This module may NOT import optiedt.analysis. docs/architecture.md's module
map states the solver depends only on domain, and that the decision layer
"may not read a score" - so this builds its own hierarchy/day-period lookups
from Instance data rather than sharing analysis/instance_view.py's, and
weights the objective by the profile's RAW weights, never by a
normalisation range: normalisation (min_i, max_i) is an analysis/-only
concept, computed after the fact for scoring, ranking and the decomposition
that gets displayed. Minimising sum(weight_i * v_i) is not the same
optimisation target as maximising the displayed score unless every
criterion happens to share the same (max_i - min_i) range - it does not, and
the specification's own wording ("minimise sum(weight_i * violations_i)",
constraint-model.md) says raw weights, not normalised ones. Solving under
one profile's objective and displaying scores under the run's weights in
force are deliberately two different, independently-correct computations -
see analysis/ranking.py's module docstring for why scoring needs a single
shared weight vector across candidates while the solver needs whatever
profile is steering that particular solve.

⚠️ S6 (room efficiency) cannot be fully encoded here. It needs PER-ROOM
occupancy, but for "fully interchangeable" room types (Variables.
cumulative_room_types - Amphi, Lab_Info, Lab_Sciences on the reference
instance, C-13) the model has no per-room decision variable at all: which
specific room a session lands in is decided AFTER solving, by the
deterministic left-edge labeller in solver/engine.py, which the objective
cannot see or influence. S6's CP-SAT term therefore only covers
non-cumulative types (Salle on the reference instance, where
Variables.assign genuinely exists per room). analysis/criteria.py still
scores S6 correctly for every room after the fact, against whatever the
labeller produced - only the SOLVER's ability to optimise for it is
limited to non-cumulative types. This is a structural consequence of the
C-13 room-assignment split, not an oversight, and closing it would mean
changing solver/variables.py, which is out of scope here.

Weights are scaled to integers before being used as CP-SAT objective
coefficients (_WEIGHT_SCALE) rather than relying on the solver's own
float-to-integer handling, for the same reproducibility reason ADR-011
gives for avoiding wall-clock time limits: this project prefers an explicit,
documented, deterministic conversion over an implicit one.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from ortools.sat.python import cp_model

from optiedt.domain.entities import (
    ConstraintCode,
    GroupId,
    RoomId,
    Session,
    SessionId,
    SlotIndex,
    TeacherId,
)
from optiedt.domain.enums import RoomType
from optiedt.domain.instance import Instance
from optiedt.solver.occupancy import Occupancy
from optiedt.solver.variables import Variables

_WEIGHT_SCALE = 1_000_000


def _scaled(weight: float) -> int:
    return round(weight * _WEIGHT_SCALE)


@dataclass(frozen=True, slots=True)
class _ObjectiveView:
    """Solver-side equivalent of analysis/instance_view.py's InstanceView -
    duplicated rather than shared, because this package may not import
    analysis (see module docstring)."""

    session_by_id: dict[SessionId, Session]
    slot_day: dict[SlotIndex, int]
    slot_by_day_period: dict[tuple[int, int], SlotIndex]
    periods_per_day: int
    days_open: tuple[int, ...]
    lunch_period_index: int
    sessions_for_leaf_group: dict[GroupId, tuple[SessionId, ...]]
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


def _build_view(instance: Instance) -> _ObjectiveView:
    session_by_id = {s.id: s for s in instance.sessions}
    slot_day = {s.index: s.day_index for s in instance.slots}
    slot_period = {s.index: s.period_index for s in instance.slots}
    slot_by_day_period = {(s.day_index, s.period_index): s.index for s in instance.slots}
    periods_per_day = max(slot_period.values()) + 1 if slot_period else 0
    days_open = tuple(sorted({s.day_index for s in instance.slots if s.is_open}))

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

    return _ObjectiveView(
        session_by_id=session_by_id,
        slot_day=slot_day,
        slot_by_day_period=slot_by_day_period,
        periods_per_day=periods_per_day,
        days_open=days_open,
        lunch_period_index=lunch_period_index,
        sessions_for_leaf_group=sessions_for_leaf_group,
        sessions_for_teacher={t: tuple(v) for t, v in sessions_for_teacher.items()},
        rooms_by_type={t: tuple(v) for t, v in rooms_by_type.items()},
        open_slot_count=sum(1 for s in instance.slots if s.is_open),
    )


@dataclass(frozen=True, slots=True)
class _DailyOccupancy:
    """occ_vars[(resource, day)][period] is 1 iff that resource occupies that
    period on that day; any_occupied[(resource, day)] is 1 iff any period
    that day is occupied. Shared by S2/S3 (idle time) and S4 (extra working
    day), which both start from "is this resource busy at this (day, period)"."""

    occ_vars: dict[tuple[str, int], list[cp_model.IntVar]]
    any_occupied: dict[tuple[str, int], cp_model.IntVar]


def _build_daily_occupancy(
    model: cp_model.CpModel,
    occupancy: Occupancy,
    view: _ObjectiveView,
    sessions_by_resource: dict[str, tuple[SessionId, ...]],
    label: str,
) -> _DailyOccupancy:
    occ_vars: dict[tuple[str, int], list[cp_model.IntVar]] = {}
    any_occupied: dict[tuple[str, int], cp_model.IntVar] = {}
    periods = range(view.periods_per_day)

    for resource_id, session_ids in sessions_by_resource.items():
        if not session_ids:
            continue
        for day in view.days_open:
            per_period = []
            for period in periods:
                slot = view.slot_by_day_period.get((day, period))
                sources = (
                    [
                        occupancy.occupies[(sid, slot)]
                        for sid in session_ids
                        if (sid, slot) in occupancy.occupies
                    ]
                    if slot is not None
                    else []
                )
                occ_var = model.new_bool_var(f"occ[{label},{resource_id},{day},{period}]")
                if sources:
                    model.add(occ_var == cp_model.LinearExpr.sum(sources))
                else:
                    model.add(occ_var == 0)
                per_period.append(occ_var)
            occ_vars[(resource_id, day)] = per_period

            any_var = model.new_bool_var(f"any[{label},{resource_id},{day}]")
            model.add(cp_model.LinearExpr.sum(per_period) >= 1).only_enforce_if(any_var)
            model.add(cp_model.LinearExpr.sum(per_period) == 0).only_enforce_if(any_var.negated())
            any_occupied[(resource_id, day)] = any_var

    return _DailyOccupancy(occ_vars=occ_vars, any_occupied=any_occupied)


def _idle_time_terms(
    model: cp_model.CpModel, daily: _DailyOccupancy, periods_per_day: int, weight: float
) -> list[cp_model.LinearExprT]:
    """S2 and S3: sum(span - occupied_count) over days a resource is used.

    Only the "loose" inequalities (first <= every occupied period, last >=
    every occupied period) are posted. Because idle is being MINIMISED and
    these two free variables appear nowhere else, the optimum pushes first up
    and last down to exactly the true min/max occupied period - the standard
    way to encode "first/last occupied index" without an equality
    constraint. See this module's docstring for why an equality is not
    needed here.
    """
    scale = _scaled(weight)
    if scale == 0:
        return []

    terms: list[cp_model.LinearExprT] = []
    for key, occ_vars in daily.occ_vars.items():
        any_var = daily.any_occupied[key]
        first = model.new_int_var(0, periods_per_day - 1, f"first[{key}]")
        last = model.new_int_var(0, periods_per_day - 1, f"last[{key}]")
        for period, occ_var in enumerate(occ_vars):
            model.add(first <= period).only_enforce_if(occ_var)
            model.add(last >= period).only_enforce_if(occ_var)

        idle = model.new_int_var(0, periods_per_day, f"idle[{key}]")
        occupied_count = cp_model.LinearExpr.sum(occ_vars)
        model.add(idle == last - first + 1 - occupied_count).only_enforce_if(any_var)
        model.add(idle == 0).only_enforce_if(any_var.negated())
        terms.append(scale * idle)
    return terms


def _extra_working_day_terms(
    model: cp_model.CpModel, daily: _DailyOccupancy, view: _ObjectiveView, weight: float
) -> list[cp_model.LinearExprT]:
    """S4: days_used(t) - ceil(total_periods(t) / P), per teacher.

    days_used(t)*P >= total_periods(t) holds for ANY feasible placement (a
    teacher cannot occupy more than P periods on a day they are used, and
    H1 forbids double-booking), so this difference is always >= 0 and no
    max(0, ...) reification is needed - matching the same proof in
    analysis/criteria.py's S4ExtraWorkingDay.
    """
    scale = _scaled(weight)
    if scale == 0:
        return []

    days_used_by_resource: dict[str, list[cp_model.IntVar]] = defaultdict(list)
    for (resource_id, _day), any_var in daily.any_occupied.items():
        days_used_by_resource[resource_id].append(any_var)

    terms: list[cp_model.LinearExprT] = []
    for resource_id, session_ids in view.sessions_for_teacher.items():
        any_vars = days_used_by_resource.get(resource_id)
        if not any_vars:
            continue
        total_periods = sum(view.session_by_id[sid].duration_periods for sid in session_ids)
        min_days = math.ceil(total_periods / view.periods_per_day) if total_periods else 0
        days_used_expr = cp_model.LinearExpr.sum(any_vars)
        extra = model.new_int_var(0, len(view.days_open), f"extra_days[{resource_id}]")
        model.add(extra >= days_used_expr - min_days)
        terms.append(scale * extra)
    return terms


def _s5_teacher_preference_terms(
    model: cp_model.CpModel, occupancy: Occupancy, view: _ObjectiveView, weight: float
) -> list[cp_model.LinearExprT]:
    """S5 proxy (C-12, option b): a session occupying the first or last
    period of its day counts as one violation."""
    scale = _scaled(weight)
    if scale == 0:
        return []

    edge_periods = {0, view.periods_per_day - 1}
    edge_slots = {
        slot for (day, period), slot in view.slot_by_day_period.items() if period in edge_periods
    }

    terms: list[cp_model.LinearExprT] = []
    for session_id in view.session_by_id:
        sources = [
            occupancy.occupies[(session_id, slot)]
            for slot in edge_slots
            if (session_id, slot) in occupancy.occupies
        ]
        if not sources:
            continue
        violated = model.new_bool_var(f"edge[{session_id}]")
        total = cp_model.LinearExpr.sum(sources)
        model.add(total >= 1).only_enforce_if(violated)
        model.add(total == 0).only_enforce_if(violated.negated())
        terms.append(scale * violated)
    return terms


def _room_efficiency_terms(
    model: cp_model.CpModel, variables: Variables, view: _ObjectiveView, weight: float
) -> list[cp_model.LinearExprT]:
    """S6, non-cumulative room types only - see module docstring."""
    scale = _scaled(weight)
    if scale == 0:
        return []

    demand_by_type: dict[RoomType, int] = defaultdict(int)
    for session in view.session_by_id.values():
        demand_by_type[session.required_room_type] += session.duration_periods

    assign_by_room: dict[RoomId, list[SessionId]] = defaultdict(list)
    for session_id, room_id in variables.assign:
        assign_by_room[room_id].append(session_id)

    terms: list[cp_model.LinearExprT] = []
    for room_type, room_ids in view.rooms_by_type.items():
        if room_type in variables.cumulative_room_types or not room_ids:
            continue
        target_periods = round(demand_by_type.get(room_type, 0) / len(room_ids))
        for room_id in room_ids:
            session_ids = assign_by_room.get(room_id, [])
            occupied_expr: cp_model.LinearExprT = (
                cp_model.LinearExpr.sum(
                    [
                        view.session_by_id[sid].duration_periods * variables.assign[(sid, room_id)]
                        for sid in session_ids
                    ]
                )
                if session_ids
                else 0
            )
            deviation = model.new_int_var(0, view.open_slot_count, f"room_dev[{room_id}]")
            model.add(deviation >= occupied_expr - target_periods)
            model.add(deviation >= target_periods - occupied_expr)
            terms.append(scale * deviation)
    return terms


def _subject_spread_terms(
    model: cp_model.CpModel, occupancy: Occupancy, view: _ObjectiveView, weight: float
) -> list[cp_model.LinearExprT]:
    """S7: more than one session of the same course reaching one leaf group
    on the same day, via ancestor-or-self."""
    scale = _scaled(weight)
    if scale == 0:
        return []

    by_group_course: dict[tuple[GroupId, str], list[SessionId]] = defaultdict(list)
    for leaf, session_ids in view.sessions_for_leaf_group.items():
        for sid in session_ids:
            by_group_course[(leaf, view.session_by_id[sid].course)].append(sid)

    starts_by_session_day: dict[tuple[SessionId, int], list[SlotIndex]] = defaultdict(list)
    for session_id, start_slot in occupancy.starts_at:
        starts_by_session_day[(session_id, view.slot_day[start_slot])].append(start_slot)

    terms: list[cp_model.LinearExprT] = []
    for (leaf, course), group_course_sessions in by_group_course.items():
        if len(group_course_sessions) < 2:
            continue
        for day in view.days_open:
            starts_today = [
                occupancy.starts_at[(sid, t0)]
                for sid in group_course_sessions
                for t0 in starts_by_session_day.get((sid, day), ())
            ]
            if len(starts_today) < 2:
                continue
            count_expr = cp_model.LinearExpr.sum(starts_today)
            excess = model.new_int_var(
                0, len(group_course_sessions), f"spread[{leaf},{course},{day}]"
            )
            model.add(excess >= count_expr - 1)
            terms.append(scale * excess)
    return terms


def _lunch_break_terms(
    occupancy: Occupancy, view: _ObjectiveView, weight: float
) -> list[cp_model.LinearExprT]:
    """S10: a leaf group occupied during the lunch period on a given day.
    Needs no new variable - the occupancy sum is already 0/1 (H12
    guarantees a leaf group's ancestor-or-self chain never overlaps
    itself), so it can be used directly as an objective term."""
    scale = _scaled(weight)
    if scale == 0:
        return []

    terms: list[cp_model.LinearExprT] = []
    for session_ids in view.sessions_for_leaf_group.values():
        for day in view.days_open:
            lunch_slot = view.slot_by_day_period.get((day, view.lunch_period_index))
            if lunch_slot is None:
                continue
            sources = [
                occupancy.occupies[(sid, lunch_slot)]
                for sid in session_ids
                if (sid, lunch_slot) in occupancy.occupies
            ]
            if not sources:
                continue
            terms.append(scale * cp_model.LinearExpr.sum(sources))
    return terms


def build_objective(
    model: cp_model.CpModel,
    variables: Variables,
    occupancy: Occupancy,
    instance: Instance,
    weights: dict[ConstraintCode, float],
) -> cp_model.LinearExprT | None:
    """Posts model.minimize(...) for the seven soft criteria and returns the
    expression, or returns None and posts nothing if every weight is zero or
    absent - which is what keeps a profile carrying no weights equivalent to
    the Phase 2 feasibility-only solve.
    """
    view = _build_view(instance)
    terms: list[cp_model.LinearExprT] = []

    teacher_weight = max(weights.get("S3", 0.0), weights.get("S4", 0.0))
    if teacher_weight > 0:
        teacher_daily = _build_daily_occupancy(
            model, occupancy, view, view.sessions_for_teacher, "t"
        )
        terms += _idle_time_terms(
            model, teacher_daily, view.periods_per_day, weights.get("S3", 0.0)
        )
        terms += _extra_working_day_terms(model, teacher_daily, view, weights.get("S4", 0.0))

    if weights.get("S2", 0.0) > 0:
        group_daily = _build_daily_occupancy(
            model, occupancy, view, view.sessions_for_leaf_group, "g"
        )
        terms += _idle_time_terms(model, group_daily, view.periods_per_day, weights.get("S2", 0.0))

    terms += _s5_teacher_preference_terms(model, occupancy, view, weights.get("S5", 0.0))
    terms += _room_efficiency_terms(model, variables, view, weights.get("S6", 0.0))
    terms += _subject_spread_terms(model, occupancy, view, weights.get("S7", 0.0))
    terms += _lunch_break_terms(occupancy, view, weights.get("S10", 0.0))

    if not terms:
        return None
    objective = cp_model.LinearExpr.sum(terms)
    model.minimize(objective)
    return objective
