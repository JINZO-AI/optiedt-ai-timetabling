"""The ITC-2007 CP-SAT model, and one solve.

⚠️ **This is a second model of a different problem, not `optiedt.solver` pointed
at foreign data.** See the package docstring for why forcing ITC-2007 through the
reference instance's schema would validate an adapter rather than an engine. What
carries over is the *approach* — CP-SAT for assignment (ADR-001), placements
correct by construction, and the solve configuration ADR-011 fixed.

**The objective is exact.** Every soft cost is encoded so that the value CP-SAT
reports equals what `cost.py` computes from the placements — not a bound on it,
not a proxy. That is deliberate and it is checkable: `runner.py` compares the two
on every instance, and a disagreement means the encoding is wrong. It is the same
guard `tests/integration/test_objective_matches_analysis.py` puts on the product,
for the same reason: two independent derivations of one number are worth far more
than one derivation asserted twice.

The four hard constraints, and where each lives:

| ITC-2007 | Here |
|---|---|
| Lectures | `Σ_p y[c,p] == lectures(c)`; `y` is boolean, so periods are distinct |
| Conflicts | `at_most_one` per (curriculum, period) and per (teacher, period) |
| RoomOccupancy | `at_most_one` per (room, period) |
| Availability | **no variable is created** for an unavailable (course, period) |

Availability by domain restriction rather than by a posted constraint mirrors how
this project applies H4/H5/H6/H8/H9 (`docs/constraint-model.md`): it costs nothing
during search and shrinks the space instead of filtering it afterwards.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ortools.sat.python import cp_model

from optiedt.validation.itc2007.cost import (
    CURRICULUM_COMPACTNESS_WEIGHT,
    MIN_WORKING_DAYS_WEIGHT,
    ROOM_CAPACITY_WEIGHT,
    ROOM_STABILITY_WEIGHT,
    SoftCost,
)
from optiedt.validation.itc2007.problem import (
    Assignment,
    CourseId,
    Itc2007Instance,
    PeriodIndex,
    RoomId,
    Solution,
)

_TERMINAL_STATUSES = (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE)


@dataclass(frozen=True, slots=True)
class SolveConfig:
    """ADR-011's configuration, applied unchanged to a foreign instance.

    A deterministic budget rather than wall-clock seconds, and
    ``interleave_search`` without which the search is not reproducible at more
    than one worker whatever the seed says (C-16). Running the benchmark under
    the production configuration is part of the point: if the settings the
    project publishes timetables under could not also solve published instances,
    that would be worth knowing.
    """

    seed: int = 42
    deterministic_budget: float = 60.0
    workers: int = 0
    wall_clock_ceiling_seconds: float = 900.0


@dataclass(frozen=True, slots=True)
class SoftCostTerms:
    """The objective, kept in its four groups rather than pre-summed.

    So that a disagreement between CP-SAT's objective and the recomputed cost
    can be *localised* instead of guessed at. When the two first diverged on
    two of the 21 instances, the four groups pinned it to one component in a
    single run; without them it would have been a hunt through four exact
    encodings that all looked right.
    """

    room_capacity: list[cp_model.LinearExpr | int]
    min_working_days: list[cp_model.LinearExpr | int]
    curriculum_compactness: list[cp_model.LinearExpr | int]
    room_stability: list[cp_model.LinearExpr | int]

    def all_terms(self) -> list[cp_model.LinearExpr | int]:
        return [
            *self.room_capacity,
            *self.min_working_days,
            *self.curriculum_compactness,
            *self.room_stability,
        ]


@dataclass(frozen=True, slots=True)
class SolveReport:
    """One solve. ``objective`` is CP-SAT's own value; the *reported* cost always
    comes from `cost.py` re-derived from ``solution``."""

    solution: Solution
    infeasible: bool
    proven_optimal: bool
    objective: int
    best_bound: int
    variables: int
    deterministic_time_used: float
    wall_clock_seconds: float
    objective_breakdown: SoftCost | None = None
    """CP-SAT's own value for each of the four soft costs, read back from the
    auxiliaries. Compare with `cost.evaluate(...).soft` — they must be equal,
    and when they are not this says which one moved."""


def solve(instance: Itc2007Instance, config: SolveConfig | None = None) -> SolveReport:
    """Build and solve one ITC-2007 instance."""
    config = config or SolveConfig()
    model = cp_model.CpModel()

    periods = range(instance.periods)
    room_ids = [room.id for room in instance.rooms]

    # x[c,p,r]: course c holds a lecture in room r at period p. Absent for an
    # unavailable (c, p) - the Availability constraint, applied as pruning.
    place: dict[tuple[CourseId, PeriodIndex, RoomId], cp_model.IntVar] = {}
    # y[c,p]: c holds a lecture at p, in some room. Channelled from x, exactly
    # as solver/occupancy.py channels y[s,t] from the start indicators.
    holds: dict[tuple[CourseId, PeriodIndex], cp_model.IntVar] = {}

    for course in instance.courses:
        for period in periods:
            if (course.id, period) in instance.unavailable:
                continue
            rooms = [
                place.setdefault(
                    (course.id, period, room_id),
                    model.new_bool_var(f"x[{course.id},{period},{room_id}]"),
                )
                for room_id in room_ids
            ]
            occupied = model.new_bool_var(f"y[{course.id},{period}]")
            holds[(course.id, period)] = occupied
            # Boolean y forces at most one room per (course, period), which is
            # the "distinct periods" half of the Lectures constraint.
            model.add(occupied == sum(rooms))

    # Lectures: every lecture scheduled, one per period.
    for course in instance.courses:
        available = [holds[(course.id, p)] for p in periods if (course.id, p) in holds]
        if len(available) < course.lectures:
            raise ValueError(
                f"{instance.name}: course {course.id} needs {course.lectures} lectures but "
                f"only {len(available)} periods are available to it - the instance is "
                "infeasible by arithmetic, before any solving"
            )
        model.add(sum(available) == course.lectures)

    # Conflicts: same curriculum, or same teacher, never share a period.
    for curriculum in instance.curricula:
        for period in periods:
            members = [
                holds[(member, period)]
                for member in dict.fromkeys(curriculum.members)
                if (member, period) in holds
            ]
            if len(members) > 1:
                model.add_at_most_one(members)

    by_teacher: dict[str, list[CourseId]] = defaultdict(list)
    for course in instance.courses:
        by_teacher[course.teacher].append(course.id)
    for taught in by_teacher.values():
        if len(taught) < 2:
            continue
        for period in periods:
            simultaneous = [holds[(c, period)] for c in taught if (c, period) in holds]
            if len(simultaneous) > 1:
                model.add_at_most_one(simultaneous)

    # RoomOccupancy: one lecture per room per period.
    for room_id in room_ids:
        for period in periods:
            occupants = [
                place[(course.id, period, room_id)]
                for course in instance.courses
                if (course.id, period, room_id) in place
            ]
            if len(occupants) > 1:
                model.add_at_most_one(occupants)

    # Redundant, and worth its place: at most one lecture per room per period
    # already implies at most |rooms| lectures in any period, but stating it
    # over y lets CP-SAT propagate a period's capacity without first reasoning
    # through every room variable. Implied constraints cannot change the set of
    # solutions - only how fast the search reaches them.
    for period in periods:
        simultaneous = [
            holds[(course.id, period)]
            for course in instance.courses
            if (course.id, period) in holds
        ]
        if len(simultaneous) > len(room_ids):
            model.add(sum(simultaneous) <= len(room_ids))

    penalties = _soft_cost_terms(model, instance, place, holds)
    model.minimize(sum(penalties.all_terms()))

    solver = cp_model.CpSolver()
    solver.parameters.max_deterministic_time = config.deterministic_budget
    solver.parameters.max_time_in_seconds = config.wall_clock_ceiling_seconds
    solver.parameters.random_seed = config.seed
    solver.parameters.num_workers = config.workers
    # Required for reproducibility at more than one worker - see ADR-011 and
    # C-16. Set here for the same reason it is set in solver/engine.py.
    solver.parameters.interleave_search = True

    status = solver.solve(model)
    if status not in _TERMINAL_STATUSES:
        return SolveReport(
            solution=(),
            infeasible=False,
            proven_optimal=False,
            objective=0,
            best_bound=0,
            variables=len(place) + len(holds),
            deterministic_time_used=solver.deterministic_time,
            wall_clock_seconds=solver.wall_time,
        )

    infeasible = status == cp_model.INFEASIBLE
    solution: Solution = ()
    breakdown: SoftCost | None = None
    if not infeasible:
        solution = tuple(
            Assignment(course=course_id, room=room_id, period=period)
            for (course_id, period, room_id), variable in sorted(place.items())
            if solver.value(variable)
        )
        breakdown = SoftCost(
            room_capacity=_group_value(solver, penalties.room_capacity),
            min_working_days=_group_value(solver, penalties.min_working_days),
            curriculum_compactness=_group_value(solver, penalties.curriculum_compactness),
            room_stability=_group_value(solver, penalties.room_stability),
        )

    return SolveReport(
        solution=solution,
        infeasible=infeasible,
        proven_optimal=status == cp_model.OPTIMAL,
        objective=round(solver.objective_value) if not infeasible else 0,
        best_bound=round(solver.best_objective_bound) if not infeasible else 0,
        variables=len(place) + len(holds),
        deterministic_time_used=solver.deterministic_time,
        wall_clock_seconds=solver.wall_time,
        objective_breakdown=breakdown,
    )


def _group_value(solver: cp_model.CpSolver, terms: list[cp_model.LinearExpr | int]) -> int:
    return sum(term if isinstance(term, int) else solver.value(term) for term in terms)


def _soft_cost_terms(
    model: cp_model.CpModel,
    instance: Itc2007Instance,
    place: dict[tuple[CourseId, PeriodIndex, RoomId], cp_model.IntVar],
    holds: dict[tuple[CourseId, PeriodIndex], cp_model.IntVar],
) -> SoftCostTerms:
    """The four soft costs as linear expressions, each **exact**.

    "Exact" is the load-bearing word: each auxiliary is pinned from both sides,
    so its value is determined by the placements rather than merely bounded in
    the direction minimisation happens to push. A one-sided encoding would give
    the same optimum and a wrong objective at every non-optimal solution, which
    would silently defeat the objective-versus-cost cross-check in runner.py.
    """
    capacity_terms: list[cp_model.LinearExpr | int] = []
    working_day_terms: list[cp_model.LinearExpr | int] = []
    compactness_terms: list[cp_model.LinearExpr | int] = []
    stability_terms: list[cp_model.LinearExpr | int] = []
    capacities = {room.id: room.capacity for room in instance.rooms}
    students = {course.id: course.students for course in instance.courses}

    lectures_of: dict[tuple[CourseId, RoomId], list[cp_model.IntVar]] = defaultdict(list)
    for (course_id, _, room_id), variable in place.items():
        lectures_of[(course_id, room_id)].append(variable)

    # RoomCapacity: a constant penalty per (course, room) pair, no auxiliary.
    capacity_terms.extend(
        variable * ((students[course_id] - capacities[room_id]) * ROOM_CAPACITY_WEIGHT)
        for (course_id, _, room_id), variable in place.items()
        if students[course_id] > capacities[room_id]
    )

    # MinimumWorkingDays: 5 per day short of the minimum. A course spread over
    # MORE days than its minimum costs nothing, so the shortfall is a max with
    # zero and not a plain difference - which would go negative and, with a
    # shortfall variable bounded below by 0, make the whole model infeasible.
    for course in instance.courses:
        day_used = []
        for day in range(instance.days):
            in_day = [
                holds[(course.id, period)]
                for period in instance.periods_of_day(day)
                if (course.id, period) in holds
            ]
            if not in_day:
                continue
            used = model.new_bool_var(f"day[{course.id},{day}]")
            model.add(used <= sum(in_day))
            for lecture in in_day:
                model.add(used >= lecture)
            day_used.append(used)
        shortfall = model.new_int_var(0, course.min_working_days, f"mwd[{course.id}]")
        model.add_max_equality(shortfall, [0, course.min_working_days - sum(day_used)])
        working_day_terms.append(shortfall * MIN_WORKING_DAYS_WEIGHT)

    # CurriculumCompactness: 2 per lecture with no same-curriculum neighbour
    # inside its own day.
    for curriculum in instance.curricula:
        occupied: dict[PeriodIndex, cp_model.IntVar] = {}
        for period in range(instance.periods):
            members = [
                holds[(member, period)]
                for member in dict.fromkeys(curriculum.members)
                if (member, period) in holds
            ]
            if not members:
                continue
            marker = model.new_bool_var(f"occ[{curriculum.id},{period}]")
            model.add(marker == sum(members))
            occupied[period] = marker

        for period, marker in occupied.items():
            neighbours = [
                occupied[adjacent]
                for adjacent in instance.adjacent_periods(period)
                if adjacent in occupied
            ]
            isolated = model.new_bool_var(f"iso[{curriculum.id},{period}]")
            model.add(isolated <= marker)
            for neighbour in neighbours:
                model.add(isolated <= 1 - neighbour)
            model.add(isolated >= marker - sum(neighbours))
            compactness_terms.append(isolated * CURRICULUM_COMPACTNESS_WEIGHT)

    # RoomStability: 1 per room beyond the first. The Lectures constraint forces
    # at least one lecture per course, so the "- 1" can never go negative.
    for course in instance.courses:
        used_rooms = []
        for room in instance.rooms:
            lectures = lectures_of.get((course.id, room.id), [])
            if not lectures:
                continue
            used = model.new_bool_var(f"room[{course.id},{room.id}]")
            model.add(used <= sum(lectures))
            for lecture in lectures:
                model.add(used >= lecture)
            used_rooms.append(used)
        stability_terms.append((sum(used_rooms) - 1) * ROOM_STABILITY_WEIGHT)

    return SoftCostTerms(
        room_capacity=capacity_terms,
        min_working_days=working_day_terms,
        curriculum_compactness=compactness_terms,
        room_stability=stability_terms,
    )
