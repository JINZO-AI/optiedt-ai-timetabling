"""The Instance aggregate — everything loaded from data/instance/, in one place.

Pure: just tuples of entities and a plain dict for calendar configuration. No
behaviour, no I/O. Consumers (the loader in optiedt.instance, the solver, later
the analysis layer) build whatever lookups they need from these tuples rather
than this module maintaining indices nobody asked for yet.

⚠️ **`students` is loaded but used ONLY by the examination model (X1).** It was
excluded entirely until Phase 13, on the reasoning that it would be dead weight
in every weekly solve. FR-20 made it live: X1 is stated per individual student,
*"whereas two students of the same group may present different optional
courses"* (SRS §6.8). Nothing in the weekly pipeline reads it, and the field
defaults to empty — a department dataset supplied through FR-1 carries no
roster, because `students.csv` is not one of the eleven files that contract
admits. See docs/constraint-model.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from optiedt.domain.entities import (
    Availability,
    ConstraintDefinition,
    Course,
    Group,
    Holiday,
    Programme,
    Promotion,
    Room,
    Session,
    Slot,
    Student,
    Teacher,
)


@dataclass(frozen=True, slots=True)
class Instance:
    """The reference instance: the 13 files of `data/instance/`."""

    programmes: tuple[Programme, ...]
    promotions: tuple[Promotion, ...]
    groups: tuple[Group, ...]
    teachers: tuple[Teacher, ...]
    courses: tuple[Course, ...]
    sessions: tuple[Session, ...]
    rooms: tuple[Room, ...]
    slots: tuple[Slot, ...]
    availability: tuple[Availability, ...]
    holidays: tuple[Holiday, ...]
    calendar_config: dict[str, str]
    constraints: tuple[ConstraintDefinition, ...]
    students: tuple[Student, ...] = ()
    """Individual students. Read by the examination model (X1) and nothing else.

    ⚠️ Defaults to empty rather than being required, and that default carries
    meaning: a dataset supplied through FR-1 has no roster, because
    `students.csv` is not among the eleven files `instance/validation.py`
    admits. An examination session on such a dataset is refused with that
    reason rather than solved against zero candidates.
    """
