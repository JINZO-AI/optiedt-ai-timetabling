"""The ITC-2007 cost function, pinned against hand-computed values.

No archive and no solver: the instances here are three courses wide and the
expected numbers are worked out in the comments, so a failure names the rule that
broke rather than a total that moved. The complementary test - that the same
function reproduces the published cost of seven real, independently produced
solutions - is `tests/integration/test_itc2007_validation.py`, and neither
replaces the other: this one says the arithmetic is what was intended, that one
says the intention matches the competition.
"""

from __future__ import annotations

import pytest

from optiedt.validation.itc2007.cost import (
    check_well_formed,
    evaluate,
    hard_violations,
    soft_cost,
)
from optiedt.validation.itc2007.problem import (
    Assignment,
    Course,
    Curriculum,
    Itc2007Instance,
    Room,
)


@pytest.fixture
def tiny() -> Itc2007Instance:
    """2 days x 3 periods, 2 rooms, 3 courses, 1 curriculum.

    Periods are 0,1,2 on day 0 and 3,4,5 on day 1. `big` seats 40, `small`
    seats 10, so placing `maths` (30 students) in `small` costs 20.
    """
    return Itc2007Instance(
        name="tiny",
        days=2,
        periods_per_day=3,
        courses=(
            Course(id="maths", teacher="t1", lectures=2, min_working_days=2, students=30),
            Course(id="physics", teacher="t1", lectures=1, min_working_days=1, students=5),
            Course(id="art", teacher="t2", lectures=1, min_working_days=1, students=5),
        ),
        rooms=(Room(id="big", capacity=40), Room(id="small", capacity=10)),
        curricula=(Curriculum(id="c1", members=("maths", "physics")),),
        unavailable=frozenset({("art", 0)}),
    )


def place(course: str, room: str, period: int) -> Assignment:
    return Assignment(course=course, room=room, period=period)


def test_a_clean_timetable_violates_nothing(tiny):
    # maths on both days, physics adjacent to maths, art anywhere but period 0.
    solution = (
        place("maths", "big", 0),
        place("maths", "big", 3),
        place("physics", "big", 1),
        place("art", "big", 4),
    )
    assert hard_violations(tiny, solution).total == 0


def test_a_missing_lecture_is_counted_once(tiny):
    solution = (place("maths", "big", 0), place("physics", "big", 1), place("art", "big", 4))
    assert hard_violations(tiny, solution).lectures == 1


def test_an_extra_lecture_is_counted_too(tiny):
    solution = (
        place("maths", "big", 0),
        place("maths", "big", 3),
        place("maths", "big", 4),
        place("physics", "big", 1),
        place("art", "big", 5),
    )
    assert hard_violations(tiny, solution).lectures == 1


def test_two_lectures_of_one_course_in_one_period_is_a_violation(tiny):
    """The half of the Lectures constraint the C++ validator cannot see.

    Its timetable is course x period -> room, so a repeat is dropped with a
    warning and never costed. "Assigned to distinct periods" is a rule, not a
    data-structure artefact - see cost.py.
    """
    solution = (
        place("maths", "big", 0),
        place("maths", "small", 0),
        place("physics", "big", 2),
        place("art", "big", 4),
    )
    assert hard_violations(tiny, solution).repeated_period == 1


def test_same_curriculum_in_one_period_conflicts(tiny):
    solution = (
        place("maths", "big", 0),
        place("maths", "big", 3),
        place("physics", "small", 0),
        place("art", "big", 4),
    )
    assert hard_violations(tiny, solution).conflicts == 1


def test_same_teacher_in_one_period_conflicts_even_across_curricula():
    """`maths` and `physics` share teacher t1 AND curriculum c1 - one pair, one
    violation, not two. The validator's `conflict` matrix is a set of pairs."""
    instance = Itc2007Instance(
        name="pair",
        days=1,
        periods_per_day=2,
        courses=(
            Course(id="a", teacher="t1", lectures=1, min_working_days=1, students=1),
            Course(id="b", teacher="t1", lectures=1, min_working_days=1, students=1),
        ),
        rooms=(Room(id="r1", capacity=10), Room(id="r2", capacity=10)),
        curricula=(Curriculum(id="c", members=("a", "b")),),
        unavailable=frozenset(),
    )
    solution = (place("a", "r1", 0), place("b", "r2", 0))
    assert hard_violations(instance, solution).conflicts == 1


def test_an_unavailable_period_is_a_violation(tiny):
    solution = (
        place("maths", "big", 1),
        place("maths", "big", 3),
        place("physics", "big", 2),
        place("art", "big", 0),  # art declared period 0 unavailable
    )
    assert hard_violations(tiny, solution).availability == 1


def test_two_lectures_in_one_room_at_one_period(tiny):
    solution = (
        place("maths", "big", 0),
        place("maths", "big", 3),
        place("physics", "big", 2),
        place("art", "big", 3),  # `big` is already taken at period 3
    )
    assert hard_violations(tiny, solution).room_occupancy == 1


def test_room_capacity_costs_one_per_missing_seat(tiny):
    """maths has 30 students; `small` seats 10, so one lecture there costs 20."""
    solution = (
        place("maths", "small", 0),
        place("maths", "big", 3),
        place("physics", "big", 1),
        place("art", "big", 4),
    )
    assert soft_cost(tiny, solution).room_capacity == 20


def test_minimum_working_days_costs_five_per_day_short(tiny):
    """maths asks for 2 days; both its lectures on day 0 is one day short."""
    solution = (
        place("maths", "big", 0),
        place("maths", "big", 1),
        place("physics", "big", 4),
        place("art", "big", 5),
    )
    assert soft_cost(tiny, solution).min_working_days == 5


def test_room_stability_costs_one_per_extra_room(tiny):
    solution = (
        place("maths", "big", 0),
        place("maths", "small", 3),
        place("physics", "big", 1),
        place("art", "big", 4),
    )
    assert soft_cost(tiny, solution).room_stability == 1


def test_compactness_charges_two_per_isolated_lecture(tiny):
    """Curriculum c1 = {maths, physics}. Placing its three lectures at periods
    0, 3 and 5 leaves all three isolated: 0 has nothing at 1, 3 nothing at 4,
    5 nothing at 4. 3 x 2 = 6."""
    solution = (
        place("maths", "big", 0),
        place("maths", "big", 3),
        place("physics", "big", 5),
        place("art", "big", 4),  # art is in no curriculum, so it does not help
    )
    assert soft_cost(tiny, solution).curriculum_compactness == 6


def test_adjacency_does_not_cross_a_day_boundary(tiny):
    """Periods 2 and 3 are consecutive integers and consecutive days. A lecture
    in the last slot of day 0 is NOT made compact by one in the first slot of
    day 1 - the rule the C++ validator special-cases and the easiest one to get
    wrong with a flat period index."""
    solution = (
        place("maths", "big", 2),
        place("maths", "big", 3),
        place("physics", "small", 5),
        place("art", "big", 4),
    )
    assert soft_cost(tiny, solution).curriculum_compactness == 6


def test_adjacent_lectures_within_a_day_cost_nothing(tiny):
    solution = (
        place("maths", "big", 0),
        place("maths", "big", 3),
        place("physics", "big", 1),
        place("art", "big", 4),
    )
    assert soft_cost(tiny, solution).curriculum_compactness == 2  # only period 3


def test_an_unknown_name_stops_the_run_rather_than_costing_something(tiny):
    with pytest.raises(ValueError, match="unknown course"):
        check_well_formed(tiny, (place("chemistry", "big", 0),))
    with pytest.raises(ValueError, match="unknown room"):
        check_well_formed(tiny, (place("maths", "cellar", 0),))
    with pytest.raises(ValueError, match="outside the"):
        check_well_formed(tiny, (place("maths", "big", 99),))


def test_a_cost_is_only_reportable_when_the_timetable_is_valid(tiny):
    invalid = (place("maths", "big", 0),)  # one lecture short
    assert not evaluate(tiny, invalid).reportable

    valid = (
        place("maths", "big", 0),
        place("maths", "big", 3),
        place("physics", "big", 1),
        place("art", "big", 4),
    )
    assert evaluate(tiny, valid).reportable
