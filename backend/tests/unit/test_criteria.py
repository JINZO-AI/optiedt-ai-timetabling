"""The seven criterion formulas, against a hand-computable instance.

This is the gap the property tests cannot cover. tests/property/ generates
synthetic SubScore values and checks that the scoring ARITHMETIC is exact and
stable - it never calls a Criterion, so an outright wrong formula (S2 counting
the wrong resource, S5 missing a 2-period session's second period, S7 counting
per promotion instead of per leaf group) would leave every property test
green.

The instance below is deliberately tiny and irregular enough to distinguish
the formulas from each other: a full promotion/TD/TP chain so S2 and S7 exercise
ancestor-or-self, two days so S4 has something to measure, and two room types so
S6 has a per-type target. Every expected value is computed by hand in the test
that asserts it - see docs/open-questions.md, C-4 for the definitions.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from optiedt.analysis.criteria import build_criteria
from optiedt.analysis.instance_view import build_instance_view
from optiedt.domain.entities import Candidate, Placement
from optiedt.domain.instance import Instance


@pytest.fixture
def instance(tiny_instance: Instance) -> Instance:
    """Alias for the shared fixture - see tests/conftest.py."""
    return tiny_instance


def _candidate(placements: dict[str, tuple[int, str]]) -> Candidate:
    return Candidate(
        id="c",
        run="r",
        profile_name="p",
        cost=0,
        score=0.0,
        placements=tuple(
            Placement(session=sid, slot=slot, room=room) for sid, (slot, room) in placements.items()
        ),
        sub_scores=(),
    )


def _by_code(instance: Instance) -> dict[str, object]:
    return {c.code: c for c in build_criteria(instance)}


def test_leaf_group_is_the_only_one_and_inherits_its_ancestors_sessions(instance):
    """S2/S7/S10 all rest on this: T is the only leaf, and all three sessions
    reach it through the promotion -> TD -> TP chain."""
    view = build_instance_view(instance)
    assert view.leaf_groups == ("T",)
    assert set(view.sessions_for_leaf_group["T"]) == {"s_leaf", "s_mid", "s_top"}


def test_lunch_period_is_derived_from_the_clock_not_hardcoded(instance):
    """S10 depends on this. Period 2 (11:50-13:20) is the one straddling noon."""
    assert build_instance_view(instance).lunch_period_index == 2


def test_s2_counts_gaps_in_the_leaf_groups_day(instance):
    """Day 0 periods {0, 2, 4} occupied -> span 5, occupied 3, idle 2."""
    candidate = _candidate({"s_leaf": (0, "R1"), "s_mid": (2, "R1"), "s_top": (4, "R1")})
    assert _by_code(instance)["S2"].raw_value(candidate) == 2.0


def test_s2_is_zero_when_the_day_is_contiguous(instance):
    candidate = _candidate({"s_leaf": (0, "R1"), "s_mid": (1, "R1"), "s_top": (2, "R1")})
    assert _by_code(instance)["S2"].raw_value(candidate) == 0.0


def test_s3_counts_per_teacher_and_ignores_the_group_hierarchy(instance):
    """T1 holds s_leaf and s_mid; placing them at periods 0 and 3 leaves 2 idle.
    T2's single session cannot create a gap, so the total is exactly 2 - which
    is what distinguishes S3 from S2 on the same placement."""
    candidate = _candidate({"s_leaf": (0, "R1"), "s_mid": (3, "R1"), "s_top": (1, "R2")})
    assert _by_code(instance)["S3"].raw_value(candidate) == 2.0


def test_s4_counts_days_beyond_the_minimum_the_load_needs(instance):
    """T1 has 2 one-period sessions, so ceil(2/5) = 1 day suffices. Spreading
    them over both days costs exactly 1 extra day."""
    criteria = _by_code(instance)
    same_day = _candidate({"s_leaf": (0, "R1"), "s_mid": (1, "R1"), "s_top": (2, "R1")})
    spread = _candidate({"s_leaf": (0, "R1"), "s_mid": (5, "R1"), "s_top": (2, "R1")})
    assert criteria["S4"].raw_value(same_day) == 0.0
    assert criteria["S4"].raw_value(spread) == 1.0


def test_s5_counts_sessions_touching_the_first_or_last_period(instance):
    """Periods 0 and 4 are the edges; period 1-3 placements are free."""
    criteria = _by_code(instance)
    middle = _candidate({"s_leaf": (1, "R1"), "s_mid": (2, "R1"), "s_top": (3, "R1")})
    edges = _candidate({"s_leaf": (0, "R1"), "s_mid": (4, "R1"), "s_top": (2, "R1")})
    assert criteria["S5"].raw_value(middle) == 0.0
    assert criteria["S5"].raw_value(edges) == 2.0


def test_s5_counts_a_two_period_session_by_either_period_it_occupies(instance):
    """The specific mistake worth guarding: a 2-period session starting at
    period 3 ENDS on the edge period 4, and must count even though its start
    is not an edge."""
    sessions = tuple(
        replace(s, duration_periods=2) if s.id == "s_leaf" else s for s in instance.sessions
    )
    with_two_period = replace(instance, sessions=sessions)
    candidate = _candidate({"s_leaf": (3, "R1"), "s_mid": (1, "R2"), "s_top": (2, "R2")})
    assert _by_code(with_two_period)["S5"].raw_value(candidate) == 1.0


def test_s7_counts_repeats_of_one_course_reaching_one_leaf_group_in_a_day(instance):
    """s_leaf and s_mid are both course C1 and both reach leaf T. Same day ->
    1 excess; different days -> 0. s_top is course C2 and never contributes."""
    criteria = _by_code(instance)
    same_day = _candidate({"s_leaf": (0, "R1"), "s_mid": (1, "R2"), "s_top": (2, "R1")})
    split = _candidate({"s_leaf": (0, "R1"), "s_mid": (5, "R2"), "s_top": (2, "R1")})
    assert criteria["S7"].raw_value(same_day) == 1.0
    assert criteria["S7"].raw_value(split) == 0.0


def test_s10_counts_leaf_group_days_that_lose_the_lunch_period(instance):
    criteria = _by_code(instance)
    protected = _candidate({"s_leaf": (0, "R1"), "s_mid": (1, "R2"), "s_top": (3, "R1")})
    lost = _candidate({"s_leaf": (2, "R1"), "s_mid": (1, "R2"), "s_top": (3, "R1")})
    assert criteria["S10"].raw_value(protected) == 0.0
    assert criteria["S10"].raw_value(lost) == 1.0


def test_s6_measures_deviation_from_the_room_types_own_mean_not_over_capacity(instance):
    """Both rooms are Salle; demand is 3 periods over 2 rooms, so the target is
    1.5 periods each. Splitting 2/1 deviates by 0.5 periods per room; piling all
    3 into one room deviates by 1.5 each - strictly worse, which is the whole
    point of the criterion."""
    criteria = _by_code(instance)
    balanced = _candidate({"s_leaf": (0, "R1"), "s_mid": (1, "R1"), "s_top": (2, "R2")})
    piled = _candidate({"s_leaf": (0, "R1"), "s_mid": (1, "R1"), "s_top": (2, "R1")})
    assert criteria["S6"].raw_value(piled) > criteria["S6"].raw_value(balanced)


def test_every_criterion_reports_bounds_that_contain_its_own_measurement(instance):
    """A bound that a real candidate can exceed would push the normalised value
    outside [0, 1] and silently corrupt every score built on it."""
    candidate = _candidate({"s_leaf": (0, "R1"), "s_mid": (2, "R2"), "s_top": (4, "R1")})
    for criterion in build_criteria(instance):
        value = criterion.raw_value(candidate)
        bounds = criterion.bounds(instance)
        assert bounds.minimum <= value <= bounds.maximum, (
            f"{criterion.code}: raw value {value} outside instance-derived bounds {bounds}"
        )
