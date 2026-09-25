from __future__ import annotations

from optiedt.evaluation.evaluator import Evaluator
from optiedt.evaluation.types import ObjectiveConfig, Placement
from optiedt.problem.model import Problem
from optiedt.problem.snapshot import SProfile
from tests.snapshot_builder import SnapshotBuilder


def _evaluator(problem: Problem, reference: dict[int, Placement] | None = None) -> Evaluator:
    profile: SProfile = next(p for p in problem.snapshot.profiles if p.code == "balanced")
    return Evaluator(problem, ObjectiveConfig.from_profile(profile, reference))


def _codes(problem: Problem, placements: dict[int, Placement]) -> list[str]:
    return sorted(v.code for v in _evaluator(problem).evaluate(placements).violations)


def test_valid_timetable() -> None:
    b = SnapshotBuilder()
    r = b.room("R1", 40)
    g = b.group("G", 30)
    t = b.instructor("T")
    b.activity("C1", groups=[g], instructors=[t], sessions=2)
    problem = b.problem()
    room = problem.room_index[r]
    evaluation = _evaluator(problem).evaluate({0: Placement(0, room), 1: Placement(5, room)})
    assert evaluation.valid
    assert evaluation.objective_values["unscheduled"] == 0
    assert evaluation.objective_values["room_fit"] == 2 * (40 - 30)
    assert evaluation.objective_values["start_consistency"] == 1  # P1 and P2 differ
    _ = g, t


def test_unscheduled_sessions_make_it_incomplete() -> None:
    b = SnapshotBuilder()
    b.room("R1", 40)
    b.activity("C1", groups=[b.group("G", 30)], duration=2)
    evaluation = _evaluator(b.problem()).evaluate({})
    assert not evaluation.complete
    assert evaluation.unscheduled_periods == 2
    assert evaluation.tiers[0] == 2


def test_instructor_student_and_room_conflicts() -> None:
    b = SnapshotBuilder()
    r = b.room("R1", 100)
    t = b.instructor("T")
    cohort = b.group("L2", 60)
    g1 = b.group("G1", 30, cohort, "tut")
    b.activity("C1", groups=[cohort], instructors=[t])
    b.activity("C2", groups=[g1], instructors=[t])
    problem = b.problem()
    room = problem.room_index[r]
    codes = _codes(problem, {0: Placement(0, room), 1: Placement(0, room)})
    assert codes == ["instructor_conflict", "room_conflict", "student_conflict"]


def test_disjoint_subgroups_may_run_in_parallel() -> None:
    b = SnapshotBuilder()
    r1, r2 = b.room("R1", 40), b.room("R2", 40)
    cohort = b.group("L2", 60)
    g1 = b.group("G1", 30, cohort, "tut")
    g2 = b.group("G2", 30, cohort, "tut")
    b.activity("C1", groups=[g1], instructors=[b.instructor("A")])
    b.activity("C2", groups=[g2], instructors=[b.instructor("B")])
    problem = b.problem()
    placements = {0: Placement(0, problem.room_index[r1]), 1: Placement(0, problem.room_index[r2])}
    assert _codes(problem, placements) == []


def test_placement_violations_name_the_cause() -> None:
    b = SnapshotBuilder(closed=[(0, 2)], joins=(True, False, True, False))
    small = b.room("SMALL", 10)
    lab = b.room("LAB", 40, "LAB")
    t = b.instructor("T", unavailable=[(1, 0)])
    g = b.group("G", 30, unavailable=[(3, 0)])
    b.activity("C1", groups=[g], instructors=[t], duration=2)
    problem = b.problem()
    ev = _evaluator(problem)
    small_i, lab_i = problem.room_index[small], problem.room_index[lab]
    assert {v.code for v in ev.placement_violations(0, Placement(problem.slot(0, 2), small_i))} == {
        "slot_closed",
        "room_capacity",
    }
    assert {v.code for v in ev.placement_violations(0, Placement(problem.slot(2, 1), lab_i))} == {
        "crosses_break",
        "room_type",
    }
    unavailable = ev.placement_violations(0, Placement(problem.slot(1, 0), None))
    assert {v.code for v in unavailable} == {"instructor_unavailable", "room_missing"}
    assert "Dr T is unavailable at Tue P1" in unavailable[0].message
    students = ev.placement_violations(0, Placement(problem.slot(3, 0), small_i))
    assert "students_unavailable" in {v.code for v in students}


def test_parent_group_unavailability_blocks_subgroup_sessions() -> None:
    b = SnapshotBuilder()
    r = b.room("R", 40)
    cohort = b.group("L2", 60, unavailable=[(2, 2)])
    g1 = b.group("G1", 30, cohort, "tut")
    b.activity("C1", groups=[g1])
    problem = b.problem()
    violations = _evaluator(problem).placement_violations(
        0, Placement(problem.slot(2, 2), problem.room_index[r])
    )
    assert [v.code for v in violations] == ["students_unavailable"]


def test_online_sessions_take_no_room_but_still_conflict() -> None:
    b = SnapshotBuilder()
    r = b.room("R", 40)
    t = b.instructor("T")
    b.activity("C1", groups=[b.group("G1", 30)], instructors=[t], online=True)
    b.activity("C2", groups=[b.group("G2", 30)], instructors=[t])
    problem = b.problem()
    room = problem.room_index[r]
    assert _codes(problem, {0: Placement(0, room), 1: Placement(1, room)}) == ["room_for_online"]
    assert _codes(problem, {0: Placement(0, None), 1: Placement(0, room)}) == [
        "instructor_conflict"
    ]


def test_different_days_and_fixed_placements() -> None:
    b = SnapshotBuilder()
    r = b.room("R", 40)
    b.activity("C1", groups=[b.group("G", 30)], sessions=2, fixed=[(1, 4, 3, None)])
    problem = b.problem()
    room = problem.room_index[r]
    codes = _codes(
        problem, {0: Placement(problem.slot(0, 0), room), 1: Placement(problem.slot(0, 2), room)}
    )
    assert codes == ["fixed_moved", "same_day_occurrences"]


def test_student_idle_counts_open_gaps_only() -> None:
    b = SnapshotBuilder(days=1, closed=[(0, 1)])
    r1, r2 = b.room("R1", 40), b.room("R2", 40)
    g = b.group("G", 30)
    b.activity("C1", groups=[g])
    b.activity("C2", groups=[g])
    problem = b.problem()
    ev = _evaluator(problem)
    # P1 and P4 used; P2 closed, P3 free → one idle period
    evaluation = ev.evaluate(
        {0: Placement(0, problem.room_index[r1]), 1: Placement(3, problem.room_index[r2])}
    )
    assert evaluation.objective_values["student_idle"] == 1
    assert evaluation.contributors["student_idle"] == [("G", 1)]


def test_instructor_preferences_and_days() -> None:
    b = SnapshotBuilder(days=3)
    r = b.room("R", 40)
    t = b.instructor("T", undesirable=[(0, 0)], preferred=[(1, 0), (1, 1)])
    b.activity("C1", groups=[b.group("G1", 20)], instructors=[t])
    b.activity("C2", groups=[b.group("G2", 20)], instructors=[t])
    problem = b.problem()
    room = problem.room_index[r]
    values = (
        _evaluator(problem)
        .evaluate({0: Placement(problem.slot(0, 0), room), 1: Placement(problem.slot(1, 0), room)})
        .objective_values
    )
    assert values["instructor_undesirable"] == 1
    assert values["instructor_preferred"] == 1  # Monday P1 is outside the preferred slots
    assert values["instructor_days"] == 1  # two days used, one would do


def test_room_preferences_and_stability() -> None:
    b = SnapshotBuilder()
    good, other = b.room("GOOD", 40), b.room("OTHER", 40)
    b.activity(
        "C1", groups=[b.group("G", 30)], sessions=2, preferred_rooms=[good], avoided_rooms=[other]
    )
    problem = b.problem()
    g, o = problem.room_index[good], problem.room_index[other]
    values = _evaluator(problem).evaluate({0: Placement(0, g), 1: Placement(5, o)}).objective_values
    assert values["room_preferences"] == 2  # one outside preferred, which is also avoided
    assert values["room_stability"] == 1


def test_stability_counts_moves_against_reference_as_multisets() -> None:
    b = SnapshotBuilder()
    r1, r2 = b.room("R1", 40), b.room("R2", 40)
    b.activity("C1", groups=[b.group("G", 30)], sessions=2)
    problem = b.problem()
    a, c = problem.room_index[r1], problem.room_index[r2]
    reference = {0: Placement(0, a), 1: Placement(8, a)}
    ev = _evaluator(problem, reference)
    # Swapping which occurrence sits where is not a change.
    swapped = ev.evaluate({0: Placement(8, a), 1: Placement(0, a)}).objective_values
    assert swapped["stability"] == 0
    moved = ev.evaluate({0: Placement(0, a), 1: Placement(9, c)}).objective_values
    assert moved["stability"] == 3 * 1 + 1  # one time move, one room move


def test_hard_and_soft_rules() -> None:
    b = SnapshotBuilder(days=1, joins=(True, False, True, False))
    rooms = [b.room(f"R{i}", 40) for i in range(4)]
    t = b.instructor("T")
    g = b.group("G", 30)
    for i in range(4):
        b.activity(f"C{i}", groups=[b.group(f"S{i}", 10)], instructors=[t])
    b.rule("max_consecutive_periods", params={"limit": 2}, instructors=[t], enforcement="hard")
    b.rule(
        "max_periods_per_day",
        params={"limit": 3},
        instructors=[t],
        enforcement="soft",
        tier=2,
        weight=4,
    )
    problem = b.problem()
    placements = {i: Placement(i, problem.room_index[rooms[i]]) for i in range(4)}
    evaluation = _evaluator(problem).evaluate(placements)
    # P1-P2 then a break, P3-P4: no run longer than 2 → hard rule holds
    assert evaluation.violations == []
    soft = next(r for r in problem.rules if r.enforcement == "soft")
    assert evaluation.rule_values[soft.id] == 1
    assert evaluation.tiers[2] >= 4
    _ = g


def test_consecutive_run_limit_with_joined_periods() -> None:
    b = SnapshotBuilder(days=1, joins=(True, True, True, False))
    rooms = [b.room(f"R{i}", 40) for i in range(4)]
    t = b.instructor("T")
    for i in range(4):
        b.activity(f"C{i}", groups=[b.group(f"S{i}", 10)], instructors=[t])
    b.rule("max_consecutive_periods", params={"limit": 2}, instructors=[t])
    problem = b.problem()
    placements = {i: Placement(i, problem.room_index[rooms[i]]) for i in range(4)}
    assert _codes(problem, placements) == ["rule:max_consecutive_periods"]


def test_pair_rules() -> None:
    b = SnapshotBuilder()
    r1, r2 = b.room("R1", 40), b.room("R2", 40)
    g = b.group("G", 30)
    lecture = b.activity("LEC", groups=[g])
    lab = b.activity("LAB", groups=[g])
    b.rule("precedence", activities=[lecture, lab], ordered=True, enforcement="soft", tier=1)
    b.rule("consecutive", activities=[lecture, lab], ordered=True, enforcement="soft", tier=1)
    problem = b.problem()
    ev = _evaluator(problem)
    a, c = problem.room_index[r1], problem.room_index[r2]
    good = ev.evaluate({0: Placement(0, a), 1: Placement(1, c)})
    assert sum(good.rule_values.values()) == 0
    bad = ev.evaluate({0: Placement(3, a), 1: Placement(0, c)})
    assert sorted(bad.rule_values.values()) == [1, 1]


def test_campus_travel() -> None:
    b = SnapshotBuilder(days=1, periods=(("08:00", "09:00"), ("09:10", "10:10")))
    b.campus("NORTH")
    b.travel("MAIN", "NORTH", 30)
    here, there = b.room("M1", 40), b.room("N1", 40, campus="NORTH")
    t = b.instructor("T")
    b.activity("C1", groups=[b.group("G1", 20)], instructors=[t])
    b.activity("C2", groups=[b.group("G2", 20)], instructors=[t])
    b.rule("campus_travel", instructors=[t])
    problem = b.problem()
    placements = {
        0: Placement(0, problem.room_index[here]),
        1: Placement(1, problem.room_index[there]),
    }
    assert _codes(problem, placements) == ["rule:campus_travel"]


def test_move_reports_conflicts_and_deltas() -> None:
    b = SnapshotBuilder(days=1)
    r1, r2 = b.room("R1", 40), b.room("R2", 40)
    t = b.instructor("T")
    g = b.group("G", 30)
    b.activity("C1", groups=[g], instructors=[t])
    b.activity("C2", groups=[b.group("H", 30)], instructors=[t])
    problem = b.problem()
    ev = _evaluator(problem)
    a, c = problem.room_index[r1], problem.room_index[r2]
    current = {0: Placement(0, a), 1: Placement(1, c)}
    clash = ev.evaluate_move(current, 1, Placement(0, c))
    assert [v.code for v in clash.violations] == ["instructor_conflict"]
    fine = ev.evaluate_move(current, 1, Placement(3, c))
    assert fine.feasible
    assert fine.objective_deltas["instructor_idle"] == 2  # P2 and P3 become idle


def test_suggestions_rank_valid_options_and_explain_blocked_ones() -> None:
    from optiedt.evaluation.suggest import options_for, rank

    b = SnapshotBuilder(days=1)
    lab, hall = b.room("LAB", 30, "LAB"), b.room("HALL", 200, "HALL")
    t = b.instructor("T", unavailable=[(0, 3)])
    g = b.group("G", 25)
    b.activity("C1", groups=[g], instructors=[t], room_type="LAB")
    b.activity("C2", groups=[b.group("H", 25)], instructors=[b.instructor("U")], room_type="LAB")
    problem = b.problem()
    ev = _evaluator(problem)
    lab_i = problem.room_index[lab]
    placements = {0: Placement(0, lab_i), 1: Placement(1, lab_i)}
    valid, blocked = rank(options_for(ev, placements, 0))
    assert [o.placement.slot for o in valid] == [0, 2]  # P2 taken by C2, P4 instructor away
    assert valid[0].is_current
    reasons = {v.code for o in blocked for v in o.violations}
    assert reasons == {"room_conflict", "instructor_unavailable"}
    assert all(o.placement.room == lab_i for o in valid + blocked)  # the hall is the wrong type
    _ = hall


def test_diff_ignores_occurrence_swaps() -> None:
    from optiedt.evaluation.diff import diff

    b = SnapshotBuilder()
    r1, r2 = b.room("R1", 40), b.room("R2", 40)
    b.activity("C1", groups=[b.group("G", 30)], sessions=3)
    problem = b.problem()
    a, c = problem.room_index[r1], problem.room_index[r2]
    before = {0: Placement(0, a), 1: Placement(4, a), 2: Placement(8, a)}
    after = {0: Placement(8, a), 1: Placement(0, a), 2: Placement(9, c)}
    changes = diff(problem, before, after)
    assert [(c.kind, c.before, c.after) for c in changes] == [
        ("moved", Placement(4, a), Placement(9, c))
    ]


def test_rules_sharing_a_name_are_reported_separately() -> None:
    b = SnapshotBuilder(days=2)
    b.room("R", 40)
    group = b.group("G", 30)
    b.activity("A", groups=[group], sessions=2)
    first = b.rule("max_days_per_week", params={"limit": 1}, groups=[group])
    second = b.rule("max_days_per_week", params={"limit": 1}, groups=[group])
    problem = b.problem()
    evaluation = Evaluator(problem, ObjectiveConfig({})).evaluate(
        {0: Placement(problem.slot(0, 0), 0), 1: Placement(problem.slot(1, 0), 0)}
    )
    assert {v.rule_id for v in evaluation.violations} == {first, second}
