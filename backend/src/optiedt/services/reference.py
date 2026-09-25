"""Reference data: departments, campuses, buildings, rooms, programmes, courses, activity
types, instructors and dated calendar events."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, delete, or_, select
from sqlalchemy.orm import Session

from optiedt.errors import FieldError, InvalidInput
from optiedt.models import (
    ActivityType,
    Building,
    CalendarEvent,
    Campus,
    CampusTravelTime,
    Course,
    Department,
    Institution,
    Instructor,
    Programme,
    Room,
    RoomFeature,
    RoomType,
)
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import apply_changes, check_version, page
from optiedt.services.resources import Resource

P = Permission


def require_exists(
    db: Session, model: type[Any], record_id: uuid.UUID | None, field: str, label: str
) -> None:
    if record_id is not None and db.get(model, record_id) is None:
        raise InvalidInput(f"Unknown {label}.", [FieldError(field, f"No such {label}.")])


# ── validation hooks ───────────────────────────────────────────────────


def _validate_department(db: Session, existing: Department | None, values: dict[str, Any]) -> None:
    parent_id = values.get("parent_id", existing.parent_id if existing else None)
    require_exists(db, Department, parent_id, "parent_id", "parent department")
    if existing is None or parent_id is None:
        return
    seen = set()
    current: uuid.UUID | None = parent_id
    while current is not None and current not in seen:
        if current == existing.id:
            raise InvalidInput(
                "A department cannot be placed under itself or one of its sub-departments.",
                [FieldError("parent_id", "Would create a cycle.")],
            )
        seen.add(current)
        current = db.scalar(select(Department.parent_id).where(Department.id == current))


def _validate_building(db: Session, existing: Building | None, values: dict[str, Any]) -> None:
    require_exists(db, Campus, values.get("campus_id"), "campus_id", "campus")


def _validate_room(db: Session, existing: Room | None, values: dict[str, Any]) -> None:
    require_exists(db, Building, values.get("building_id"), "building_id", "building")
    require_exists(db, RoomType, values.get("room_type_id"), "room_type_id", "room type")
    require_exists(db, Department, values.get("department_id"), "department_id", "department")
    feature_ids = values.get("feature_ids")
    if feature_ids:
        found = set(db.scalars(select(RoomFeature.id).where(RoomFeature.id.in_(feature_ids))))
        if found != set(feature_ids):
            raise InvalidInput("Unknown room feature.", [FieldError("feature_ids", "Not found.")])


def _apply_room_features(db: Session, room: Room, extra: dict[str, Any]) -> dict[str, list[Any]]:
    if "feature_ids" not in extra:
        return {}
    wanted = list(dict.fromkeys(extra["feature_ids"] or []))
    before = sorted(str(f.id) for f in room.features)
    room.features = list(db.scalars(select(RoomFeature).where(RoomFeature.id.in_(wanted))))
    after = sorted(str(f) for f in wanted)
    return {"feature_ids": [before, after]} if before != after else {}


def _validate_department_ref(db: Session, existing: object, values: dict[str, Any]) -> None:
    require_exists(db, Department, values.get("department_id"), "department_id", "department")


def _validate_activity_type(
    db: Session, existing: ActivityType | None, values: dict[str, Any]
) -> None:
    require_exists(
        db, RoomType, values.get("default_room_type_id"), "default_room_type_id", "room type"
    )


def _validate_calendar_event(
    db: Session, existing: CalendarEvent | None, values: dict[str, Any]
) -> None:
    start = values.get("start_date", existing.start_date if existing else None)
    end = values.get("end_date", existing.end_date if existing else None)
    if start and end and end < start:
        raise InvalidInput(
            "The end date is before the start date.",
            [FieldError("end_date", "Must be on or after the start date.")],
        )


# ── resources ──────────────────────────────────────────────────────────

DEPARTMENTS = Resource(
    model=Department,
    label="department",
    audit_type="department",
    write_permission=P.CATALOGUE_MANAGE,
    describe=lambda d: f"{d.code} ({d.name})",
    duplicate_message="A department with this code already exists.",
    validate=_validate_department,
)
CAMPUSES = Resource(
    model=Campus,
    label="campus",
    audit_type="campus",
    write_permission=P.ORGANIZATION_MANAGE,
    describe=lambda c: f"{c.code} ({c.name})",
    duplicate_message="A campus with this code already exists.",
)
BUILDINGS = Resource(
    model=Building,
    label="building",
    audit_type="building",
    write_permission=P.ORGANIZATION_MANAGE,
    describe=lambda b: f"{b.code} ({b.name})",
    duplicate_message="A building with this code already exists on the campus.",
    validate=_validate_building,
)
ROOM_TYPES = Resource(
    model=RoomType,
    label="room type",
    audit_type="room_type",
    write_permission=P.ORGANIZATION_MANAGE,
    describe=lambda t: f"{t.code} ({t.name})",
    duplicate_message="A room type with this code already exists.",
)
ROOM_FEATURES = Resource(
    model=RoomFeature,
    label="room feature",
    audit_type="room_feature",
    write_permission=P.ORGANIZATION_MANAGE,
    describe=lambda f: f"{f.code} ({f.name})",
    duplicate_message="A room feature with this code already exists.",
)
ROOMS = Resource(
    model=Room,
    label="room",
    audit_type="room",
    write_permission=P.ORGANIZATION_MANAGE,
    describe=lambda r: r.code,
    duplicate_message="A room with this code already exists in the building.",
    validate=_validate_room,
    extra_fields=("feature_ids",),
    apply_extra=_apply_room_features,
)
PROGRAMMES = Resource(
    model=Programme,
    label="programme",
    audit_type="programme",
    write_permission=P.CATALOGUE_MANAGE,
    describe=lambda p: f"{p.code} ({p.name})",
    duplicate_message="A programme with this code already exists.",
    validate=_validate_department_ref,
)
COURSES = Resource(
    model=Course,
    label="course",
    audit_type="course",
    write_permission=P.COURSES_MANAGE,
    describe=lambda c: f"{c.code} ({c.title})",
    duplicate_message="A course with this code already exists.",
    department_of=lambda c: c.department_id,
    validate=_validate_department_ref,
)
ACTIVITY_TYPES = Resource(
    model=ActivityType,
    label="activity type",
    audit_type="activity_type",
    write_permission=P.CATALOGUE_MANAGE,
    describe=lambda t: f"{t.code} ({t.name})",
    duplicate_message="An activity type with this code already exists.",
    validate=_validate_activity_type,
)
INSTRUCTORS = Resource(
    model=Instructor,
    label="instructor",
    audit_type="instructor",
    write_permission=P.STAFF_MANAGE,
    describe=lambda i: f"{i.code} ({i.first_name} {i.last_name})",
    duplicate_message="An instructor with this staff code already exists.",
    department_of=lambda i: i.department_id,
    validate=_validate_department_ref,
)
CALENDAR_EVENTS = Resource(
    model=CalendarEvent,
    label="calendar event",
    audit_type="calendar_event",
    write_permission=P.TERMS_MANAGE,
    describe=lambda e: f"{e.label} ({e.start_date} to {e.end_date})",
    duplicate_message="This calendar event already exists.",
    validate=_validate_calendar_event,
)


# ── listing ────────────────────────────────────────────────────────────


def _search(statement: Select[Any], q: str | None, *columns: Any) -> Select[Any]:
    if not q:
        return statement
    like = f"%{q.strip()}%"
    return statement.where(or_(*(column.ilike(like) for column in columns)))


def list_rooms(
    db: Session,
    principal: Principal,
    *,
    q: str | None,
    campus_id: uuid.UUID | None,
    building_id: uuid.UUID | None,
    room_type_id: uuid.UUID | None,
    min_capacity: int | None,
    active: bool | None,
    offset: int,
    limit: int,
) -> tuple[Sequence[Room], int]:
    principal.require(P.REFERENCE_READ)
    statement = select(Room).join(Building, Building.id == Room.building_id)
    statement = _search(statement, q, Room.code, Room.name, Building.code, Building.name)
    if campus_id:
        statement = statement.where(Building.campus_id == campus_id)
    if building_id:
        statement = statement.where(Room.building_id == building_id)
    if room_type_id:
        statement = statement.where(Room.room_type_id == room_type_id)
    if min_capacity:
        statement = statement.where(Room.capacity >= min_capacity)
    if active is not None:
        statement = statement.where(Room.is_active.is_(active))
    statement = statement.order_by(Building.code, Room.code)
    return page(db, statement, offset=offset, limit=limit)


def list_instructors(
    db: Session,
    principal: Principal,
    *,
    q: str | None,
    department_id: uuid.UUID | None,
    active: bool | None,
    offset: int,
    limit: int,
) -> tuple[Sequence[Instructor], int]:
    principal.require(P.REFERENCE_READ)
    statement = _search(
        select(Instructor),
        q,
        Instructor.code,
        Instructor.first_name,
        Instructor.last_name,
        Instructor.email,
    )
    if department_id:
        statement = statement.where(Instructor.department_id == department_id)
    if active is not None:
        statement = statement.where(Instructor.is_active.is_(active))
    statement = statement.order_by(Instructor.last_name, Instructor.first_name)
    return page(db, statement, offset=offset, limit=limit)


def list_courses(
    db: Session,
    principal: Principal,
    *,
    q: str | None,
    department_id: uuid.UUID | None,
    active: bool | None,
    offset: int,
    limit: int,
) -> tuple[Sequence[Course], int]:
    principal.require(P.REFERENCE_READ)
    statement = _search(select(Course), q, Course.code, Course.title)
    if department_id:
        statement = statement.where(Course.department_id == department_id)
    if active is not None:
        statement = statement.where(Course.is_active.is_(active))
    statement = statement.order_by(Course.code)
    return page(db, statement, offset=offset, limit=limit)


def list_simple(
    db: Session,
    principal: Principal,
    model: type[Any],
    *,
    q: str | None,
    order: Sequence[Any],
    search: Sequence[Any],
    filters: Sequence[Any] = (),
    offset: int,
    limit: int,
) -> tuple[Sequence[Any], int]:
    principal.require(P.REFERENCE_READ)
    statement = _search(select(model), q, *search)
    for condition in filters:
        statement = statement.where(condition)
    return page(db, statement.order_by(*order), offset=offset, limit=limit)


# ── campus travel times ────────────────────────────────────────────────


def travel_times(db: Session, principal: Principal) -> list[CampusTravelTime]:
    principal.require(P.REFERENCE_READ)
    return list(db.scalars(select(CampusTravelTime)))


def set_travel_times(
    db: Session, principal: Principal, entries: Sequence[tuple[uuid.UUID, uuid.UUID, int]]
) -> list[CampusTravelTime]:
    """Replace the whole matrix. Pairs are unordered; each pair may appear once."""
    principal.require_everywhere(P.ORGANIZATION_MANAGE)
    normalised: dict[tuple[uuid.UUID, uuid.UUID], int] = {}
    errors = []
    campus_ids = set(db.scalars(select(Campus.id)))
    for index, (a, b, minutes) in enumerate(entries):
        if a == b:
            errors.append(FieldError(f"{index}", "A campus has no travel time to itself."))
            continue
        if a not in campus_ids or b not in campus_ids:
            errors.append(FieldError(f"{index}", "Unknown campus."))
            continue
        if minutes < 0 or minutes > 24 * 60:
            errors.append(FieldError(f"{index}.minutes", "Must be between 0 and 1440."))
            continue
        key = (a, b) if a < b else (b, a)
        if key in normalised:
            errors.append(FieldError(f"{index}", "This pair appears twice."))
            continue
        normalised[key] = minutes
    if errors:
        raise InvalidInput("Some travel times are invalid.", errors)
    before = {
        (str(t.campus_a_id), str(t.campus_b_id)): t.minutes for t in travel_times(db, principal)
    }
    db.execute(delete(CampusTravelTime))
    rows = [
        CampusTravelTime(campus_a_id=a, campus_b_id=b, minutes=m)
        for (a, b), m in normalised.items()
    ]
    db.add_all(rows)
    db.flush()
    after = {(str(a), str(b)): m for (a, b), m in normalised.items()}
    if before != after:
        audit.record(
            db,
            principal,
            action="campus.travel_times",
            entity_type="campus",
            entity_id=None,
            summary="Updated travel times between campuses",
            changes={"pairs": [len(before), len(after)]},
        )
    return rows


# ── institution ────────────────────────────────────────────────────────

INSTITUTION_DEFAULTS: dict[str, Any] = {
    "name": "Institution",
    "short_name": "INST",
    "timezone": "UTC",
    "default_locale": "en",
    "enabled_locales": ["en", "fr", "ar"],
    "week_start": 0,
    "date_format": "dd/MM/yyyy",
    "time_format": "HH:mm",
    "public_timetable_enabled": False,
    "approval_required": True,
    "assistant_enabled": False,
}


def get_institution(db: Session) -> Institution:
    institution = db.get(Institution, 1)
    if institution is None:
        institution = Institution(id=1, version=1, **INSTITUTION_DEFAULTS)
        db.add(institution)
        db.flush()
    return institution


def update_institution(
    db: Session, principal: Principal, *, version: int, values: dict[str, Any]
) -> Institution:
    principal.require_everywhere(P.INSTITUTION_MANAGE)
    institution = get_institution(db)
    check_version(institution, version, "institution")
    if "enabled_locales" in values or "default_locale" in values:
        locales = values.get("enabled_locales", institution.enabled_locales)
        default = values.get("default_locale", institution.default_locale)
        if default not in locales:
            raise InvalidInput(
                "The default language must be one of the enabled languages.",
                [FieldError("default_locale", "Not enabled.")],
            )
    changes = apply_changes(institution, values)
    db.flush()
    if changes:
        audit.record(
            db,
            principal,
            action="institution.update",
            entity_type="institution",
            entity_id="1",
            summary="Updated institution settings",
            changes=changes,
        )
    return institution
