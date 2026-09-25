"""Availability grids of instructors, student groups, rooms and activities."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.errors import FieldError, InvalidInput, NotFound, PermissionDenied, StaleVersion
from optiedt.models import Activity, AvailabilityGrid, Instructor, Period, Room, StudentGroup
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.activities import department_of_activity
from optiedt.services.groups import department_of_group
from optiedt.services.terms import get_term

KINDS = ("instructor", "group", "room", "activity")
ALLOWED_STATES: dict[str, frozenset[str]] = {
    "instructor": frozenset({"preferred", "undesirable", "unavailable"}),
    "group": frozenset({"unavailable"}),
    "room": frozenset({"unavailable"}),
    "activity": frozenset({"unavailable"}),
}
_COLUMN = {
    "instructor": AvailabilityGrid.instructor_id,
    "group": AvailabilityGrid.group_id,
    "room": AvailabilityGrid.room_id,
    "activity": AvailabilityGrid.activity_id,
}


@dataclass(frozen=True, slots=True)
class Cell:
    weekday: int
    period_id: uuid.UUID
    state: str


def _resource_department(
    db: Session, term_id: uuid.UUID, kind: str, resource_id: uuid.UUID
) -> uuid.UUID | None:
    """The department that scopes edits of this resource; raises NotFound if absent."""
    if kind == "instructor":
        instructor = db.get(Instructor, resource_id)
        if instructor is None:
            raise NotFound("Instructor")
        return instructor.department_id
    if kind == "group":
        group = db.get(StudentGroup, resource_id)
        if group is None or group.term_id != term_id:
            raise NotFound("Student group")
        return department_of_group(db, group)
    if kind == "room":
        if db.get(Room, resource_id) is None:
            raise NotFound("Room")
        return None
    activity = db.get(Activity, resource_id)
    if activity is None or activity.term_id != term_id:
        raise NotFound("Activity")
    return department_of_activity(db, activity)


def _find(
    db: Session, term_id: uuid.UUID, kind: str, resource_id: uuid.UUID
) -> AvailabilityGrid | None:
    return db.scalar(
        select(AvailabilityGrid).where(
            AvailabilityGrid.term_id == term_id, _COLUMN[kind] == resource_id
        )
    )


def _check_kind(kind: str) -> None:
    if kind not in KINDS:
        raise NotFound("Availability kind")


def get_grid(
    db: Session, principal: Principal, term_id: uuid.UUID, kind: str, resource_id: uuid.UUID
) -> AvailabilityGrid | None:
    _check_kind(kind)
    get_term(db, term_id)
    _resource_department(db, term_id, kind, resource_id)
    own = kind == "instructor" and principal.instructor_id == resource_id
    if not own:
        principal.require(Permission.TERM_DATA_READ)
    return _find(db, term_id, kind, resource_id)


def declaration_open(term_open_until: date | None, today: date) -> bool:
    return term_open_until is not None and today <= term_open_until


def put_grid(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    kind: str,
    resource_id: uuid.UUID,
    *,
    version: int | None,
    cells: Sequence[Cell],
    today: date,
) -> AvailabilityGrid:
    _check_kind(kind)
    term = get_term(db, term_id)
    department = _resource_department(db, term_id, kind, resource_id)
    own = kind == "instructor" and principal.instructor_id == resource_id
    scope = principal.scope(Permission.AVAILABILITY_MANAGE)
    if scope.covers(department) or (department is None and scope.everywhere):
        source = "staff"
    elif own and principal.can(Permission.AVAILABILITY_SELF):
        if not declaration_open(term.availability_open_until, today):
            raise PermissionDenied("Availability declarations for this term are closed.")
        if term.status == "closed":
            raise PermissionDenied("This term is closed.")
        source = "self"
    else:
        raise PermissionDenied()

    periods = {str(p) for p in db.scalars(select(Period.id).where(Period.term_id == term_id))}
    allowed = ALLOWED_STATES[kind]
    errors = []
    seen: set[tuple[int, str]] = set()
    normalised: list[dict[str, Any]] = []
    for index, cell in enumerate(cells):
        key = (cell.weekday, str(cell.period_id))
        if cell.weekday not in term.weekdays:
            errors.append(FieldError(f"cells.{index}.weekday", "Not a teaching day."))
        if str(cell.period_id) not in periods:
            errors.append(FieldError(f"cells.{index}.period_id", "Not a period of this term."))
        if cell.state not in allowed:
            errors.append(
                FieldError(
                    f"cells.{index}.state",
                    f"Allowed states: {', '.join(sorted(allowed))}.",
                )
            )
        if key in seen:
            errors.append(FieldError(f"cells.{index}", "This slot appears twice."))
        seen.add(key)
        normalised.append(
            {"weekday": cell.weekday, "period_id": str(cell.period_id), "state": cell.state}
        )
    if errors:
        raise InvalidInput("The availability grid is invalid.", errors)
    normalised.sort(key=lambda c: (c["weekday"], c["period_id"]))

    grid = _find(db, term_id, kind, resource_id)
    before = grid.cells if grid else []
    if grid is None:
        grid = AvailabilityGrid(term_id=term_id, cells=normalised, source=source)
        setattr(grid, f"{kind}_id", resource_id)
        db.add(grid)
    else:
        if version is not None and version != grid.version:
            raise StaleVersion("availability grid")
        grid.cells = normalised
        grid.source = source
    grid.updated_by_id = principal.user_id
    db.flush()
    if before != normalised:
        audit.record(
            db,
            principal,
            action="availability.update",
            entity_type=f"{kind}_availability",
            entity_id=resource_id,
            term_id=term_id,
            summary=f"Updated {kind} availability ({len(normalised)} marked slots, by {source})",
            changes={"marked_slots": [len(before), len(normalised)]},
            department_ids=[department],
        )
    return grid


def list_grids(
    db: Session, principal: Principal, term_id: uuid.UUID, kind: str
) -> list[AvailabilityGrid]:
    _check_kind(kind)
    principal.require(Permission.TERM_DATA_READ)
    return list(
        db.scalars(
            select(AvailabilityGrid).where(
                AvailabilityGrid.term_id == term_id, _COLUMN[kind].is_not(None)
            )
        )
    )
