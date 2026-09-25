"""Compiling a term's live data into an immutable problem snapshot (ADR 0008)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.models import (
    Activity,
    ActivityType,
    AvailabilityGrid,
    Building,
    Campus,
    CampusTravelTime,
    ConstraintRule,
    Course,
    Department,
    Instructor,
    ObjectiveProfile,
    Period,
    ProblemSnapshot,
    Programme,
    Room,
    RoomFeature,
    RoomType,
    SlotSetting,
    StudentGroup,
)
from optiedt.problem.snapshot import (
    SActivity,
    SActivityType,
    SBuilding,
    SCampus,
    SCourse,
    SDay,
    SDepartment,
    SFixed,
    SGroup,
    SInstructor,
    SNamed,
    Snapshot,
    SObjectiveSetting,
    SPeriod,
    SProfile,
    SRoom,
    SRule,
    SSession,
    SSlot,
    STerm,
    content_hash,
    session_id,
)
from optiedt.security.permissions import expand_departments
from optiedt.services.activities import load_details
from optiedt.services.reference import get_institution
from optiedt.services.terms import get_term

Slot = tuple[int, int]


def _hhmm(value: Any) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


def compile_snapshot(db: Session, term_id: uuid.UUID) -> Snapshot:
    term = get_term(db, term_id)
    institution = get_institution(db)
    periods = list(
        db.scalars(select(Period).where(Period.term_id == term_id).order_by(Period.position))
    )
    period_index = {p.id: i for i, p in enumerate(periods)}
    day_index = {weekday: i for i, weekday in enumerate(term.weekdays)}

    def slot(weekday: int, period_id: uuid.UUID | str) -> Slot | None:
        key = uuid.UUID(str(period_id))
        if weekday not in day_index or key not in period_index:
            return None
        return (day_index[weekday], period_index[key])

    slots = []
    for setting in db.scalars(select(SlotSetting).where(SlotSetting.term_id == term_id)):
        position = slot(setting.weekday, setting.period_id)
        if position is None:
            continue
        slots.append(
            SSlot(
                day=position[0],
                period=position[1],
                closed=setting.is_closed,
                penalty=setting.penalty,
                start=_hhmm(setting.start_time) if setting.start_time else None,
                end=_hhmm(setting.end_time) if setting.end_time else None,
                reason=setting.closed_reason,
            )
        )
    slots.sort(key=lambda s: (s.day, s.period))

    grids: dict[tuple[str, uuid.UUID], dict[str, list[Slot]]] = {}
    for grid in db.scalars(select(AvailabilityGrid).where(AvailabilityGrid.term_id == term_id)):
        for kind in ("instructor", "group", "room", "activity"):
            resource = getattr(grid, f"{kind}_id")
            if resource is None:
                continue
            by_state: dict[str, list[Slot]] = {}
            for cell in grid.cells:
                position = slot(int(cell["weekday"]), cell["period_id"])
                if position is not None:
                    by_state.setdefault(cell["state"], []).append(position)
            grids[(kind, resource)] = {k: sorted(v) for k, v in by_state.items()}

    def states(kind: str, resource: uuid.UUID, state: str) -> list[Slot]:
        return grids.get((kind, resource), {}).get(state, [])

    activities = list(
        db.scalars(
            select(Activity)
            .where(Activity.term_id == term_id)
            .order_by(Activity.created_at, Activity.id)
        )
    )
    details = load_details(db, activities)
    groups = list(
        db.scalars(
            select(StudentGroup).where(StudentGroup.term_id == term_id).order_by(StudentGroup.code)
        )
    )
    group_size = {g.id: g.size for g in groups}
    programme_department = dict(db.execute(select(Programme.id, Programme.department_id)).all())

    instructor_ids = sorted({i for d in details for i in d.instructor_ids})
    instructors = list(
        db.scalars(
            select(Instructor).where(Instructor.id.in_(instructor_ids)).order_by(Instructor.code)
        )
    )
    course_ids = sorted({d.activity.course_id for d in details})
    courses = list(
        db.scalars(select(Course).where(Course.id.in_(course_ids)).order_by(Course.code))
    )
    type_ids = sorted({d.activity.activity_type_id for d in details})
    activity_types = list(
        db.scalars(
            select(ActivityType).where(ActivityType.id.in_(type_ids)).order_by(ActivityType.code)
        )
    )
    default_room_type = {t.id: t.default_room_type_id for t in activity_types}

    rooms = list(
        db.scalars(select(Room).where(Room.is_active.is_(True)).order_by(Room.code, Room.id))
    )
    buildings = {b.id: b for b in db.scalars(select(Building))}
    campuses = sorted(
        {buildings[r.building_id].campus_id for r in rooms}
        | {d.activity.campus_id for d in details if d.activity.campus_id},
        key=str,
    )
    campus_rows = {c.id: c for c in db.scalars(select(Campus).where(Campus.id.in_(campuses)))}

    departments = list(db.scalars(select(Department).order_by(Department.code)))
    parent_of = {d.id: d.parent_id for d in departments}

    snapshot_activities = []
    snapshot_sessions = []
    for item in details:
        a = item.activity
        online = a.delivery_mode == "online"
        room_type = (
            None if online else (a.room_type_id or default_room_type.get(a.activity_type_id))
        )
        seats = a.min_capacity or sum(group_size.get(g, 0) for g in item.group_ids)
        fixed = []
        for f in item.fixed:
            position = slot(f.weekday, f.period_id)
            if position is not None:
                fixed.append(
                    SFixed(
                        occurrence=f.occurrence,
                        day=position[0],
                        period=position[1],
                        room_id=str(f.room_id) if f.room_id else None,
                    )
                )
        snapshot_activities.append(
            SActivity(
                id=str(a.id),
                course_id=str(a.course_id),
                type_id=str(a.activity_type_id),
                label=a.label,
                duration=a.duration,
                sessions_per_week=a.sessions_per_week,
                different_days=a.different_days and a.sessions_per_week > 1,
                online=online,
                room_type_id=str(room_type) if room_type else None,
                features=sorted(str(f) for f in item.feature_ids),
                min_capacity=max(seats, 1),
                campus_id=str(a.campus_id) if a.campus_id else None,
                building_id=str(a.building_id) if a.building_id else None,
                allowed_rooms=sorted(str(r) for r, k in item.rooms if k == "allowed"),
                preferred_rooms=sorted(str(r) for r, k in item.rooms if k == "preferred"),
                avoided_rooms=sorted(str(r) for r, k in item.rooms if k == "avoided"),
                group_ids=[str(g) for g in item.group_ids],
                instructor_ids=[str(i) for i in item.instructor_ids],
                unavailable=states("activity", a.id, "unavailable"),
                fixed=sorted(fixed, key=lambda f: f.occurrence),
            )
        )
        for occurrence in range(1, a.sessions_per_week + 1):
            snapshot_sessions.append(
                SSession(
                    id=str(session_id(a.id, occurrence)),
                    activity_id=str(a.id),
                    occurrence=occurrence,
                )
            )

    snapshot_groups = [
        SGroup(
            id=str(g.id),
            code=g.code,
            name=g.name,
            parent_id=str(g.parent_id) if g.parent_id else None,
            partition=g.partition_key,
            size=g.size,
            department_id=str(programme_department[g.programme_id])
            if g.programme_id in programme_department
            else None,
            unavailable=states("group", g.id, "unavailable"),
        )
        for g in groups
    ]

    rules = _compile_rules(
        db,
        term_id,
        instructors=instructors,
        group_ids=[g.id for g in groups],
        activity_ids={a.id for a in activities},
        parent_of=parent_of,
        slot=slot,
        period_index=period_index,
    )

    travel = sorted(
        (str(t.campus_a_id), str(t.campus_b_id), t.minutes)
        for t in db.scalars(select(CampusTravelTime))
        if t.campus_a_id in campus_rows and t.campus_b_id in campus_rows
    )

    return Snapshot(
        term=STerm(
            id=str(term.id),
            code=term.code,
            name=term.name,
            start_date=term.start_date.isoformat(),
            end_date=term.end_date.isoformat(),
            timezone=institution.timezone,
            room_capacity_ratio=term.room_capacity_ratio,
        ),
        days=[SDay(index=i, weekday=w) for i, w in enumerate(term.weekdays)],
        periods=[
            SPeriod(
                id=str(p.id),
                index=i,
                label=p.label,
                start=_hhmm(p.start_time),
                end=_hhmm(p.end_time),
                joins_next=p.joins_next and i < len(periods) - 1,
            )
            for i, p in enumerate(periods)
        ],
        slots=slots,
        campuses=[
            SCampus(id=str(c.id), code=c.code, name=c.name)
            for c in sorted(campus_rows.values(), key=lambda c: c.code)
        ],
        travel_minutes=travel,
        buildings=[
            SBuilding(id=str(b.id), code=b.code, name=b.name, campus_id=str(b.campus_id))
            for b in sorted(buildings.values(), key=lambda b: (b.code, str(b.id)))
            if b.campus_id in campus_rows
        ],
        room_types=[
            SNamed(id=str(t.id), code=t.code, name=t.name)
            for t in db.scalars(select(RoomType).order_by(RoomType.code))
        ],
        features=[
            SNamed(id=str(f.id), code=f.code, name=f.name)
            for f in db.scalars(select(RoomFeature).order_by(RoomFeature.code))
        ],
        rooms=[
            SRoom(
                id=str(r.id),
                code=r.code,
                name=r.name,
                building_id=str(r.building_id),
                campus_id=str(buildings[r.building_id].campus_id),
                type_id=str(r.room_type_id),
                capacity=r.capacity,
                features=sorted(str(f.id) for f in r.features),
                department_id=str(r.department_id) if r.department_id else None,
                unavailable=states("room", r.id, "unavailable"),
            )
            for r in rooms
        ],
        departments=[
            SDepartment(
                id=str(d.id),
                code=d.code,
                name=d.name,
                parent_id=str(d.parent_id) if d.parent_id else None,
            )
            for d in departments
        ],
        instructors=[
            SInstructor(
                id=str(i.id),
                code=i.code,
                name=f"{i.first_name} {i.last_name}",
                email=i.email,
                department_id=str(i.department_id),
                max_weekly_periods=i.max_weekly_periods,
                active=i.is_active,
                unavailable=states("instructor", i.id, "unavailable"),
                undesirable=states("instructor", i.id, "undesirable"),
                preferred=states("instructor", i.id, "preferred"),
            )
            for i in instructors
        ],
        groups=snapshot_groups,
        courses=[
            SCourse(id=str(c.id), code=c.code, title=c.title, department_id=str(c.department_id))
            for c in courses
        ],
        activity_types=[
            SActivityType(id=str(t.id), code=t.code, name=t.name, color=t.color)
            for t in activity_types
        ],
        activities=snapshot_activities,
        sessions=snapshot_sessions,
        rules=rules,
        profiles=[
            SProfile(
                code=p.code,
                name=p.name,
                objectives={
                    code: SObjectiveSetting.model_validate(setting)
                    for code, setting in sorted(p.objectives.items())
                },
            )
            for p in db.scalars(
                select(ObjectiveProfile)
                .where(ObjectiveProfile.term_id == term_id)
                .order_by(ObjectiveProfile.position, ObjectiveProfile.code)
            )
        ],
    )


def _compile_rules(
    db: Session,
    term_id: uuid.UUID,
    *,
    instructors: Iterable[Instructor],
    group_ids: list[uuid.UUID],
    activity_ids: set[uuid.UUID],
    parent_of: dict[uuid.UUID, uuid.UUID | None],
    slot: Any,
    period_index: dict[uuid.UUID, int],
) -> list[SRule]:
    instructors = list(instructors)
    known_instructors = {i.id for i in instructors}
    known_groups = set(group_ids)
    compiled = []
    for rule in db.scalars(
        select(ConstraintRule)
        .where(ConstraintRule.term_id == term_id, ConstraintRule.is_enabled.is_(True))
        .order_by(ConstraintRule.created_at, ConstraintRule.id)
    ):
        scope = rule.scope
        target_instructors: set[uuid.UUID] = set()
        target_groups: set[uuid.UUID] = set()
        target_activities: list[uuid.UUID] = []
        if scope.get("all_instructors"):
            target_instructors |= known_instructors
        if scope.get("all_groups"):
            target_groups |= known_groups
        target_instructors |= {
            uuid.UUID(i) for i in scope.get("instructor_ids", [])
        } & known_instructors
        target_groups |= {uuid.UUID(g) for g in scope.get("group_ids", [])} & known_groups
        if scope.get("department_ids"):
            covered = expand_departments({uuid.UUID(d) for d in scope["department_ids"]}, parent_of)
            target_instructors |= {i.id for i in instructors if i.department_id in covered}
        ordered = False
        if scope.get("first_activity_id"):
            target_activities = [
                uuid.UUID(scope["first_activity_id"]),
                uuid.UUID(scope["second_activity_id"]),
            ]
            ordered = True
        else:
            target_activities = [uuid.UUID(a) for a in scope.get("activity_ids", [])]
        target_activities = [a for a in target_activities if a in activity_ids]

        params = dict(rule.params)
        if "period_ids" in params:
            params["periods"] = sorted(
                period_index[uuid.UUID(p)]
                for p in params.pop("period_ids")
                if uuid.UUID(p) in period_index
            )
        if "period_id" in params:
            period = uuid.UUID(params.pop("period_id"))
            if period not in period_index:
                continue
            params["period"] = period_index[period]
        if "slots" in params:
            resolved = [slot(s["weekday"], s["period_id"]) for s in params.pop("slots")]
            params["slots"] = sorted(s for s in resolved if s is not None)

        compiled.append(
            SRule(
                id=str(rule.id),
                type=rule.rule_type,
                name=rule.name,
                enforcement=rule.enforcement,
                tier=rule.tier,
                weight=rule.weight,
                params=params,
                instructor_ids=sorted(str(i) for i in target_instructors),
                group_ids=sorted(str(g) for g in target_groups),
                activity_ids=[str(a) for a in target_activities],
                ordered=ordered,
            )
        )
    return compiled


def store_snapshot(db: Session, term_id: uuid.UUID, snapshot: Snapshot) -> ProblemSnapshot:
    payload = snapshot.model_dump(mode="json")
    digest = content_hash(payload)
    existing = db.scalar(
        select(ProblemSnapshot).where(
            ProblemSnapshot.term_id == term_id, ProblemSnapshot.content_hash == digest
        )
    )
    if existing is not None:
        return existing
    row = ProblemSnapshot(
        term_id=term_id,
        content_hash=digest,
        schema_version=snapshot.schema_version,
        payload=payload,
        stats={
            "activities": len(snapshot.activities),
            "sessions": len(snapshot.sessions),
            "periods_to_place": sum(a.duration * a.sessions_per_week for a in snapshot.activities),
            "rooms": len(snapshot.rooms),
            "instructors": len(snapshot.instructors),
            "groups": len(snapshot.groups),
            "rules": len(snapshot.rules),
        },
    )
    db.add(row)
    db.flush()
    return row


def load_snapshot(row: ProblemSnapshot) -> Snapshot:
    return Snapshot.model_validate(row.payload)
