"""Evaluating one move incrementally must equal the difference of two full evaluations."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from optiedt.evaluation.evaluator import Evaluator
from optiedt.evaluation.types import ObjectiveConfig, Placement
from optiedt.problem.model import Problem
from tests.snapshot_builder import SnapshotBuilder


def _problem(seed: int) -> Problem:
    b = SnapshotBuilder(days=3, joins=(True, False, True, False), penalties={(2, 3): 2})
    b.campus("NORTH")
    b.travel("MAIN", "NORTH", 20)
    rooms = [b.room("R1", 40), b.room("R2", 60), b.room("N1", 40, campus="NORTH")]
    teachers = [
        b.instructor("A", undesirable=[(0, 0)], preferred=[(1, 1)]),
        b.instructor("B", unavailable=[(2, 0)]),
    ]
    cohort = b.group("L2", 60)
    g1 = b.group("G1", 30, cohort, "tut")
    g2 = b.group("G2", 30, cohort, "tut")
    en = b.group("EN", 40, cohort, "lang")
    lec = b.activity(
        "LEC", groups=[cohort], instructors=[teachers[0]], sessions=2, preferred_rooms=[rooms[1]]
    )
    tut = b.activity("TUT", groups=[g1], instructors=[teachers[1]], duration=2)
    b.activity("TUT", groups=[g2], instructors=[teachers[1]])
    b.activity("ENG", groups=[en], instructors=[teachers[0]], online=seed % 2 == 0)
    b.rule(
        "max_periods_per_day",
        params={"limit": 2},
        groups=[cohort],
        enforcement="soft",
        tier=2,
        weight=3,
    )
    b.rule(
        "break_in_window",
        params={"periods": [1, 2], "min_free": 1},
        instructors=[teachers[0]],
        enforcement="soft",
        tier=3,
    )
    b.rule("precedence", activities=[lec, tut], ordered=True, enforcement="soft", tier=1)
    b.rule("campus_travel", instructors=[teachers[1]], enforcement="soft", tier=2)
    b.rule("avoid_slots", params={"slots": [(1, 3)]}, groups=[g1], enforcement="hard")
    return b.problem()


placement = st.tuples(
    st.integers(min_value=0, max_value=11), st.one_of(st.none(), st.integers(0, 2))
)


@settings(max_examples=200, deadline=None)
@given(
    seed=st.integers(0, 1),
    assignment=st.dictionaries(st.integers(0, 4), placement, max_size=5),
    moved=st.integers(0, 4),
    target=st.one_of(st.none(), placement),
    with_reference=st.booleans(),
)
def test_move_equals_difference_of_full_evaluations(
    seed: int,
    assignment: dict[int, tuple[int, int | None]],
    moved: int,
    target: tuple[int, int | None] | None,
    with_reference: bool,
) -> None:
    problem = _problem(seed)
    placements = {s: Placement(slot, room) for s, (slot, room) in assignment.items()}
    reference = {0: Placement(0, 1), 1: Placement(4, 1)} if with_reference else None
    profile = next(p for p in problem.snapshot.profiles if p.code == "balanced")
    evaluator = Evaluator(problem, ObjectiveConfig.from_profile(profile, reference))

    target_placement = Placement(*target) if target is not None else None
    after = dict(placements)
    if target_placement is None:
        after.pop(moved, None)
    else:
        after[moved] = target_placement

    full_before = evaluator.evaluate(placements)
    full_after = evaluator.evaluate(after)
    move = evaluator.evaluate_move(placements, moved, target_placement)

    for code, value in full_after.objective_values.items():
        assert move.objective_deltas[code] == value - full_before.objective_values[code], code
    for rule_id, value in full_after.rule_values.items():
        assert move.rule_deltas.get(rule_id, 0) == value - full_before.rule_values[rule_id], rule_id
    assert move.tier_deltas == [
        a - b for a, b in zip(full_after.tiers, full_before.tiers, strict=True)
    ]

    # Every hard problem involving the moved session in the full evaluation is reported.
    if target_placement is not None:
        involving = {
            v.code
            for v in full_after.violations
            if moved in v.sessions and not v.code.startswith("rule:")
        }
        reported = {v.code for v in move.violations}
        assert involving <= reported
