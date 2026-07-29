"""Decision variables for the weekly model, and where H4-H10 actually happen.

docs/constraint-model.md is explicit that H4, H5, H6, H8, H9 and H10 "are
applied by reducing variable domains before the search begins... This costs
nothing during solving." That is not a style choice — a CP-SAT variable's
domain is fixed at construction, so restricting it is something that can only
happen HERE, when start[s] is built, not as a constraint posted afterwards.
The ConstraintBuilder registrations for those six codes (in
solver/constraints/domain_pruned.py) exist for catalogue completeness and to
answer C-6 (none of them can carry an assumption literal — there is nothing
posted to attach one to); the actual enforcement is this module.

Room assignment does NOT use a plain room[s] integer variable, even though
that is how docs/constraint-model.md's Table 26 describes it. room[s] is
meant to obey H3 (no room double-booked) and H3's partition key is a decision
variable, not a fixed session attribute the way teacher_id or the group
hierarchy are for H1/H12 - you cannot group NoOverlap by something CP-SAT
hasn't decided yet. The standard construction instead gives each session one
boolean assign[s, r] per candidate room, with an optional interval present
only when that boolean is true, and H3 is a NoOverlap per room over those
optional intervals. room[s] as reported in a Placement is read off of
whichever assign[s, r] the solver sets to 1, after solving, in engine.py -
never carried as its own model variable. This was flagged and approved before
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from optiedt.domain.entities import RoomId, Session, SessionId, SlotIndex
from optiedt.domain.enums import AvailabilityState
from optiedt.domain.instance import Instance
from optiedt.solver.interfaces import SolverInput


@dataclass(slots=True)
class Variables:
    """Everything a ConstraintBuilder needs. Built once per solve."""

    start: dict[SessionId, cp_model.IntVar]
    """The slot session s begins at. Domain already excludes closed slots
    (H9), day-boundary-crossing starts (H8) and the teacher's declared
    unavailability (H6) - see build_variables()."""

    interval: dict[SessionId, cp_model.IntervalVar]
    """Unconditional occupation of s in time, built from start[s]. Feeds H1
    (teacher) and H12 (hierarchy), neither of which depends on which room s
    lands in."""

    candidate_rooms: dict[SessionId, tuple[RoomId, ...]]
    """Rooms of the required type with sufficient capacity (H4, H5). A
    session with an empty tuple here is unplaceable - see
    build_variables(), which raises rather than hand CP-SAT an
    impossible-to-satisfy assignment sum."""

    assign: dict[tuple[SessionId, RoomId], cp_model.IntVar]
    """assign[s, r] is 1 iff session s is placed in room r. Only defined
    for (s, r) pairs in candidate_rooms[s]."""

    room_interval: dict[tuple[SessionId, RoomId], cp_model.IntervalVar]
    """Optional interval, present iff assign[s, r] is 1. Feeds H3 (room
    NoOverlap). Same (start, size) as interval[s] - only the presence
    literal differs between sessions competing for the same room."""

    excluded_room_pairs: frozenset[tuple[SessionId, RoomId]] = field(default_factory=frozenset)
    """(session, room) pairs an accepted exclude_slot recommendation has
    removed from candidacy (ADR-007). Recorded here so H7's exactly-one
    sum can be checked against it in tests; the exclusion itself already
    happened by the pair being absent from candidate_rooms."""


def _open_slot_map(instance: Instance) -> dict[SlotIndex, bool]:
    return {s.index: s.is_open for s in instance.slots}


def _day_of(instance: Instance) -> dict[SlotIndex, int]:
    return {s.index: s.day_index for s in instance.slots}


def _unavailable_by_teacher(instance: Instance) -> dict[str, frozenset[SlotIndex]]:
    by_teacher: dict[str, set[SlotIndex]] = {}
    for a in instance.availability:
        if a.state is AvailabilityState.UNAVAILABLE:
            by_teacher.setdefault(a.teacher, set()).add(a.slot)
    return {t: frozenset(v) for t, v in by_teacher.items()}


def _valid_starts(
    session: Session,
    all_slot_indices: list[SlotIndex],
    is_open: dict[SlotIndex, bool],
    day_of: dict[SlotIndex, int],
    unavailable: frozenset[SlotIndex],
    excluded_starts: frozenset[SlotIndex],
) -> list[SlotIndex]:
    """H6, H8, H9 combined: which slot indices session s could legally
    start at, given its duration and its teacher's declared unavailability.
    """
    duration = session.duration_periods
    valid: list[SlotIndex] = []
    for t in all_slot_indices:
        if t in excluded_starts:
            continue
        span = range(t, t + duration)
        # H9: every consumed period must be an open slot that exists.
        if any(p not in is_open or not is_open[p] for p in span):
            continue
        # H8: a multi-period session must not cross into the next day.
        if len({day_of[p] for p in span if p in day_of}) != 1:
            continue
        # H6: none of the consumed periods may be declared unavailable.
        if any(p in unavailable for p in span):
            continue
        valid.append(t)
    return valid


def _candidate_rooms(
    session: Session,
    instance: Instance,
    group_size_by_id: dict[str, int],
    excluded_rooms: frozenset[RoomId],
) -> tuple[RoomId, ...]:
    """H4, H5: rooms of the required type with capacity for the group."""
    size = group_size_by_id[session.group]
    return tuple(
        r.id
        for r in instance.rooms
        if r.type is session.required_room_type
        and r.capacity >= size
        and r.id not in excluded_rooms
    )


def build_variables(model: cp_model.CpModel, request: SolverInput) -> Variables:
    """Build every decision variable for one solve.

    Raises ValueError naming the session if H6/H8/H9 leave it with no valid
    start, or if H4/H5 leave it with no candidate room - both mean the
    instance is infeasible for a reason the pre-analysis should have caught
    first (this is exactly why pre-analysis exists; see
    docs/architecture.md). This function does not run pre-analysis itself,
    it only refuses to build a model on data pre-analysis would have
    rejected.

    request.locked_sessions is honoured by refusing to proceed: there is
    currently no way to supply the TARGET slot/room a locked session should
    keep (SolverInput carries only session ids, not the paired values), so a
    non-empty set here is a caller error today, not a silently-ignored
    field. See docs/open-questions.md for why this is a known gap rather
    than an oversight - it only becomes fillable once recommendation-driven
    regeneration (Phase 3) has a candidate to lock a session's placement
    FROM. The reference instance has zero locked sessions, so this path is
    never exercised by anything in Phase 2.
    """
    if request.locked_sessions:
        raise ValueError(
            "SolverInput.locked_sessions is non-empty, but there is no mechanism yet "
            "to supply the target (slot, room) a locked session should keep - only "
            "session ids are carried today. This is Phase 3 territory (recommendation "
            "regeneration); see docs/open-questions.md."
        )

    instance = request.instance
    all_slots = sorted(s.index for s in instance.slots)
    is_open = _open_slot_map(instance)
    day_of = _day_of(instance)
    unavailable_by_teacher = _unavailable_by_teacher(instance)
    group_size_by_id = {g.id: g.size for g in instance.groups}

    excluded_starts_by_session: dict[SessionId, set[SlotIndex]] = {}
    excluded_rooms_by_session: dict[SessionId, set[RoomId]] = {}
    for session_id, slot_index in request.excluded_slots:
        excluded_starts_by_session.setdefault(session_id, set()).add(slot_index)
    for session_id, room_id in request.excluded_rooms:
        excluded_rooms_by_session.setdefault(session_id, set()).add(room_id)

    start: dict[SessionId, cp_model.IntVar] = {}
    interval: dict[SessionId, cp_model.IntervalVar] = {}
    candidate_rooms: dict[SessionId, tuple[RoomId, ...]] = {}
    assign: dict[tuple[SessionId, RoomId], cp_model.IntVar] = {}
    room_interval: dict[tuple[SessionId, RoomId], cp_model.IntervalVar] = {}

    for session in instance.sessions:
        unavailable = unavailable_by_teacher.get(session.teacher, frozenset())
        excluded_starts = frozenset(excluded_starts_by_session.get(session.id, ()))
        valid_starts = _valid_starts(
            session, all_slots, is_open, day_of, unavailable, excluded_starts
        )
        if not valid_starts:
            raise ValueError(
                f"session {session.id}: no valid start slot after H6/H8/H9 pruning "
                f"(teacher {session.teacher}, duration {session.duration_periods}). "
                "The pre-analysis should catch this before the solver is ever called."
            )
        domain = cp_model.Domain.FromValues(valid_starts)
        start[session.id] = model.new_int_var_from_domain(domain, f"start[{session.id}]")
        interval[session.id] = model.new_interval_var(
            start[session.id],
            session.duration_periods,
            start[session.id] + session.duration_periods,
            f"iv[{session.id}]",
        )

        excluded_rooms = frozenset(excluded_rooms_by_session.get(session.id, ()))
        rooms = _candidate_rooms(session, instance, group_size_by_id, excluded_rooms)
        if not rooms:
            raise ValueError(
                f"session {session.id}: no candidate room after H4/H5 pruning "
                f"(required type {session.required_room_type}, group {session.group}). "
                "The pre-analysis should catch this before the solver is ever called."
            )
        candidate_rooms[session.id] = rooms

        for room_id in rooms:
            key = (session.id, room_id)
            assign[key] = model.new_bool_var(f"assign[{session.id},{room_id}]")
            room_interval[key] = model.new_optional_interval_var(
                start[session.id],
                session.duration_periods,
                start[session.id] + session.duration_periods,
                assign[key],
                f"room_iv[{session.id},{room_id}]",
            )

    return Variables(
        start=start,
        interval=interval,
        candidate_rooms=candidate_rooms,
        assign=assign,
        room_interval=room_interval,
    )
