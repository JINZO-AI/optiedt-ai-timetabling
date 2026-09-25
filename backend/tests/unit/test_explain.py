"""Explanations for sessions that are not in the timetable."""

from __future__ import annotations

from optiedt.evaluation.evaluator import Evaluator
from optiedt.evaluation.explain import explain
from optiedt.evaluation.types import ObjectiveConfig, Placement
from optiedt.problem.model import Problem
from tests.snapshot_builder import SnapshotBuilder

ONE_DAY = (("08:00", "09:00"), ("09:00", "10:00"), ("10:00", "11:00"), ("11:00", "12:00"))


def evaluator(problem: Problem) -> Evaluator:
    return Evaluator(problem, ObjectiveConfig({}))


def test_an_instructor_busy_in_every_window() -> None:
    b = SnapshotBuilder(days=1, periods=ONE_DAY)
    for i in range(5):
        b.room(f"R{i}", 40)
    teacher = b.instructor("T")
    for i in range(5):
        b.activity(f"C{i}", groups=[b.group(f"G{i}", 20)], instructors=[teacher])
    problem = b.problem()
    placements = {i: Placement(problem.slot(0, i), i) for i in range(4)}
    result = explain(evaluator(problem), placements, 4)
    assert result.windows == 4
    assert result.free == ()
    assert [(o.code, o.windows) for o in result.obstacles] == [("instructor_conflict", 4)]
    assert result.obstacles[0].sessions == (0, 1, 2, 3)
    assert "Dr T teaches another session (4 windows)" in result.summary


def test_unavailability_and_busy_students_share_the_windows() -> None:
    b = SnapshotBuilder(days=1, periods=ONE_DAY)
    b.room("R1", 40)
    b.room("R2", 40)
    group = b.group("G", 30, unavailable=[(0, 0), (0, 1)])
    b.activity("A", groups=[group], instructors=[b.instructor("T")])
    b.activity("B", groups=[group], instructors=[b.instructor("U")])
    b.activity("C", groups=[group], instructors=[b.instructor("V")])
    problem = b.problem()
    placements = {0: Placement(problem.slot(0, 2), 0), 1: Placement(problem.slot(0, 3), 0)}
    result = explain(evaluator(problem), placements, 2)
    found = {(o.code, o.windows) for o in result.obstacles}
    assert found == {("students_unavailable", 2), ("student_conflict", 2)}
    assert "students of G are unavailable (2 windows)" in result.summary


def test_every_suitable_room_taken() -> None:
    b = SnapshotBuilder(days=1, periods=ONE_DAY)
    b.room("LAB", 30, "LAB")
    for i in range(5):
        b.activity(f"C{i}", groups=[b.group(f"G{i}", 20)], room_type="LAB")
    problem = b.problem()
    placements = {i: Placement(problem.slot(0, i), 0) for i in range(4)}
    result = explain(evaluator(problem), placements, 4)
    assert result.rooms == 1
    assert [(o.code, o.windows) for o in result.obstacles] == [("rooms_busy", 4)]
    assert result.obstacles[0].sessions == (0, 1, 2, 3)


def test_no_suitable_room_at_all() -> None:
    b = SnapshotBuilder(days=1, periods=ONE_DAY)
    b.room("C1", 40)
    b.room("C2", 20)
    b.activity("CS", "LAB", groups=[b.group("G", 24)], room_type="LAB")
    result = explain(evaluator(b.problem()), {}, 0)
    assert result.rooms == 0
    assert result.room_problems == {"room_type": 2, "room_capacity": 1}
    assert result.summary.startswith("CS LAB (G) has no suitable room")


def test_a_session_that_fits_now_says_where() -> None:
    b = SnapshotBuilder(days=1, periods=ONE_DAY)
    b.room("R", 40)
    b.activity("A", groups=[b.group("G", 30)])
    problem = b.problem()
    result = explain(evaluator(problem), {}, 0)
    assert result.free[0] == Placement(problem.slot(0, 0), 0)
    assert len(result.free) == 4
    assert "fits now" in result.summary


def test_a_hard_rule_rules_out_windows() -> None:
    b = SnapshotBuilder(days=1, periods=ONE_DAY)
    b.room("R1", 40)
    b.room("R2", 40)
    group = b.group("G", 30)
    b.activity("A", groups=[group])
    b.activity("B", groups=[group])
    rule = b.rule("max_periods_per_day", params={"limit": 1}, groups=[group])
    problem = b.problem()
    result = explain(evaluator(problem), {0: Placement(problem.slot(0, 0), 0)}, 1)
    rules = [o for o in result.obstacles if o.rule_id == rule]
    assert [(o.code, o.windows) for o in rules] == [("rule:max_periods_per_day", 3)]
    assert "would be broken" in rules[0].message


def test_a_break_limits_the_windows_of_long_sessions() -> None:
    b = SnapshotBuilder(days=1, periods=ONE_DAY, joins=(True, False, True, False))
    b.room("R", 40)
    b.activity("A", groups=[b.group("G", 30)], duration=2)
    result = explain(evaluator(b.problem()), {}, 0)
    assert result.windows == 2
