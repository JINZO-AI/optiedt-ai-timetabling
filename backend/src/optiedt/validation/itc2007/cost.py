"""ITC-2007's four hard constraints and four soft costs, re-derived from a
solution. The authority on whether a run may be reported at all.

Every rule here is transcribed from the **bundled `validator/main.cpp`**, not
from a recollection of the competition rules and not from a paper: that file is
the artefact the published costs in `results/` were produced against, so
agreeing with it is a checkable claim. `docs/testing-strategy.md` §1 asks for two
things — "that no timetable produced violates a hard constraint, and the distance
between the cost obtained and the best known results" — and both are read off
this module.

⚠️ **This must never be computed from the CP-SAT objective.** The objective is
the model's *opinion* of the cost; this is the cost. That disagreement is only
visible while the two are derived separately — the same reason
`tests/integration/test_h1_h12.py` re-derives H1-H12 from the raw CSVs instead
of trusting the solver's status. It earned its place on 2026-07-31: under
`interleave_search`, `CpSolver.objective_value` was found to sit a few units
above the objective at the solution actually returned, on solves that stop
before proving optimality (ADR-011). Every figure this harness prints comes from
here instead, so none of them moved.

**One deliberate difference from the C++ validator.** It stores the timetable as
`course x period -> room`, so a second lecture of one course in one period is
*dropped* with a warning and never costed. That is a data-structure artefact, not
a rule: the Lectures constraint says lectures must be assigned to **distinct
periods**. This module counts such a repeat as a violation (`repeated_period`).
On any feasible solution the two agree exactly; on a broken one this module is
stricter, which is the direction a checker should err in.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from optiedt.validation.itc2007.problem import (
    CourseId,
    Itc2007Instance,
    PeriodIndex,
    RoomId,
    Solution,
)

ROOM_CAPACITY_WEIGHT = 1
MIN_WORKING_DAYS_WEIGHT = 5
CURRICULUM_COMPACTNESS_WEIGHT = 2
ROOM_STABILITY_WEIGHT = 1
"""The four soft weights, from `Faculty::Faculty` in validator/main.cpp:
``MIN_WORKING_DAYS_COST(5), CURRICULUM_COMPACTNESS_COST(2), ROOM_STABILITY_COST(1)``.
Room capacity carries no constant there because it is applied at weight 1 -
"each student above the capacity counts as 1 point of penalty"."""


@dataclass(frozen=True, slots=True)
class HardViolations:
    """The four hard constraints. Any non-zero total invalidates the run.

    Reported per constraint rather than as a boolean because a validation report
    that says only "invalid" cannot be acted on - the same reason FR-12 requires
    a failing pre-analysis check to name the resource and the quantity.
    """

    lectures: int
    """|scheduled - required|, summed over courses."""
    repeated_period: int
    """Lectures of one course sharing a period. See the module docstring."""
    conflicts: int
    """Pairs of courses in one period sharing a curriculum or a teacher."""
    availability: int
    """Lectures placed in a period the course declared unavailable."""
    room_occupancy: int
    """Lectures beyond the first in one room at one period."""

    @property
    def total(self) -> int:
        return (
            self.lectures
            + self.repeated_period
            + self.conflicts
            + self.availability
            + self.room_occupancy
        )

    @property
    def feasible(self) -> bool:
        return self.total == 0


@dataclass(frozen=True, slots=True)
class SoftCost:
    """The four soft costs, **already weighted** — so these are the columns the
    bundled benchmark logs print as `cost_rc cost_mwd cost_cc cost_rs cost`, and
    `total` is that last column."""

    room_capacity: int
    min_working_days: int
    curriculum_compactness: int
    room_stability: int

    @property
    def total(self) -> int:
        return (
            self.room_capacity
            + self.min_working_days
            + self.curriculum_compactness
            + self.room_stability
        )


@dataclass(frozen=True, slots=True)
class Evaluation:
    hard: HardViolations
    soft: SoftCost

    @property
    def reportable(self) -> bool:
        """A cost may only be compared with published results when the timetable
        is feasible. Comparing the cost of an invalid timetable to a valid one is
        meaningless, and cheap to do by accident."""
        return self.hard.feasible


def _by_period(solution: Solution) -> dict[PeriodIndex, list[tuple[CourseId, RoomId]]]:
    grouped: dict[PeriodIndex, list[tuple[CourseId, RoomId]]] = defaultdict(list)
    for assignment in solution:
        grouped[assignment.period].append((assignment.course, assignment.room))
    return grouped


def _conflicting_pairs(instance: Itc2007Instance) -> set[frozenset[CourseId]]:
    """Course pairs that may never share a period: same curriculum, or same
    teacher. Built exactly as `Faculty::Faculty` builds its `conflict` matrix —
    curriculum co-membership first, shared teachers added afterwards."""
    pairs: set[frozenset[CourseId]] = set()
    for curriculum in instance.curricula:
        for index, first in enumerate(curriculum.members):
            for second in curriculum.members[index + 1 :]:
                if first != second:
                    pairs.add(frozenset((first, second)))

    by_teacher: dict[str, list[CourseId]] = defaultdict(list)
    for course in instance.courses:
        by_teacher[course.teacher].append(course.id)
    for taught in by_teacher.values():
        for index, first in enumerate(taught):
            for second in taught[index + 1 :]:
                pairs.add(frozenset((first, second)))
    return pairs


def check_well_formed(instance: Itc2007Instance, solution: Solution) -> None:
    """Raise if the solution names something the instance does not contain.

    An unknown course, an unknown room or a period outside the week is a
    **mismatch between reader and file**, not a bad timetable, and costing it as
    a violation would report a plausible number for a broken pairing. The
    bundled C++ validator drops such rows with a warning to stderr; here they
    stop the run.
    """
    courses = {course.id for course in instance.courses}
    rooms = {room.id for room in instance.rooms}
    for assignment in solution:
        if assignment.course not in courses:
            raise ValueError(f"{instance.name}: solution names unknown course {assignment.course}")
        if assignment.room not in rooms:
            raise ValueError(f"{instance.name}: solution names unknown room {assignment.room}")
        if not 0 <= assignment.period < instance.periods:
            raise ValueError(
                f"{instance.name}: period {assignment.period} is outside the "
                f"{instance.periods}-period week"
            )


def hard_violations(instance: Itc2007Instance, solution: Solution) -> HardViolations:
    """Count violations of Lectures, Conflicts, Availability and RoomOccupancy."""
    check_well_formed(instance, solution)

    scheduled: dict[CourseId, int] = defaultdict(int)
    periods_of_course: dict[CourseId, list[PeriodIndex]] = defaultdict(list)
    for assignment in solution:
        scheduled[assignment.course] += 1
        periods_of_course[assignment.course].append(assignment.period)

    lectures = sum(
        abs(scheduled.get(course.id, 0) - course.lectures) for course in instance.courses
    )
    repeated_period = sum(
        len(periods) - len(set(periods)) for periods in periods_of_course.values()
    )
    availability = sum(1 for a in solution if (a.course, a.period) in instance.unavailable)

    conflicting = _conflicting_pairs(instance)
    grouped = _by_period(solution)
    conflicts = 0
    room_occupancy = 0
    for entries in grouped.values():
        for index, (first_course, _) in enumerate(entries):
            for second_course, _ in entries[index + 1 :]:
                if frozenset((first_course, second_course)) in conflicting:
                    conflicts += 1
        rooms_used: dict[RoomId, int] = defaultdict(int)
        for _, room in entries:
            rooms_used[room] += 1
        room_occupancy += sum(count - 1 for count in rooms_used.values() if count > 1)

    return HardViolations(
        lectures=lectures,
        repeated_period=repeated_period,
        conflicts=conflicts,
        availability=availability,
        room_occupancy=room_occupancy,
    )


def soft_cost(instance: Itc2007Instance, solution: Solution) -> SoftCost:
    """The weighted RoomCapacity, MinWorkingDays, CurriculumCompactness and
    RoomStability costs."""
    check_well_formed(instance, solution)
    students = {course.id: course.students for course in instance.courses}
    capacities = {room.id: room.capacity for room in instance.rooms}

    room_capacity = sum(
        max(0, students[a.course] - capacities[a.room]) * ROOM_CAPACITY_WEIGHT for a in solution
    )

    days_used: dict[CourseId, set[int]] = defaultdict(set)
    rooms_used: dict[CourseId, set[RoomId]] = defaultdict(set)
    for assignment in solution:
        days_used[assignment.course].add(instance.day_of(assignment.period))
        rooms_used[assignment.course].add(assignment.room)

    min_working_days = (
        sum(
            max(0, course.min_working_days - len(days_used.get(course.id, set())))
            for course in instance.courses
        )
        * MIN_WORKING_DAYS_WEIGHT
    )

    room_stability = (
        sum(max(0, len(rooms_used.get(course.id, set())) - 1) for course in instance.courses)
        * ROOM_STABILITY_WEIGHT
    )

    return SoftCost(
        room_capacity=room_capacity,
        min_working_days=min_working_days,
        curriculum_compactness=_compactness(instance, solution),
        room_stability=room_stability,
    )


def _compactness(instance: Itc2007Instance, solution: Solution) -> int:
    """Curriculum compactness: 2 points per lecture with no same-curriculum
    lecture in an adjacent period **of the same day**.

    The count added for an isolated position is the number of the curriculum's
    lectures sitting there, not 1 — matching `CostsOnCurriculumCompactness`,
    which adds `CurriculumPeriodLectures(g, p)`. On a feasible solution that is
    always 1, because two courses of one curriculum in one period is a Conflicts
    violation; the difference only shows on an already-invalid timetable.
    """
    lectures_at: dict[CourseId, set[PeriodIndex]] = defaultdict(set)
    for assignment in solution:
        lectures_at[assignment.course].add(assignment.period)

    isolated = 0
    for curriculum in instance.curricula:
        occupancy: dict[PeriodIndex, int] = defaultdict(int)
        for member in curriculum.members:
            for period in lectures_at.get(member, ()):
                occupancy[period] += 1
        for period, count in occupancy.items():
            neighbours = instance.adjacent_periods(period)
            if all(occupancy.get(neighbour, 0) == 0 for neighbour in neighbours):
                isolated += count
    return isolated * CURRICULUM_COMPACTNESS_WEIGHT


def evaluate(instance: Itc2007Instance, solution: Solution) -> Evaluation:
    """The full verdict on one timetable."""
    return Evaluation(
        hard=hard_violations(instance, solution),
        soft=soft_cost(instance, solution),
    )
