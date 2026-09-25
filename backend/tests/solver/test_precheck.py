"""Pathological datasets: each must be caught before solving with a message naming the cause."""

from __future__ import annotations

from optiedt.problem.issues import Issue
from optiedt.solver.domains import build_context
from optiedt.solver.precheck import precheck
from tests.snapshot_builder import SnapshotBuilder


def _errors(builder: SnapshotBuilder) -> list[Issue]:
    return [i for i in precheck(build_context(builder.problem())) if i.severity == "error"]


def _codes(builder: SnapshotBuilder) -> set[str]:
    return {i.code for i in _errors(builder)}


def test_sound_instance_has_no_errors() -> None:
    b = SnapshotBuilder()
    b.room("R1", 40)
    g = b.group("G", 30)
    t = b.instructor("T")
    b.activity("C1", groups=[g], instructors=[t], sessions=2)
    assert _errors(b) == []


def test_impossible_room_capacity() -> None:
    b = SnapshotBuilder()
    b.room("SMALL", 20)
    g = b.group("G", 45)
    b.activity("C1", groups=[g], instructors=[b.instructor("T")])
    errors = _errors(b)
    assert [e.code for e in errors] == ["no_compatible_room"]
    assert "45 seats" in errors[0].message
    assert "too small (1)" in errors[0].message


def test_missing_room_feature() -> None:
    b = SnapshotBuilder()
    b.room("LAB", 30, "LAB", features=("COMPUTERS",))
    g = b.group("G", 20)
    b.activity("C1", groups=[g], room_type="LAB", features=("COMPUTERS", "GPU"))
    assert "missing a required feature" in _errors(b)[0].message


def test_instructor_with_zero_availability() -> None:
    b = SnapshotBuilder(days=2)
    b.room("R1", 40)
    everything = [(d, p) for d in range(2) for p in range(4)]
    t = b.instructor("T", unavailable=everything)
    b.activity("C1", groups=[b.group("G", 20)], instructors=[t])
    errors = _errors(b)
    assert {"no_valid_start", "instructor_overbooked"} <= {e.code for e in errors}
    start = next(e for e in errors if e.code == "no_valid_start")
    assert "Dr T is unavailable (8)" in start.message


def test_instructor_teaching_more_than_the_week_allows() -> None:
    b = SnapshotBuilder(days=1)
    for i in range(3):
        b.room(f"R{i}", 40)
    t = b.instructor("T")
    for course in ("C1", "C2", "C3", "C4", "C5"):
        b.activity(course, groups=[b.group(f"G{course}", 20)], instructors=[t])
    errors = [e for e in _errors(b) if e.code == "instructor_overbooked"]
    assert errors[0].figures == {"load": 5, "available": 4}


def test_group_needs_more_periods_than_open() -> None:
    b = SnapshotBuilder(days=1, closed=[(0, 3)])
    b.room("R", 40)
    g = b.group("L1", 30)
    for course in ("C1", "C2", "C3", "C4"):
        b.activity(course, groups=[g], instructors=[b.instructor(course)])
    errors = [e for e in _errors(b) if e.code == "students_overbooked"]
    assert "need 4 periods" in errors[0].message
    assert "3 open periods" in errors[0].message


def test_parent_lecture_counts_against_subgroups() -> None:
    b = SnapshotBuilder(days=1)
    b.room("R1", 100)
    b.room("R2", 40)
    cohort = b.group("L2", 60)
    g1 = b.group("G1", 30, cohort, "tut")
    b.group("G2", 30, cohort, "tut")
    for course in ("C1", "C2", "C3"):
        b.activity(course, groups=[cohort], instructors=[b.instructor(course)])
    b.activity("C4", groups=[g1], instructors=[b.instructor("X")])
    b.activity("C5", groups=[g1], instructors=[b.instructor("Y")])
    assert "students_overbooked" in _codes(b)


def test_all_rooms_of_a_type_occupied() -> None:
    b = SnapshotBuilder(days=1)
    b.room("LAB1", 30, "LAB")
    for i in range(5):
        b.activity(
            f"C{i}",
            groups=[b.group(f"G{i}", 20)],
            instructors=[b.instructor(f"T{i}")],
            room_type="LAB",
        )
    errors = [e for e in _errors(b) if e.code == "rooms_overbooked"]
    assert errors[0].figures == {"demand": 5, "supply": 4}
    assert "LAB1" in errors[0].message


def test_room_unavailability_reduces_supply() -> None:
    b = SnapshotBuilder(days=1)
    b.room("LAB1", 30, "LAB", unavailable=[(0, 0), (0, 1)])
    for i in range(3):
        b.activity(
            f"C{i}",
            groups=[b.group(f"G{i}", 20)],
            instructors=[b.instructor(f"T{i}")],
            room_type="LAB",
        )
    assert "rooms_overbooked" in _codes(b)


def test_double_periods_need_uninterrupted_windows() -> None:
    # Two periods before lunch, two after: a room offers two 2-period windows per day.
    b = SnapshotBuilder(days=1, joins=(True, False, True, False))
    b.room("LAB1", 30, "LAB")
    for i in range(3):
        b.activity(
            f"C{i}",
            groups=[b.group(f"G{i}", 20)],
            instructors=[b.instructor(f"T{i}")],
            room_type="LAB",
            duration=2,
        )
    errors = [e for e in _errors(b) if e.code in ("room_windows_short", "rooms_overbooked")]
    assert errors
    assert errors[0].code == "rooms_overbooked"  # 6 periods needed, 4 offered


def test_window_shortage_detected_when_total_fits() -> None:
    # Three periods per day with a break after P2: each day holds one 2-period window.
    b = SnapshotBuilder(
        days=2,
        periods=(("08:00", "09:00"), ("09:00", "10:00"), ("11:00", "12:00")),
        joins=(True, False, False),
    )
    b.room("LAB1", 30, "LAB")
    for i in range(3):
        b.activity(
            f"C{i}",
            groups=[b.group(f"G{i}", 20)],
            instructors=[b.instructor(f"T{i}")],
            room_type="LAB",
            duration=2,
        )
    errors = [e for e in _errors(b) if e.code == "room_windows_short"]
    assert errors[0].figures == {"sessions": 3, "windows": 2}


def test_impossible_duration() -> None:
    b = SnapshotBuilder(joins=(True, False, True, False))
    b.room("R", 40)
    b.activity("C1", groups=[b.group("G", 20)], duration=3)
    errors = _errors(b)
    assert errors[0].code == "no_valid_start"
    assert "run across a break" in errors[0].message


def test_fixed_assignment_conflict() -> None:
    b = SnapshotBuilder()
    room = b.room("AMPHI", 200)
    t = b.instructor("T")
    b.activity("C1", groups=[b.group("G1", 50)], instructors=[t], fixed=[(1, 0, 0, room)])
    b.activity("C2", groups=[b.group("G2", 50)], instructors=[t], fixed=[(1, 0, 0, None)])
    errors = [e for e in _errors(b) if e.code == "fixed_collision"]
    assert "an instructor" in errors[0].message


def test_fixed_assignment_on_closed_slot() -> None:
    b = SnapshotBuilder(closed=[(2, 2)])
    b.room("R", 40)
    b.activity("C1", groups=[b.group("G", 20)], fixed=[(1, 2, 2, None)])
    errors = _errors(b)
    assert errors[0].code == "no_valid_start"
    assert "fixed placement" in errors[0].message


def test_sessions_need_more_days_than_possible() -> None:
    b = SnapshotBuilder(days=5)
    b.room("R", 40)
    t = b.instructor("T", unavailable=[(d, p) for d in (2, 3, 4) for p in range(4)])
    b.activity("C1", groups=[b.group("G", 20)], instructors=[t], sessions=3)
    assert "not_enough_days" in _codes(b)


def test_conflicting_hard_rules() -> None:
    b = SnapshotBuilder(days=5)
    for i in range(3):
        b.room(f"R{i}", 40)
    t = b.instructor("T")
    for course in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"):
        b.activity(course, groups=[b.group(f"G{course}", 20)], instructors=[t])
    b.rule("max_days_per_week", params={"limit": 2}, instructors=[t])
    errors = [e for e in _errors(b) if e.code == "rule_below_load"]
    assert errors[0].figures == {"load": 9, "capacity": 8}


def test_hard_avoid_slots_rule_restricts_domain() -> None:
    b = SnapshotBuilder(days=1)
    b.room("R", 40)
    g = b.group("G", 20)
    b.activity("C1", groups=[g])
    b.rule("avoid_slots", params={"slots": [(0, 0), (0, 1), (0, 2), (0, 3)]}, groups=[g])
    assert "no_valid_start" in _codes(b)


def test_tight_pool_is_a_warning() -> None:
    b = SnapshotBuilder(days=1)
    b.room("LAB1", 30, "LAB")
    for i in range(4):
        b.activity(
            f"C{i}",
            groups=[b.group(f"G{i}", 20)],
            instructors=[b.instructor(f"T{i}")],
            room_type="LAB",
        )
    issues = precheck(build_context(b.problem()))
    assert [i.code for i in issues if i.severity == "warning"] == ["rooms_tight"]
