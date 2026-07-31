"""The ITC-2007 Track 3 entities. Pure data, no I/O.

Deliberately shares nothing with `optiedt.domain`. The two problems disagree on
almost every entity — see this package's docstring — and a shared type would
force one of the two definitions to bend.

A **period** is a single integer, `day * periods_per_day + timeslot`, which is
the encoding both the `.ctt` unavailability records and the bundled validator
use. Keeping one representation removes the class of bug where a day-major
index meets a period-major one.
"""

from __future__ import annotations

from dataclasses import dataclass

CourseId = str
RoomId = str
CurriculumId = str
TeacherId = str
PeriodIndex = int


@dataclass(frozen=True, slots=True)
class Course:
    """One `.ctt` COURSES row: `<id> <teacher> <lectures> <min_days> <students>`."""

    id: CourseId
    teacher: TeacherId
    lectures: int
    """How many lectures must be scheduled, each in a DISTINCT period."""
    min_working_days: int
    """Days the lectures should be spread over. A shortfall costs 5 per day."""
    students: int
    """Attendance. Seats short of it cost 1 each, per lecture — a SOFT cost in
    this formulation, which is where ITC-2007 differs most sharply from OptiEDT's
    room model."""


@dataclass(frozen=True, slots=True)
class Room:
    """One `.ctt` ROOMS row: `<id> <capacity>`. All rooms suit all courses."""

    id: RoomId
    capacity: int


@dataclass(frozen=True, slots=True)
class Curriculum:
    """A set of courses with students in common. Two of its courses may never
    share a period (hard), and its lectures should sit adjacent within a day
    (soft, 2 per isolated lecture)."""

    id: CurriculumId
    members: tuple[CourseId, ...]


@dataclass(frozen=True, slots=True)
class Itc2007Instance:
    """One `comp*.ctt` file, read whole."""

    name: str
    days: int
    periods_per_day: int
    courses: tuple[Course, ...]
    rooms: tuple[Room, ...]
    curricula: tuple[Curriculum, ...]
    unavailable: frozenset[tuple[CourseId, PeriodIndex]]
    """(course, period) pairs the course may NOT occupy. The `.ctt` file states
    these as `<course> <day> <timeslot>`; the reader flattens them here."""

    @property
    def periods(self) -> int:
        return self.days * self.periods_per_day

    def day_of(self, period: PeriodIndex) -> int:
        return period // self.periods_per_day

    def timeslot_of(self, period: PeriodIndex) -> int:
        return period % self.periods_per_day

    def periods_of_day(self, day: int) -> range:
        return range(day * self.periods_per_day, (day + 1) * self.periods_per_day)

    def adjacent_periods(self, period: PeriodIndex) -> tuple[PeriodIndex, ...]:
        """The periods that count as adjacent to ``period`` **within its own
        day** — the definition curriculum compactness turns on.

        The first timeslot of a day has only a successor and the last only a
        predecessor: a lecture in the last slot of Monday is not made compact by
        one in the first slot of Tuesday. Reproduced from the bundled
        `validator/main.cpp`, which special-cases exactly those two positions.
        """
        timeslot = self.timeslot_of(period)
        neighbours: list[PeriodIndex] = []
        if timeslot > 0:
            neighbours.append(period - 1)
        if timeslot < self.periods_per_day - 1:
            neighbours.append(period + 1)
        return tuple(neighbours)


@dataclass(frozen=True, slots=True)
class Assignment:
    """One lecture placed: this course, in this room, at this period."""

    course: CourseId
    room: RoomId
    period: PeriodIndex


Solution = tuple[Assignment, ...]
"""A complete or partial timetable. Order carries no meaning; the evaluator
sorts whatever it needs. A course appearing twice at the same period is a
violation, not a duplicate to collapse — see cost.py."""
