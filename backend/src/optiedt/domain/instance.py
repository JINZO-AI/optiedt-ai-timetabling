"""The Instance aggregate — everything loaded from data/instance/, in one place.

Pure: just tuples of entities and a plain dict for calendar configuration. No
behaviour, no I/O. Consumers (the loader in optiedt.instance, the solver, later
the analysis layer) build whatever lookups they need from these tuples rather
than this module maintaining indices nobody asked for yet.

Deliberately excludes Student: the 425 students exist only for the examination
model (X1), which is increment 2. Loading them into Instance now would be dead
weight carried through every Phase 2 solve. See docs/constraint-model.md.
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
    Teacher,
)


@dataclass(frozen=True, slots=True)
class Instance:
    """The reference instance: 13 files, minus students.csv (see module docstring)."""

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
