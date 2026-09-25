"""Diagnosis by relaxation, on instances whose cheapest fix is known."""

from __future__ import annotations

import pytest

from optiedt.problem.model import Problem
from optiedt.solver.domains import build_context
from optiedt.solver.engine import SolveSettings
from optiedt.solver.relaxation import COSTS, Relaxation, RelaxationResult
from tests.snapshot_builder import SnapshotBuilder
from tests.solver.helpers import solve

pytestmark = pytest.mark.solver


def diagnose(problem: Problem, seconds: float = 3.0) -> RelaxationResult:
    settings = SolveSettings(mode="reproducible", time_limit_seconds=seconds, workers=4, seed=3)
    return Relaxation(build_context(problem), settings).run()


def kinds(result: RelaxationResult) -> list[tuple[str, int]]:
    return [(change.kind, change.cost) for change in result.changes]


def test_one_more_available_period_for_an_overbooked_instructor() -> None:
    b = SnapshotBuilder(days=1)
    for i in range(3):
        b.room(f"R{i}", 40)
    teacher = b.instructor("T", unavailable=[(0, 2), (0, 3)])
    for i in range(3):
        b.activity(f"C{i}", groups=[b.group(f"G{i}", 30)], instructors=[teacher])
    problem = b.problem()
    assert solve(problem, seconds=2).tier0.value == 1

    result = diagnose(problem)
    assert result.complete
    assert kinds(result) == [("instructor_unavailable", COSTS["instructor_unavailable"])]
    change = result.changes[0]
    assert len(change.slots) == 1
    assert change.slots[0] in (problem.slot(0, 2), problem.slot(0, 3))
    assert "Dr T would need to be available" in change.message


def test_a_lab_without_the_required_feature() -> None:
    b = SnapshotBuilder(days=1)
    b.room("LAB1", 30, "LAB")
    b.room("C1", 40)
    b.activity("CS", "LAB", groups=[b.group("G", 24)], room_type="LAB", features=("MATLAB",))
    result = diagnose(b.problem())
    assert result.complete
    assert kinds(result) == [("room_features", COSTS["room_features"])]
    assert "LAB1" in result.changes[0].message


def test_the_cheaper_room_compromise_wins() -> None:
    # A classroom five seats short costs 5 x 5; a large hall of the wrong type costs 20.
    b = SnapshotBuilder(days=1)
    b.room("C1", 40)
    b.room("H1", 50, "HALL")
    b.activity("CS", groups=[b.group("G", 45)])
    result = diagnose(b.problem())
    assert kinds(result) == [("room_type", COSTS["room_type"])]
    assert "H1" in result.changes[0].message


def test_a_hard_rule_that_cannot_hold() -> None:
    b = SnapshotBuilder(days=1)
    b.room("R", 40)
    group = b.group("G", 30)
    b.activity("A", groups=[group])
    b.activity("B", groups=[group])
    b.rule("max_periods_per_day", params={"limit": 1}, groups=[group])
    problem = b.problem()
    assert solve(problem, seconds=2).tier0.value == 1
    result = diagnose(problem)
    assert result.complete
    assert kinds(result) == [("rule", COSTS["rule"])]
    assert result.changes[0].units == 1


def test_occurrences_that_need_more_days_than_exist() -> None:
    b = SnapshotBuilder(days=2)
    b.room("R", 40)
    b.activity("A", groups=[b.group("G", 30)], sessions=3)
    result = diagnose(b.problem())
    assert result.complete
    assert kinds(result) == [("different_days", COSTS["different_days"])]


def test_opening_a_closed_slot() -> None:
    b = SnapshotBuilder(days=1, periods=(("08:00", "09:00"), ("09:00", "10:00")), closed=[(0, 1)])
    b.room("R", 40)
    group = b.group("G", 30)
    b.activity("A", groups=[group])
    b.activity("B", groups=[group])
    result = diagnose(b.problem())
    assert result.complete
    assert kinds(result) == [("slot_closed", COSTS["slot_closed"])]
    assert result.changes[0].slots == [1]


def test_what_no_relaxation_can_fix_is_reported_unscheduled() -> None:
    b = SnapshotBuilder(days=1, periods=(("08:00", "09:00"), ("09:00", "10:00")))
    b.room("R1", 40)
    b.room("R2", 40)
    teacher = b.instructor("T")
    for i in range(3):
        b.activity(f"C{i}", groups=[b.group(f"G{i}", 20)], instructors=[teacher])
    result = diagnose(b.problem())
    assert not result.complete
    assert len(result.unscheduled) == 1
    assert result.changes[-1].kind == "unscheduled"
    assert "cannot be placed even with every relaxation" in result.changes[-1].message


def test_two_fixed_sessions_on_top_of_each_other() -> None:
    b = SnapshotBuilder(days=1)
    b.room("R", 40)
    teacher = b.instructor("T")
    for i in range(2):
        b.activity(
            f"C{i}", groups=[b.group(f"G{i}", 20)], instructors=[teacher], fixed=[(1, 0, 0, None)]
        )
    result = diagnose(b.problem())
    assert result.complete
    assert kinds(result) == [("fixed_moved", COSTS["fixed_moved"])]


def test_a_feasible_instance_needs_no_change() -> None:
    b = SnapshotBuilder()
    b.room("R", 40)
    b.activity("A", groups=[b.group("G", 30)], instructors=[b.instructor("T")], sessions=2)
    result = diagnose(b.problem())
    assert result.complete
    assert result.changes == []
    assert result.total_cost == 0
