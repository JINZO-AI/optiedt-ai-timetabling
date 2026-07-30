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


def test_locked_sessions_not_yet_supported(instance):
    model = cp_model.CpModel()
    request = SolverInput(
        instance=instance,
        profile=None,  # type: ignore[arg-type]
        seed=42,
        deterministic_budget=5.0,
        locked_sessions=frozenset({"S0001"}),
    )
    with pytest.raises(ValueError, match="no mechanism yet"):
        build_variables(model, request)
