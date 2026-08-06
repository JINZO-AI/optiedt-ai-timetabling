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

That per-room encoding is NOT used for every room type, though. Amphi,
Lab_Info and Lab_Sciences are fully interchangeable room types on the
reference instance - every session needing one gets every room of that type
as a candidate - so the cumulative encoding below applies to them.

⚠️ This split was introduced to fix a search-performance problem that did
not exist. The `UNKNOWN` results it was reacting to were an INFEASIBLE
instance, not a hard symmetric search: the reference instance offered 66
two-period laboratory windows against 80 sessions needing one (C-13,
resolved 2026-07-30 - see docs/open-questions.md). The encoding is still
correct, still unit-tested, and cuts the room-assignment boolean count by
roughly 90%, so it is kept - but **whether the simpler per-room encoding
would now serve for every type has not been measured**, and the honest
reason this code exists is a diagnosis that turned out to be wrong. A room
type qualifies as
"cumulative" here (see cumulative_room_types below) only when EVERY session
needing it has ALL of that type's rooms as candidates - if even one session
is narrower (the way Salle sessions are, since group size varies), the whole
type falls back to the per-room encoding, because the interval-colouring
argument the cumulative encoding relies on (see solver/engine.py) only holds
when every room of the type is truly interchangeable for every session.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from optiedt.domain.entities import Placement, RoomId, Session, SessionId, SlotIndex
from optiedt.domain.enums import AvailabilityState, RoomType
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
    for (s, r) pairs in candidate_rooms[s] where s's room type is NOT in
    cumulative_room_types - a cumulative-encoded session has no assign
    variable at all, since which specific room it gets is decided after
    solving (engine.py), not by the model."""

    room_interval: dict[tuple[SessionId, RoomId], cp_model.IntervalVar]
    """Optional interval, present iff assign[s, r] is 1. Feeds H3 (room
    NoOverlap). Same (start, size) as interval[s] - only the presence
    literal differs between sessions competing for the same room. Same
    restriction as assign: only built for non-cumulative room types."""

    cumulative_room_types: frozenset[RoomType] = field(default_factory=frozenset)
    """Room types for which every requiring session has every room of that
    type as a candidate (C-13). H3 posts a single AddCumulative over these
    sessions' unconditional intervals instead of a NoOverlap per room, and
    H7 posts nothing for them - see solver/constraints/room_assignment.py
    and solver/engine.py for how a specific room is still chosen afterward."""

    excluded_room_pairs: frozenset[tuple[SessionId, RoomId]] = field(default_factory=frozenset)
    """(session, room) pairs an accepted exclude_slot recommendation has
    removed from candidacy (ADR-007). Recorded here so H7's exactly-one
    sum can be checked against it in tests; the exclusion itself already
    happened by the pair being absent from candidate_rooms."""

    locked_placements: frozenset[Placement] = field(default_factory=frozenset)
    """Sessions H10 pinned to one slot and one room. Recorded here for the
    same reason as excluded_room_pairs: the pruning already happened, by
    start[s]'s domain being the single locked slot and candidate_rooms[s]
    being the single locked room, and a test needs something to check that
    against."""


def open_slot_map(instance: Instance) -> dict[SlotIndex, bool]:
    return {s.index: s.is_open for s in instance.slots}


def day_of(instance: Instance) -> dict[SlotIndex, int]:
    return {s.index: s.day_index for s in instance.slots}


def unavailable_by_teacher(instance: Instance) -> dict[str, frozenset[SlotIndex]]:
    by_teacher: dict[str, set[SlotIndex]] = {}
    for a in instance.availability:
        if a.state is AvailabilityState.UNAVAILABLE:
            by_teacher.setdefault(a.teacher, set()).add(a.slot)
    return {t: frozenset(v) for t, v in by_teacher.items()}


def valid_starts(
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


def candidate_rooms_for_session(
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


def _locks_by_session(locked: frozenset[Placement]) -> dict[SessionId, Placement]:
    """H10's locks indexed by session, refusing two locks on one session.

    Two Placements naming the same session with different targets is not a
    conflict CP-SAT should be asked to resolve - it is a caller that composed
    two incompatible recommendations, and the one that would silently win
    depends on frozenset iteration order. Raising names both targets.
    """
    by_session: dict[SessionId, Placement] = {}
    for placement in sorted(locked, key=lambda p: (p.session, p.slot, p.room)):
        existing = by_session.get(placement.session)
        if existing is not None and existing != placement:
            raise ValueError(
                f"session {placement.session}: locked twice, to "
                f"(slot {existing.slot}, room {existing.room}) and to "
                f"(slot {placement.slot}, room {placement.room}). A session has one "
                "placement; two locks on it cannot both be honoured."
            )
        by_session[placement.session] = placement
    return by_session


def _fully_interchangeable_types(
    instance: Instance, candidate_rooms: dict[SessionId, tuple[RoomId, ...]]
) -> frozenset[RoomType]:
    """A room type is "fully interchangeable" iff every session that needs
    it has EVERY room of that type as a candidate - i.e. H4/H5 pruning
    removed nothing for that type on this request. Only then does the
    cumulative encoding's correctness argument hold (solver/engine.py):
    if simultaneous demand for the type never exceeds its room count, a
    per-room labelling can always be recovered afterward, because any one
    room of the type would have worked for any one of these sessions.

    A single narrower session (the way Salle sessions are, since group
    size varies room to room) disqualifies its whole type - there is no
    per-session mixing, only per-type, to keep the correctness argument
    simple to state and simple to verify independently (see
    tests/integration/test_h1_h12.py).
    """
    rooms_by_type: dict[RoomType, set[RoomId]] = defaultdict(set)
    for room in instance.rooms:
        rooms_by_type[room.type].add(room.id)

    sessions_by_type: dict[RoomType, list[SessionId]] = defaultdict(list)
    for session in instance.sessions:
        sessions_by_type[session.required_room_type].append(session.id)

    return frozenset(
        room_type
        for room_type, session_ids in sessions_by_type.items()
        if all(
            frozenset(candidate_rooms[sid]) == frozenset(rooms_by_type[room_type])
            for sid in session_ids
        )
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

    request.locked_placements is H10, applied here like the other five
    domain-pruned rules: a locked session's start domain becomes the single
    locked slot and its candidate room tuple becomes the single locked room.
    Nothing is posted, so H10 carries no assumption literal (C-6) and costs
    nothing during search.

    ⚠️ Until 2026-08-06 this function RAISED on a non-empty lock set, because
    SolverInput carried session ids with no target to lock them to. C-19
    replaced that field with frozenset[Placement] and H10 stopped being
    dormant.

    ⚠️ **A lock RESTRICTS; it never grants permission.** The locked slot and
    room are INTERSECTED with the domains H4/H5/H6/H8/H9 already pruned, never
    substituted for them, so a lock cannot smuggle a session onto a closed slot
    or into a room too small for its group. When the intersection is empty the
    function raises naming the session, the target and the rule that refused -
    the same treatment every other unsatisfiable domain gets here.
    """
    instance = request.instance
    all_slots = sorted(s.index for s in instance.slots)
    is_open = open_slot_map(instance)
    day_by_slot = day_of(instance)
    unavailable_by_teacher_map = unavailable_by_teacher(instance)
    group_size_by_id = {g.id: g.size for g in instance.groups}

    excluded_starts_by_session: dict[SessionId, set[SlotIndex]] = {}
    excluded_rooms_by_session: dict[SessionId, set[RoomId]] = {}
    for session_id, slot_index in request.excluded_slots:
        excluded_starts_by_session.setdefault(session_id, set()).add(slot_index)
    for session_id, room_id in request.excluded_rooms:
        excluded_rooms_by_session.setdefault(session_id, set()).add(room_id)

    lock_by_session = _locks_by_session(request.locked_placements)

    start: dict[SessionId, cp_model.IntVar] = {}
    interval: dict[SessionId, cp_model.IntervalVar] = {}
    candidate_rooms: dict[SessionId, tuple[RoomId, ...]] = {}

    # Pass 1: start/interval/candidate_rooms for every session. Needed
    # regardless of which room-assignment encoding a session ends up with -
    # cumulative_room_types (below) can only be decided once every session's
    # candidate set is known.
    for session in instance.sessions:
        unavailable = unavailable_by_teacher_map.get(session.teacher, frozenset())
        excluded_starts = frozenset(excluded_starts_by_session.get(session.id, ()))
        valid_start_slots = valid_starts(
            session, all_slots, is_open, day_by_slot, unavailable, excluded_starts
        )
        if not valid_start_slots:
            raise ValueError(
                f"session {session.id}: no valid start slot after H6/H8/H9 pruning "
                f"(teacher {session.teacher}, duration {session.duration_periods}). "
                "The pre-analysis should catch this before the solver is ever called."
            )

        lock = lock_by_session.get(session.id)
        if lock is not None:
            # H10 INTERSECTS - see the docstring. A locked slot that H6/H8/H9
            # already refused stays refused, and the caller is told which rule.
            if lock.slot not in valid_start_slots:
                raise ValueError(
                    f"session {session.id}: H10 locks it to slot {lock.slot}, which "
                    f"H6/H8/H9 already exclude (teacher {session.teacher}, duration "
                    f"{session.duration_periods}). A lock restricts the solver's "
                    "choices; it cannot grant a placement the hard rules forbid."
                )
            valid_start_slots = [lock.slot]

        domain = cp_model.Domain.FromValues(valid_start_slots)
        start[session.id] = model.new_int_var_from_domain(domain, f"start[{session.id}]")
        interval[session.id] = model.new_interval_var(
            start[session.id],
            session.duration_periods,
            start[session.id] + session.duration_periods,
            f"iv[{session.id}]",
        )

        excluded_rooms = frozenset(excluded_rooms_by_session.get(session.id, ()))
        rooms = candidate_rooms_for_session(session, instance, group_size_by_id, excluded_rooms)
        if not rooms:
            raise ValueError(
                f"session {session.id}: no candidate room after H4/H5 pruning "
                f"(required type {session.required_room_type}, group {session.group}). "
                "The pre-analysis should catch this before the solver is ever called."
            )

        if lock is not None:
            if lock.room not in rooms:
                raise ValueError(
                    f"session {session.id}: H10 locks it to room {lock.room}, which "
                    f"H4/H5 already exclude (required type {session.required_room_type}, "
                    f"group {session.group}). A lock restricts the solver's choices; it "
                    "cannot grant a placement the hard rules forbid."
                )
            rooms = (lock.room,)

        candidate_rooms[session.id] = rooms

    cumulative_room_types = _fully_interchangeable_types(instance, candidate_rooms)

    # Pass 2: assign/room_interval, only for sessions whose room type is NOT
    # fully interchangeable. A cumulative-encoded session gets neither - see
    # cumulative_room_types's docstring on Variables and
    # solver/constraints/room_assignment.py for how H3/H7 handle the split.
    assign: dict[tuple[SessionId, RoomId], cp_model.IntVar] = {}
    room_interval: dict[tuple[SessionId, RoomId], cp_model.IntervalVar] = {}
    for session in instance.sessions:
        if session.required_room_type in cumulative_room_types:
            continue
        for room_id in candidate_rooms[session.id]:
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
        cumulative_room_types=cumulative_room_types,
        excluded_room_pairs=request.excluded_rooms,
        locked_placements=request.locked_placements,
    )
