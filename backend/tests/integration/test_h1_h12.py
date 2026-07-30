"""Solve the real reference instance end-to-end and independently re-verify
every hard constraint against raw data.

CP-SAT's own status only proves that CP-SAT's own model has (or lacks) a
solution - it says nothing about whether that model actually MEANS what
H1-H12 require. This project's own H12 bug (docs/status.md, 2026-07-30)
produced a wrongly-INFEASIBLE model from a too-tight constraint; the
opposite mistake - a too-loose model reporting a false OPTIMAL - would not
be caught by trusting the solver's status alone. So beyond checking
feasibility, this recomputes every hard-constraint rule directly from the
returned placements and the CSVs, independently of the CP-SAT machinery
that produced them.

H2 and H11 are not checked separately: H2 (a group has at most one session
per slot) is implied by the H12 check below, since every group's own
sessions are included in its own ancestor-chain check. H11 (aggregate
demand per room type does not exceed capacity) is implied by the H3 check,
since a per-room NoOverlap that holds for every room of a type already
bounds simultaneous demand for that type. This matches the C-6 resolution
in docs/open-questions.md: H2 and H11 carry no assumption literal because
there is no separate posting for them to attach one to.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from optiedt.domain.enums import AvailabilityState
from optiedt.instance.loader import load_instance
from optiedt.solver.engine import CpSatSolver
from optiedt.solver.interfaces import SolverInput

INSTANCE_PATH = Path(__file__).resolve().parents[3] / "data" / "instance"
SEED = 42

# Measured on the reference instance (docs/status.md, 2026-07-30): the room
# type Lab_Info is 6 fully interchangeable rooms packed to 160/168
# room-periods (95.2%), which makes room assignment a hard symmetric
# bin-packing search for CP-SAT's default portfolio, independently of
# whether H1-H12 are modelled correctly. This budget is generous rather than
# tight for exactly that reason - see the deterministic-time measurement
# recorded in docs/status.md for what was actually needed.
DETERMINISTIC_BUDGET = 480.0
WALL_CLOCK_CEILING = 480.0


@pytest.fixture(scope="module")
def instance():
    return load_instance(INSTANCE_PATH)


@pytest.fixture(scope="module")
def result(instance):
    request = SolverInput(
        instance=instance,
        profile=None,  # type: ignore[arg-type]
        seed=SEED,
        deterministic_budget=DETERMINISTIC_BUDGET,
    )
    solver = CpSatSolver(wall_clock_ceiling_seconds=WALL_CLOCK_CEILING)
    return solver.solve(request)


def _occupied(duration_periods: int, start_slot: int) -> set[int]:
    return set(range(start_slot, start_slot + duration_periods))


@pytest.mark.solver
def test_reference_instance_is_feasible(instance, result):
    assert not result.infeasible, (
        "H1+H3+H7+H12 (plus the domain-pruned H4/H5/H6/H8/H9/H10) could not place "
        "all sessions of the reference instance within the deterministic budget. "
        "All five pre-analysis checks pass on this instance, so this points to a "
        "modelling bug, not an unsolvable instance - isolate further by solving "
        "constraint subsets individually against the real data, per docs/status.md."
    )
    assert len(result.placements) == len(instance.sessions)


@pytest.mark.solver
def test_no_session_is_locked_in_the_reference_instance():
    """H10 (locked sessions keep their placement) has no implementation yet -
    build_variables() refuses to run if any session is locked. This is a
    documented Phase 3 gap (see solver/variables.py), not an oversight, and
    it is only safe because the reference instance has zero locked sessions.
    This assertion exists so that if that ever stops being true, the gap
    surfaces here loudly instead of being silently mismodelled."""
    instance = load_instance(INSTANCE_PATH)
    assert not any(s.locked for s in instance.sessions)


@pytest.mark.solver
def test_placements_satisfy_every_hard_constraint_independently(instance, result):
    assert not result.infeasible

    session_by_id = {s.id: s for s in instance.sessions}
    room_by_id = {r.id: r for r in instance.rooms}
    slot_by_index = {s.index: s for s in instance.slots}
    group_size_by_id = {g.id: g.size for g in instance.groups}
    parent_of = {g.id: g.parent_group for g in instance.groups}
    placement_by_session = {p.session: p for p in result.placements}

    unavailable_by_teacher: dict[str, set[int]] = {}
    for a in instance.availability:
        if a.state is AvailabilityState.UNAVAILABLE:
            unavailable_by_teacher.setdefault(a.teacher, set()).add(a.slot)

    # Every session was placed exactly once.
    assert set(placement_by_session) == set(session_by_id)

    for placement in result.placements:
        session = session_by_id[placement.session]
        occupied = _occupied(session.duration_periods, placement.slot)

        # H9: every occupied period is an open slot that exists.
        for slot_index in occupied:
            assert slot_index in slot_by_index, f"{session.id}: slot {slot_index} does not exist"
            assert slot_by_index[slot_index].is_open, f"{session.id}: slot {slot_index} is closed"

        # H8: a multi-period session must not cross a day boundary.
        days = {slot_by_index[t].day_index for t in occupied}
        assert len(days) == 1, f"{session.id} spans more than one day: {occupied}"

        # H6: none of the occupied periods may be the teacher's declared unavailability.
        unavailable = unavailable_by_teacher.get(session.teacher, set())
        assert occupied.isdisjoint(unavailable), (
            f"{session.id}: placed at a slot teacher {session.teacher} declared unavailable"
        )

        # H4, H5: the assigned room matches the required type and has capacity.
        room = room_by_id[placement.room]
        assert room.type is session.required_room_type, (
            f"{session.id}: room {room.id} is {room.type}, "
            f"session requires {session.required_room_type}"
        )
        assert room.capacity >= group_size_by_id[session.group], (
            f"{session.id}: room {room.id} capacity {room.capacity} < "
            f"group size {group_size_by_id[session.group]}"
        )

    # H1: no teacher is double-booked.
    occupied_by_teacher: dict[str, set[int]] = {}
    for placement in result.placements:
        session = session_by_id[placement.session]
        span = _occupied(session.duration_periods, placement.slot)
        already = occupied_by_teacher.setdefault(session.teacher, set())
        overlap = already & span
        assert not overlap, f"teacher {session.teacher} double-booked at slot(s) {overlap}"
        already |= span

    # H3: no room is double-booked.
    occupied_by_room: dict[str, set[int]] = {}
    for placement in result.placements:
        session = session_by_id[placement.session]
        span = _occupied(session.duration_periods, placement.slot)
        already = occupied_by_room.setdefault(placement.room, set())
        overlap = already & span
        assert not overlap, f"room {placement.room} double-booked at slot(s) {overlap}"
        already |= span

    # H12: a group and every ancestor in its hierarchy are never busy together.
    sessions_by_group: dict[str, list] = {}
    for placement in result.placements:
        session = session_by_id[placement.session]
        sessions_by_group.setdefault(session.group, []).append((session, placement))

    def ancestor_chain(group_id: str) -> list[str]:
        chain = []
        current: str | None = group_id
        while current is not None:
            chain.append(current)
            current = parent_of.get(current)
        return chain

    for group in instance.groups:
        chain = ancestor_chain(group.id)
        occupied_lineage: set[int] = set()
        for ancestor_id in chain:
            for session, placement in sessions_by_group.get(ancestor_id, []):
                span = _occupied(session.duration_periods, placement.slot)
                overlap = occupied_lineage & span
                assert not overlap, (
                    f"group {group.id}'s lineage double-booked at slot(s) {overlap} "
                    f"(via ancestor {ancestor_id})"
                )
                occupied_lineage |= span
