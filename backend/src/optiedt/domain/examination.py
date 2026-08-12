"""Entities of the examination session — FR-20, increment 2.

Pure, like `entities.py`: no I/O, no ORM, no framework, no `ortools`.

**These types are PARALLEL to the weekly ones, never a widening of them.**
SRS §3.2 Table 19 gives FR-20's output as *"One slot and one or more rooms
assigned to each examination"*, and SRS §6.8 states the reason: *"An
examination may occupy several rooms at once, so the assignment of the rooms
becomes a sum of capacities and not the choice of a single room."* That is
**R-6**. The weekly `Placement` carries exactly one `room` and is depended on
by persistence, scoring, the four views and invariant 6's immutability tests —
widening it to a collection to accommodate exams would push a shape only the
examination model needs through every one of those. `ExamPlacement` exists so
that it does not.

Three differences from the weekly model, all from SRS §6.8:

1. **Rooms are a set with a capacity sum** (X2), not a single choice.
2. **The horizon is the examination period, not the week** — `ExamSlot.index`
   runs over the days of that period, so it is NOT a weekly `SlotIndex` and the
   two must never be compared or interchanged.
3. **Conflicts are computed per individual student** (X1), not per group,
   *"whereas two students of the same group may present different optional
   courses"*.

⚠️ On the reference instance every course belongs to exactly one promotion, so
a per-student conflict and a per-promotion conflict happen to coincide. The
model is still written per student, because that equivalence is a property of
this dataset and not of the requirement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from optiedt.domain.entities import (
    CourseId,
    PromotionId,
    RoomId,
    StudentId,
    TeacherId,
)

type ExaminationId = str
type ExamSlotIndex = int
"""Index over the days of the EXAMINATION PERIOD.

⚠️ Not interchangeable with `SlotIndex`, which indexes the ordinary week.
Distinct type aliases so the two cannot be confused at a glance in a signature.
"""


@dataclass(frozen=True, slots=True)
class Examination:
    """One examination of the session.

    **Derived from the instance, never supplied** (ADR-013). FR-20 lists
    "Examinations" among its inputs and the SRS data model (Table 25) defines
    no Examination entity, so the derivation rule is a project decision — see
    C-23. `candidates` holds individual student ids because X1 is stated per
    student.
    """

    id: ExaminationId
    course: CourseId
    promotion: PromotionId
    supervisor: TeacherId
    """The CM teacher of the course.

    ⚠️ Chosen because it is the only unambiguous teacher the data yields: a
    course has 3 to 13 teachers once TD and TP groups are counted, and exactly
    one CM. The CdC grants a teacher *"consultation of the personal timetable
    and of the examinations supervised"*, so a teacher IS a supervisor; which
    one is what the data had to settle. See C-23.
    """

    candidates: tuple[StudentId, ...]

    @property
    def candidate_count(self) -> int:
        """X2's quantity: how many seats this examination needs."""
        return len(self.candidates)


@dataclass(frozen=True, slots=True)
class ExamSlot:
    """One placeable slot of the examination period.

    Only slots that survive X3 are built at all — a day outside the period or
    on a blocking holiday produces no `ExamSlot`, so "inside the period and
    outside the holidays" is enforced by the domain of the variable rather than
    by a constraint posted afterwards. That is the same technique H9 uses for
    the weekly model.
    """

    index: ExamSlotIndex
    day_index: int
    """0-based within the examination period, NOT a weekday."""

    period_index: int
    day: date


@dataclass(frozen=True, slots=True)
class ExamPlacement:
    """One examination, placed. The examination model's unit of result.

    ⚠️ `rooms` is a TUPLE and that is the whole of R-6. Never collapse it to a
    single value, and never map it onto the weekly `Placement`.
    """

    examination: ExaminationId
    slot: ExamSlotIndex
    rooms: tuple[RoomId, ...]


@dataclass(frozen=True, slots=True)
class ExamSession:
    """Everything one examination solve needs.

    The examination counterpart of `SolverInput`, deliberately much smaller:
    FR-20 asks for *a* timetable, not a ranked portfolio, so there is no weight
    profile, no scoring vector and no candidate set. PPM's completion criterion
    is "the timetable of an examination session is produced under the
    constraints X1 to X4" — singular.
    """

    examinations: tuple[Examination, ...]
    slots: tuple[ExamSlot, ...]
    seed: int = 42
    deterministic_budget: float = 30.0
    """Deterministic time, NOT wall-clock seconds — ADR-011, same as the weekly
    model. A wall-clock bound with parallel workers is not reproducible."""


@dataclass(frozen=True, slots=True)
class ExamTimetable:
    """The result of one examination solve.

    `placements` is empty when `infeasible` is True.
    """

    placements: tuple[ExamPlacement, ...]
    spread_penalty: int
    """SX1, measured on the timetable returned.

    ⚠️ Recomputed from the placements rather than read from CP-SAT's objective,
    for the reason ADR-011 records: `CpSolver.objective_value` can be reported
    above the objective at the solution actually returned when a solve stops
    before proving optimality.
    """

    infeasible: bool = False
    proven_optimal: bool = False
    deterministic_time_used: float = 0.0
    wall_clock_seconds: float = 0.0
