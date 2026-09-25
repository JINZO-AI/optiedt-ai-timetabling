"""Solver behaviour, always checked by the independent evaluator."""

from __future__ import annotations

import time

import pytest

from optiedt.problem.model import Problem
from optiedt.problem.solution import Placement
from optiedt.solver.engine import EngineResult
from tests.snapshot_builder import SnapshotBuilder
from tests.solver.helpers import evaluate, remap, solve

pytestmark = pytest.mark.solver


def _department(b: SnapshotBuilder) -> None:
    """Two cohorts with tutorial groups, shared lecture halls, labs and instructors."""
    b.room("AMPHI", 150, "HALL")
    for i in range(4):
        b.room(f"S{i}", 40)
    b.room("LAB1", 24, "LAB")
    b.room("LAB2", 24, "LAB")
    teachers = [b.instructor(f"T{i}") for i in range(6)]
    for cohort_index, cohort_code in enumerate(("L1", "L2")):
        cohort = b.group(cohort_code, 90)
        groups = [b.group(f"{cohort_code}-G{k}", 30, cohort, "tut") for k in range(3)]
        for course in range(3):
            lecturer = teachers[(cohort_index * 3 + course) % 6]
            b.activity(
                f"{cohort_code}-C{course}",
                "LEC",
                groups=[cohort],
                instructors=[lecturer],
                room_type="HALL",
                sessions=2,
            )
            for k, group in enumerate(groups):
                tutor = teachers[(cohort_index + course + k) % 6]
                b.activity(f"{cohort_code}-C{course}", "TUT", groups=[group], instructors=[tutor])
        for k, group in enumerate(groups):
            b.activity(
                f"{cohort_code}-LAB",
                "LAB",
                groups=[group],
                instructors=[teachers[k]],
                room_type="LAB",
                duration=2,
                seats=22,
            )


def test_complete_valid_timetable_and_matching_tier_values() -> None:
    b = SnapshotBuilder()
    _department(b)
    problem = b.problem()
    result = solve(problem, ("balanced", "student_centred"))
    assert result.tier0.value == 0
    for outcome in result.profiles:
        evaluation = evaluate(problem, outcome.placements, outcome.code)
        assert evaluation.valid, [v.message for v in evaluation.violations][:5]
        for tier in outcome.tiers:
            assert tier.value == evaluation.tiers[tier.tier], (outcome.code, tier)


def test_overloaded_instance_returns_best_partial_timetable() -> None:
    b = SnapshotBuilder(days=1)
    b.room("LAB1", 30, "LAB")
    for i in range(6):
        b.activity(
            f"C{i}",
            groups=[b.group(f"G{i}", 20)],
            instructors=[b.instructor(f"T{i}")],
            room_type="LAB",
        )
    problem = b.problem()
    result = solve(problem, seconds=3)
    assert result.tier0.value == 2  # four periods, six sessions
    assert result.tier0.proven_optimal
    evaluation = evaluate(problem, result.profiles[0].placements)
    assert evaluation.violations == []
    assert evaluation.unscheduled_periods == 2
    assert not evaluation.complete


def test_every_hard_rule_is_respected() -> None:
    b = SnapshotBuilder(joins=(True, False, True, False))
    for i in range(3):
        b.room(f"R{i}", 40)
    t = b.instructor("T")
    u = b.instructor("U")
    g = b.group("G", 30)
    h = b.group("H", 30)
    lecture = b.activity("LEC", groups=[g], instructors=[t], sessions=2)
    tutorial = b.activity("TUT", groups=[g], instructors=[u], sessions=2)
    other = b.activity("OTH", groups=[h], instructors=[t], sessions=3)
    lab = b.activity("LAB", groups=[h], instructors=[u])
    b.rule("max_periods_per_day", params={"limit": 1}, instructors=[t])
    b.rule("max_days_per_week", params={"limit": 3}, instructors=[u])
    b.rule("break_in_window", params={"periods": [1, 2], "min_free": 1}, groups=[g])
    b.rule("precedence", activities=[lecture, tutorial], ordered=True)
    b.rule("consecutive", activities=[other, lab], ordered=True)
    b.rule("min_days_between", params={"days": 2}, activities=[other])
    b.rule("avoid_slots", params={"slots": [(0, 0), (1, 0)]}, groups=[h])
    b.rule("latest_end", params={"period": 2}, instructors=[u])
    problem = b.problem()
    result = solve(problem, seconds=5)
    placements = result.profiles[0].placements
    evaluation = evaluate(problem, placements)
    assert evaluation.violations == []
    assert evaluation.complete


def test_known_optimum_for_student_idle_time() -> None:
    # Four one-period sessions for one group, at most two a day over two days: both days
    # can be gap-free.
    b = SnapshotBuilder(days=2)
    for i in range(4):
        b.room(f"R{i}", 40)
    g = b.group("G", 30)
    for i in range(4):
        b.activity(f"C{i}", groups=[g], instructors=[b.instructor(f"T{i}")])
    b.rule("max_periods_per_day", params={"limit": 2}, groups=[g])
    problem = b.problem()
    result = solve(problem, ("student_centred",), seconds=5)
    evaluation = evaluate(problem, result.profiles[0].placements, "student_centred")
    assert evaluation.objective_values["student_idle"] == 0
    assert result.profiles[0].tiers[0].proven_optimal


def _changed_department(close: str, slots: list[tuple[int, int]], spare: bool) -> Problem:
    b = SnapshotBuilder()
    _department(b)
    if spare:
        b.room("S9", 40)
    b._rooms = [
        room.model_copy(update={"unavailable": slots}) if room.code == close else room
        for room in b._rooms
    ]
    return b.problem()


def _busiest(problem: Problem, placements: dict[int, Placement], prefix: str = "") -> str:
    rooms = [r for r in problem.rooms if r.code.startswith(prefix)]
    return max(rooms, key=lambda r: sum(p.room == r.index for p in placements.values())).code


def test_repair_with_a_spare_room_only_changes_rooms() -> None:
    b = SnapshotBuilder()
    _department(b)
    problem = b.problem()
    first = solve(problem, seconds=5).profiles[0].placements
    # A classroom closes for the whole week and an identical spare room becomes available:
    # the least disruptive repair moves each of its sessions to the spare room, same time.
    closed = _busiest(problem, first, "S")
    week = [(d, q) for d in range(5) for q in range(4)]
    changed = _changed_department(closed, week, spare=True)
    reference = remap(problem, changed, first)
    blocked = next(r.index for r in changed.rooms if r.code == closed)
    affected = [s for s, p in reference.items() if p.room == blocked]
    assert affected

    result = solve(changed, seconds=5, reference=reference)
    repaired = result.profiles[0].placements
    after = evaluate(changed, repaired, reference=reference)
    assert after.valid
    assert after.complete
    assert result.profiles[0].tiers[0].proven_optimal
    assert after.objective_values["stability"] == len(affected)
    for s, placement in reference.items():
        assert repaired[s].slot == placement.slot, "no session needed a new time"


def test_full_repair_is_never_worse_than_moving_only_affected_sessions() -> None:
    b = SnapshotBuilder()
    _department(b)
    problem = b.problem()
    first = solve(problem, seconds=5).profiles[0].placements
    # The busiest room closes on Monday and Tuesday; other sessions may have to make way.
    closed = _busiest(problem, first)
    changed = _changed_department(closed, [(d, q) for d in (0, 1) for q in range(4)], spare=False)
    reference = remap(problem, changed, first)
    blocked = next(r.index for r in changed.rooms if r.code == closed)
    affected = {s for s, p in reference.items() if p.room == blocked and changed.day_of(p.slot) < 2}
    assert affected
    untouched = {s: p for s, p in reference.items() if s not in affected}

    full = solve(changed, seconds=12, reference=reference)
    restricted = solve(changed, seconds=12, reference=reference, pins=untouched)
    assert full.tier0.proven_optimal
    assert full.profiles[0].tiers[0].proven_optimal

    def rank(result: EngineResult) -> tuple[int, int]:
        evaluation = evaluate(changed, result.profiles[0].placements, reference=reference)
        assert evaluation.violations == []
        return evaluation.unscheduled_periods, evaluation.objective_values["stability"]

    assert rank(full) <= rank(restricted)
    for s, placement in untouched.items():
        assert restricted.profiles[0].placements.get(s) == placement


def test_cancellation_stops_promptly() -> None:
    b = SnapshotBuilder()
    _department(b)
    problem = b.problem()
    started = time.monotonic()
    deadline = started + 1.0
    result = solve(
        problem,
        ("balanced", "student_centred", "instructor_centred"),
        seconds=60,
        should_stop=lambda: time.monotonic() > deadline,
    )
    assert time.monotonic() - started < 10
    assert result.cancelled


def test_pins_are_kept_and_invalid_pins_are_reported() -> None:
    from optiedt.solver.model import PinError

    b = SnapshotBuilder(closed=[(4, 3)])
    _department(b)
    problem = b.problem()
    pinned = {0: Placement(problem.slot(2, 1), problem.room_index[b._rooms[0].id])}
    result = solve(problem, seconds=4, pins=pinned)
    assert result.profiles[0].placements[0] == pinned[0]
    with pytest.raises(PinError, match="cannot stay"):
        solve(problem, seconds=2, pins={0: Placement(problem.slot(4, 3), None)})
