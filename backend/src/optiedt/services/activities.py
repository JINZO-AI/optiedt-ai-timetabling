"""Activities of a term: what must be taught, to whom, by whom, how often and where."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from optiedt.errors import FieldError, InvalidInput, NotFound
from optiedt.models import (
    Activity,
    ActivityRoom,
    ActivityType,
    Building,
    Campus,
    Course,
    FixedPlacement,
    Instructor,
    Period,
    Room,
    RoomFeature,
    RoomType,
    StudentGroup,
    activity_features,
    activity_groups,
    activity_instructors,
)
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import apply_changes, check_version
from optiedt.services.terms import get_term

ROOM_KINDS = ("allowed", "preferred", "avoided")
SCALAR_FIELDS = (
    "course_id",
    "activity_type_id",
    "label",
    "duration",
    "sessions_per_week",
    "different_days",
    "delivery_mode",
    "room_type_id",
    "min_capacity",
    "campus_id",
    "building_id",
    "notes",
)


@dataclass(frozen=True, slots=True)
class FixedSpec:
    occurrence: int
    weekday: int
    period_id: uuid.UUID
    room_id: uuid.UUID | None = None


@dataclass
class ActivityDetails:
    activity: Activity
    group_ids: list[uuid.UUID] = field(default_factory=list)
    instructor_ids: list[uuid.UUID] = field(default_factory=list)
    feature_ids: list[uuid.UUID] = field(default_factory=list)
    rooms: list[tuple[uuid.UUID, str]] = field(default_factory=list)
    fixed: list[FixedSpec] = field(default_factory=list)


def department_of_activity(db: Session, activity: Activity) -> uuid.UUID | None:
    return db.scalar(select(Course.department_id).where(Course.id == activity.course_id))


def _course_department(db: Session, course_id: uuid.UUID) -> uuid.UUID:
    department = db.scalar(select(Course.department_id).where(Course.id == course_id))
    if department is None:
        raise InvalidInput("Unknown course.", [FieldError("course_id", "Not found.")])
    return department


def _get(db: Session, term_id: uuid.UUID, activity_id: uuid.UUID) -> Activity:
    activity = db.get(Activity, activity_id)
    if activity is None or activity.term_id != term_id:
        raise NotFound("Activity")
    return activity


def load_details(db: Session, activities: Sequence[Activity]) -> list[ActivityDetails]:
    """Bulk-load every link of the given activities (five queries, whatever their number)."""
    details = {a.id: ActivityDetails(activity=a) for a in activities}
    ids = list(details)
    if not ids:
        return []
    for activity_id, group_id in db.execute(
        select(activity_groups.c.activity_id, activity_groups.c.group_id).where(
            activity_groups.c.activity_id.in_(ids)
        )
    ):
        details[activity_id].group_ids.append(group_id)
    for activity_id, instructor_id in db.execute(
        select(activity_instructors.c.activity_id, activity_instructors.c.instructor_id).where(
            activity_instructors.c.activity_id.in_(ids)
        )
    ):
        details[activity_id].instructor_ids.append(instructor_id)
    for activity_id, feature_id in db.execute(
        select(activity_features.c.activity_id, activity_features.c.feature_id).where(
            activity_features.c.activity_id.in_(ids)
        )
    ):
        details[activity_id].feature_ids.append(feature_id)
    for link in db.scalars(select(ActivityRoom).where(ActivityRoom.activity_id.in_(ids))):
        details[link.activity_id].rooms.append((link.room_id, link.kind))
    for fixed in db.scalars(
        select(FixedPlacement)
        .where(FixedPlacement.activity_id.in_(ids))
        .order_by(FixedPlacement.occurrence)
    ):
        details[fixed.activity_id].fixed.append(
            FixedSpec(fixed.occurrence, fixed.weekday, fixed.period_id, fixed.room_id)
        )
    for item in details.values():
        item.group_ids.sort()
        item.instructor_ids.sort()
        item.feature_ids.sort()
        item.rooms.sort()
    return [details[a.id] for a in activities]


def _existing_ids(db: Session, column: Any, ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    wanted = list(set(ids))
    if not wanted:
        return set()
    return set(db.scalars(select(column).where(column.in_(wanted))))


def _validate(
    db: Session,
    term_id: uuid.UUID,
    merged: dict[str, Any],
) -> None:
    """``merged`` holds the complete proposed state: scalars and link lists."""
    term = get_term(db, term_id)
    errors: list[FieldError] = []

    if db.get(Course, merged["course_id"]) is None:
        errors.append(FieldError("course_id", "Unknown course."))
    if db.get(ActivityType, merged["activity_type_id"]) is None:
        errors.append(FieldError("activity_type_id", "Unknown activity type."))

    period_count = len(list(db.scalars(select(Period.id).where(Period.term_id == term_id))))
    if merged["duration"] > period_count:
        errors.append(FieldError("duration", f"The term has only {period_count} periods per day."))
    if merged["different_days"] and merged["sessions_per_week"] > len(term.weekdays):
        errors.append(
            FieldError(
                "sessions_per_week",
                f"{merged['sessions_per_week']} sessions on different days need more than "
                f"{len(term.weekdays)} teaching days.",
            )
        )

    group_ids = merged["group_ids"]
    if not group_ids:
        errors.append(FieldError("group_ids", "An activity needs at least one student group."))
    else:
        found = set(
            db.scalars(
                select(StudentGroup.id).where(
                    StudentGroup.id.in_(group_ids), StudentGroup.term_id == term_id
                )
            )
        )
        if found != set(group_ids):
            errors.append(FieldError("group_ids", "A group does not belong to this term."))
    if len(set(group_ids)) != len(group_ids):
        errors.append(FieldError("group_ids", "A group is listed twice."))

    instructor_ids = merged["instructor_ids"]
    if len(set(instructor_ids)) != len(instructor_ids):
        errors.append(FieldError("instructor_ids", "An instructor is listed twice."))
    if instructor_ids:
        active = set(
            db.scalars(
                select(Instructor.id).where(
                    Instructor.id.in_(instructor_ids), Instructor.is_active.is_(True)
                )
            )
        )
        if active != set(instructor_ids):
            errors.append(FieldError("instructor_ids", "Unknown or inactive instructor."))

    online = merged["delivery_mode"] == "online"
    if merged["room_type_id"] and db.get(RoomType, merged["room_type_id"]) is None:
        errors.append(FieldError("room_type_id", "Unknown room type."))
    if _existing_ids(db, RoomFeature.id, merged["feature_ids"]) != set(merged["feature_ids"]):
        errors.append(FieldError("feature_ids", "Unknown room feature."))
    campus_id, building_id = merged["campus_id"], merged["building_id"]
    if campus_id and db.get(Campus, campus_id) is None:
        errors.append(FieldError("campus_id", "Unknown campus."))
    if building_id:
        building = db.get(Building, building_id)
        if building is None:
            errors.append(FieldError("building_id", "Unknown building."))
        elif campus_id and building.campus_id != campus_id:
            errors.append(FieldError("building_id", "The building is not on the chosen campus."))

    rooms = merged["rooms"]
    room_ids = [room_id for room_id, _ in rooms]
    if len(set(room_ids)) != len(room_ids):
        errors.append(FieldError("rooms", "A room is listed twice."))
    if any(kind not in ROOM_KINDS for _, kind in rooms):
        errors.append(FieldError("rooms", "Room kind must be allowed, preferred or avoided."))
    fixed_rooms = [f.room_id for f in merged["fixed"] if f.room_id]
    if _existing_ids(db, Room.id, room_ids + fixed_rooms) != set(room_ids + fixed_rooms):
        errors.append(FieldError("rooms", "Unknown room."))

    if online and (
        merged["room_type_id"]
        or merged["feature_ids"]
        or rooms
        or campus_id
        or building_id
        or fixed_rooms
    ):
        errors.append(
            FieldError(
                "delivery_mode",
                "Online activities take no room, so room requirements do not apply.",
            )
        )

    term_periods = set(db.scalars(select(Period.id).where(Period.term_id == term_id)))
    occurrences = [f.occurrence for f in merged["fixed"]]
    if len(set(occurrences)) != len(occurrences):
        errors.append(FieldError("fixed", "An occurrence is fixed twice."))
    for index, fixed in enumerate(merged["fixed"]):
        if not 1 <= fixed.occurrence <= merged["sessions_per_week"]:
            errors.append(
                FieldError(f"fixed.{index}.occurrence", "No such occurrence of the activity.")
            )
        if fixed.weekday not in term.weekdays:
            errors.append(FieldError(f"fixed.{index}.weekday", "Not a teaching day."))
        if fixed.period_id not in term_periods:
            errors.append(FieldError(f"fixed.{index}.period_id", "Not a period of this term."))
    if errors:
        raise InvalidInput("The activity is invalid.", errors)


def _write_links(
    db: Session, activity: Activity, merged: dict[str, Any], replace: set[str]
) -> None:
    activity_id = activity.id
    if "group_ids" in replace:
        db.execute(delete(activity_groups).where(activity_groups.c.activity_id == activity_id))
        if merged["group_ids"]:
            db.execute(
                insert(activity_groups),
                [
                    {"term_id": activity.term_id, "activity_id": activity_id, "group_id": g}
                    for g in merged["group_ids"]
                ],
            )
    if "instructor_ids" in replace:
        db.execute(
            delete(activity_instructors).where(activity_instructors.c.activity_id == activity_id)
        )
        if merged["instructor_ids"]:
            db.execute(
                insert(activity_instructors),
                [
                    {"activity_id": activity_id, "instructor_id": i}
                    for i in merged["instructor_ids"]
                ],
            )
    if "feature_ids" in replace:
        db.execute(delete(activity_features).where(activity_features.c.activity_id == activity_id))
        if merged["feature_ids"]:
            db.execute(
                insert(activity_features),
                [{"activity_id": activity_id, "feature_id": f} for f in merged["feature_ids"]],
            )
    if "rooms" in replace:
        db.execute(delete(ActivityRoom).where(ActivityRoom.activity_id == activity_id))
        db.add_all(
            ActivityRoom(activity_id=activity_id, room_id=room_id, kind=kind)
            for room_id, kind in merged["rooms"]
        )
    if "fixed" in replace:
        db.execute(delete(FixedPlacement).where(FixedPlacement.activity_id == activity_id))
        db.add_all(
            FixedPlacement(
                activity_id=activity_id,
                occurrence=f.occurrence,
                weekday=f.weekday,
                period_id=f.period_id,
                room_id=f.room_id,
            )
            for f in merged["fixed"]
        )


LINK_FIELDS = ("group_ids", "instructor_ids", "feature_ids", "rooms", "fixed")


def _link_summary(details: ActivityDetails) -> dict[str, Any]:
    return {
        "group_ids": [str(g) for g in details.group_ids],
        "instructor_ids": [str(i) for i in details.instructor_ids],
        "feature_ids": [str(f) for f in details.feature_ids],
        "rooms": sorted([str(r), k] for r, k in details.rooms),
        "fixed": [
            [f.occurrence, f.weekday, str(f.period_id), str(f.room_id or "")] for f in details.fixed
        ],
    }


def create_activity(
    db: Session, principal: Principal, term_id: uuid.UUID, values: dict[str, Any]
) -> ActivityDetails:
    principal.require(Permission.TERM_DATA_MANAGE, _course_department(db, values["course_id"]))
    merged = {
        "label": None,
        "duration": 1,
        "sessions_per_week": 1,
        "different_days": True,
        "delivery_mode": "in_person",
        "room_type_id": None,
        "min_capacity": None,
        "campus_id": None,
        "building_id": None,
        "notes": None,
        "group_ids": [],
        "instructor_ids": [],
        "feature_ids": [],
        "rooms": [],
        "fixed": [],
        **values,
    }
    _validate(db, term_id, merged)
    activity = Activity(term_id=term_id, **{k: merged[k] for k in SCALAR_FIELDS})
    db.add(activity)
    db.flush()
    _write_links(db, activity, merged, set(LINK_FIELDS))
    db.flush()
    details = load_details(db, [activity])[0]
    audit.record(
        db,
        principal,
        action="activity.create",
        entity_type="activity",
        entity_id=activity.id,
        term_id=term_id,
        summary=f"Created activity {describe(db, activity)}",
        changes=audit.field_changes({}, _link_summary(details)),
        department_ids=[department_of_activity(db, activity)],
    )
    return details


def update_activity(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    activity_id: uuid.UUID,
    *,
    version: int,
    values: dict[str, Any],
) -> ActivityDetails:
    activity = _get(db, term_id, activity_id)
    department = department_of_activity(db, activity)
    principal.require(Permission.TERM_DATA_MANAGE, department)
    if "course_id" in values:
        principal.require(Permission.TERM_DATA_MANAGE, _course_department(db, values["course_id"]))
    check_version(activity, version, "activity")
    current = load_details(db, [activity])[0]
    merged: dict[str, Any] = {name: getattr(activity, name) for name in SCALAR_FIELDS}
    merged.update(
        group_ids=current.group_ids,
        instructor_ids=current.instructor_ids,
        feature_ids=current.feature_ids,
        rooms=current.rooms,
        fixed=current.fixed,
    )
    merged.update(values)
    _validate(db, term_id, merged)

    before_links = _link_summary(current)
    changes = apply_changes(activity, {k: v for k, v in values.items() if k in SCALAR_FIELDS})
    replace = {k for k in values if k in LINK_FIELDS}
    _write_links(db, activity, merged, replace)
    db.flush()
    updated = load_details(db, [activity])[0]
    link_changes = audit.field_changes(before_links, _link_summary(updated))
    if link_changes and not changes:
        activity.updated_at = datetime.now(UTC)
        db.flush()
    changes.update(link_changes)
    if changes:
        audit.record(
            db,
            principal,
            action="activity.update",
            entity_type="activity",
            entity_id=activity.id,
            term_id=term_id,
            summary=f"Updated activity {describe(db, activity)}",
            changes=changes,
            department_ids=[department, department_of_activity(db, activity)],
        )
    return updated


def delete_activity(
    db: Session, principal: Principal, term_id: uuid.UUID, activity_id: uuid.UUID
) -> None:
    activity = _get(db, term_id, activity_id)
    department = department_of_activity(db, activity)
    principal.require(Permission.TERM_DATA_MANAGE, department)
    description = describe(db, activity)
    db.delete(activity)
    db.flush()
    audit.record(
        db,
        principal,
        action="activity.delete",
        entity_type="activity",
        entity_id=activity_id,
        term_id=term_id,
        summary=f"Deleted activity {description}",
        department_ids=[department],
    )


def describe(db: Session, activity: Activity) -> str:
    course = db.get(Course, activity.course_id)
    kind = db.get(ActivityType, activity.activity_type_id)
    base = f"{course.code if course else '?'} {kind.code if kind else ''}".strip()
    return f"{base} — {activity.label}" if activity.label else base


def list_activities(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    *,
    department_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
    instructor_id: uuid.UUID | None = None,
) -> list[ActivityDetails]:
    principal.require(Permission.TERM_DATA_READ)
    get_term(db, term_id)
    statement = (
        select(Activity)
        .join(Course, Course.id == Activity.course_id)
        .where(Activity.term_id == term_id)
        .order_by(Course.code, Activity.activity_type_id, Activity.label)
    )
    if department_id:
        statement = statement.where(Course.department_id == department_id)
    if course_id:
        statement = statement.where(Activity.course_id == course_id)
    if group_id:
        statement = statement.where(
            Activity.id.in_(
                select(activity_groups.c.activity_id).where(activity_groups.c.group_id == group_id)
            )
        )
    if instructor_id:
        statement = statement.where(
            Activity.id.in_(
                select(activity_instructors.c.activity_id).where(
                    activity_instructors.c.instructor_id == instructor_id
                )
            )
        )
    return load_details(db, list(db.scalars(statement)))


def get_activity(
    db: Session, principal: Principal, term_id: uuid.UUID, activity_id: uuid.UUID
) -> ActivityDetails:
    principal.require(Permission.TERM_DATA_READ)
    return load_details(db, [_get(db, term_id, activity_id)])[0]


def workload_by_instructor(details: Sequence[ActivityDetails]) -> dict[uuid.UUID, int]:
    """Weekly periods each instructor must teach."""
    load: dict[uuid.UUID, int] = defaultdict(int)
    for item in details:
        periods = item.activity.duration * item.activity.sessions_per_week
        for instructor_id in item.instructor_ids:
            load[instructor_id] += periods
    return dict(load)
