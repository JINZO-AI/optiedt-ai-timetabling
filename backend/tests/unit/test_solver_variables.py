"""Variable domains against known facts about the real reference instance.

Each assertion here is checked against a concrete row in data/instance/, not
a synthetic fixture, so a wrong domain restriction (the kind of bug that
would silently make the model over- or under-constrained) shows up here
before it ever reaches the solver.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ortools.sat.python import cp_model

from optiedt.domain.entities import Placement
from optiedt.domain.enums import RoomType
from optiedt.instance.loader import load_instance
from optiedt.solver.interfaces import SolverInput
from optiedt.solver.variables import build_variables

INSTANCE_PATH = Path(__file__).resolve().parents[3] / "data" / "instance"


@pytest.fixture(scope="module")
def instance():
    return load_instance(INSTANCE_PATH)


@pytest.fixture
def variables(instance):
    model = cp_model.CpModel()
    request = SolverInput(instance=instance, profile=None, seed=42, deterministic_budget=5.0)  # type: ignore[arg-type]
    return model, build_variables(model, request)


def _expand_domain(var: cp_model.IntVar) -> set[int]:
    """Domain protos store [min0, max0, min1, max1, ...] interval pairs."""
    values: set[int] = set()
    d = var.proto.domain
    for i in range(0, len(d), 2):
        values.update(range(d[i], d[i + 1] + 1))
    return values


def test_h9_closed_slots_excluded_from_every_session(instance, variables):
    # Slots 28 and 29 are the two closed Saturday-afternoon periods.
    _, v = variables
    for session_id, var in v.start.items():
        domain = _expand_domain(var)
        assert 28 not in domain, f"{session_id} allows closed slot 28"
        assert 29 not in domain, f"{session_id} allows closed slot 29"


def test_h6_teacher_unavailability_excluded(instance, variables):
    # T001 is declared unavailable at slots 13 and 14 (H6), and teaches
    # S0001 and S0145 (both 1-period CM sessions).
    _, v = variables
    for session_id in ("S0001", "S0145"):
        domain = _expand_domain(v.start[session_id])
        assert 13 not in domain
        assert 14 not in domain


def test_h8_two_period_session_cannot_cross_a_day_boundary(instance, variables):
    # S0006 is a 2-period session. The last period of each day is index
    # 4, 9, 14, 19, 24 or 29 - starting a 2-period session there would
    # spill into the next day.
    _, v = variables
    domain = _expand_domain(v.start["S0006"])
    for boundary in (4, 9, 14, 19, 24, 29):
        assert boundary not in domain, f"S0006 could start at day-boundary slot {boundary}"


def test_h4_h5_candidate_rooms_match_type_and_capacity(instance, variables):
    _, v = variables
    room_type_by_id = {r.id: r.type for r in instance.rooms}
    room_capacity_by_id = {r.id: r.capacity for r in instance.rooms}
    group_size_by_id = {g.id: g.size for g in instance.groups}

    for session in instance.sessions:
        candidates = v.candidate_rooms[session.id]
        assert candidates, f"{session.id} has no candidate room"
        size = group_size_by_id[session.group]
        for room_id in candidates:
            assert room_type_by_id[room_id] is session.required_room_type
            assert room_capacity_by_id[room_id] >= size


def test_lab_info_session_only_gets_lab_info_rooms(instance, variables):
    _, v = variables
    room_type_by_id = {r.id: r.type for r in instance.rooms}
    for room_id in v.candidate_rooms["S0006"]:
        assert room_type_by_id[room_id] is RoomType.LAB_INFO


def test_assign_variables_exist_only_for_candidate_pairs(instance, variables):
    """Only for sessions whose room type is NOT fully interchangeable
    (C-13) - a cumulative-encoded session has candidate_rooms populated
    (H4/H5 still needs it) but no assign/room_interval at all, since which
    specific room it gets is decided after solving, not by the model."""
    _, v = variables
    session_by_id = {s.id: s for s in instance.sessions}
    for session_id, rooms in v.candidate_rooms.items():
        if session_by_id[session_id].required_room_type in v.cumulative_room_types:
            for room_id in rooms:
                assert (session_id, room_id) not in v.assign
                assert (session_id, room_id) not in v.room_interval
            continue
        for room_id in rooms:
            assert (session_id, room_id) in v.assign
            assert (session_id, room_id) in v.room_interval


def test_fully_interchangeable_room_types_are_cumulative_encoded(instance, variables):
    """Amphi, Lab_Info and Lab_Sciences: every session needing that type
    has every room of that type as a candidate (2/2, 8/8, 3/3 after the
    C-13 room re-typing - see docs/open-questions.md). Salle is only
    partially interchangeable (5-7 of 7, since a group of 35 does not fit
    the two 30-seat rooms), so it must stay per-room."""
    _, v = variables
    assert v.cumulative_room_types == {
        RoomType.AMPHI,
        RoomType.LAB_INFO,
        RoomType.LAB_SCIENCES,
    }
    assert RoomType.SALLE not in v.cumulative_room_types


def _built_with(instance, **kwargs):
    model = cp_model.CpModel()
    request = SolverInput(
        instance=instance,
        profile=None,  # type: ignore[arg-type]
        seed=42,
        deterministic_budget=5.0,
        **kwargs,
    )
    return model, build_variables(model, request)


# ── H10, live since 2026-08-06 (C-19) ──────────────────────────────────────
#
# Until then SolverInput carried session ids with no target and
# build_variables() raised. The test that pinned THAT behaviour was replaced
# by these: a dormant rule is pinned by asserting it refuses, a live one by
# asserting it restricts.


def test_h10_locks_the_start_domain_to_the_single_locked_slot(instance):
    # S0001 is T001's 1-period Amphi CM; slot 7 is inside its valid starts.
    _, v = _built_with(instance, locked_placements=frozenset({Placement("S0001", 7, "2")}))
    assert _expand_domain(v.start["S0001"]) == {7}


def test_h10_locks_the_candidate_rooms_to_the_single_locked_room(instance):
    # Unlocked, S0001 may take either Amphi (rooms 1 and 2).
    _, unlocked = _built_with(instance)
    assert unlocked.candidate_rooms["S0001"] == ("1", "2")

    _, v = _built_with(instance, locked_placements=frozenset({Placement("S0001", 7, "2")}))
    assert v.candidate_rooms["S0001"] == ("2",)


def test_h10_leaves_every_other_session_untouched(instance):
    """A lock restricts the session it names and nothing else.

    Worth asserting rather than assuming: the pruning runs inside the loop
    over every session, so an indexing slip would narrow the wrong one and
    still produce a solvable model.
    """
    _, unlocked = _built_with(instance)
    _, v = _built_with(instance, locked_placements=frozenset({Placement("S0001", 7, "2")}))
    for session_id in v.start:
        if session_id == "S0001":
            continue
        assert _expand_domain(v.start[session_id]) == _expand_domain(unlocked.start[session_id])
        assert v.candidate_rooms[session_id] == unlocked.candidate_rooms[session_id]


def test_h10_records_its_locks_on_the_variables(instance):
    locks = frozenset({Placement("S0001", 7, "2")})
    _, v = _built_with(instance, locked_placements=locks)
    assert v.locked_placements == locks


def test_h10_cannot_grant_a_slot_h6_forbids(instance):
    """T001 is unavailable at slot 13 and teaches S0001.

    The lock INTERSECTS the pruning H6/H8/H9 already did; it does not replace
    it. If it replaced it, a recommendation could quietly place a session on
    a slot a teacher declared unavailable - an invariant-2 violation arriving
    through the one door recommendations are allowed to use.
    """
    with pytest.raises(ValueError, match="H10 locks it to slot 13, which H6/H8/H9 already exclude"):
        _built_with(instance, locked_placements=frozenset({Placement("S0001", 13, "2")}))


def test_h10_cannot_grant_a_closed_slot(instance):
    # Slot 28 is Saturday afternoon, closed (H9).
    with pytest.raises(ValueError, match="H10 locks it to slot 28"):
        _built_with(instance, locked_placements=frozenset({Placement("S0001", 28, "2")}))


def test_h10_cannot_grant_a_room_h4_forbids(instance):
    # Room 4 is a Salle; S0001 requires an Amphi.
    with pytest.raises(ValueError, match="H10 locks it to room 4, which H4/H5 already exclude"):
        _built_with(instance, locked_placements=frozenset({Placement("S0001", 7, "4")}))


def test_h10_refuses_two_conflicting_locks_on_one_session(instance):
    """Which one wins would otherwise depend on frozenset iteration order."""
    with pytest.raises(ValueError, match="locked twice"):
        _built_with(
            instance,
            locked_placements=frozenset({Placement("S0001", 7, "2"), Placement("S0001", 8, "2")}),
        )


def test_h10_accepts_the_same_lock_twice(instance):
    """Two identical Placements are one lock, not a conflict - and a frozenset
    already collapses them. Asserted so the duplicate check is known to test
    the TARGET rather than the count."""
    _, v = _built_with(
        instance,
        locked_placements=frozenset({Placement("S0001", 7, "2"), Placement("S0001", 7, "2")}),
    )
    assert _expand_domain(v.start["S0001"]) == {7}


def test_locking_a_cumulative_type_falls_back_to_the_per_room_encoding(instance):
    """Locking an Amphi session takes Amphi out of cumulative_room_types.

    This is required for correctness, not a side effect to tolerate: a
    cumulative-encoded session has no assign[s, r] variable at all and its
    specific room is chosen by a post-solve labeller (solver/engine.py), which
    cannot honour a lock. Narrowing candidate_rooms makes the type stop being
    fully interchangeable, so H7 posts its exactly-one over a single room and
    the lock binds. If this test ever fails, H10 has become unenforceable for
    that room type while still appearing to be applied.
    """
    _, unlocked = _built_with(instance)
    assert RoomType.AMPHI in unlocked.cumulative_room_types
    assert ("S0001", "2") not in unlocked.assign

    _, v = _built_with(instance, locked_placements=frozenset({Placement("S0001", 7, "2")}))
    assert RoomType.AMPHI not in v.cumulative_room_types
    assert ("S0001", "2") in v.assign
    assert ("S0001", "1") not in v.assign
