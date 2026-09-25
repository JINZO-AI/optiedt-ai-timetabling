"""Reference data: institution settings, organisation, catalogue, staff and calendar."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from optiedt.api.crud_routes import register_crud
from optiedt.api.deps import AuthDep, DbSession, PageDep, PrincipalDep
from optiedt.api.schemas import reference as s
from optiedt.api.schemas.common import Page
from optiedt.models import (
    ActivityType,
    Building,
    CalendarEvent,
    Campus,
    Department,
    Programme,
    RoomFeature,
    RoomType,
)
from optiedt.services import reference

Search = Annotated[str | None, Query(max_length=100)]


def _page[T](items: list[T], total: int, paging: PageDep) -> Page[T]:
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


# ── institution ────────────────────────────────────────────────────────

institution_router = APIRouter(prefix="/institution", tags=["institution"])


@institution_router.get("", response_model=s.InstitutionOut)
def get_institution(db: DbSession, _: AuthDep) -> s.InstitutionOut:
    institution = reference.get_institution(db)
    db.commit()
    return s.InstitutionOut.model_validate(institution)


@institution_router.patch("", response_model=s.InstitutionOut)
def update_institution(
    body: s.InstitutionPatch, db: DbSession, principal: PrincipalDep
) -> s.InstitutionOut:
    institution = reference.update_institution(
        db, principal, version=body.version, values=body.changes()
    )
    db.commit()
    return s.InstitutionOut.model_validate(institution)


# ── departments ────────────────────────────────────────────────────────

departments_router = APIRouter(prefix="/departments", tags=["organisation"])


@departments_router.get("", response_model=Page[s.DepartmentOut])
def list_departments(
    db: DbSession, principal: PrincipalDep, paging: PageDep, q: Search = None
) -> Page[s.DepartmentOut]:
    items, total = reference.list_simple(
        db,
        principal,
        Department,
        q=q,
        order=[Department.code],
        search=[Department.code, Department.name],
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.DepartmentOut.model_validate(i) for i in items], total, paging)


register_crud(
    departments_router,
    reference.DEPARTMENTS,
    create_schema=s.DepartmentIn,
    patch_schema=s.DepartmentPatch,
    out_schema=s.DepartmentOut,
)

# ── campuses ───────────────────────────────────────────────────────────

campuses_router = APIRouter(prefix="/campuses", tags=["organisation"])


@campuses_router.get("", response_model=Page[s.CampusOut])
def list_campuses(
    db: DbSession, principal: PrincipalDep, paging: PageDep, q: Search = None
) -> Page[s.CampusOut]:
    items, total = reference.list_simple(
        db,
        principal,
        Campus,
        q=q,
        order=[Campus.code],
        search=[Campus.code, Campus.name],
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.CampusOut.model_validate(i) for i in items], total, paging)


@campuses_router.get("/travel-times", response_model=list[s.TravelTimeOut])
def get_travel_times(db: DbSession, principal: PrincipalDep) -> list[s.TravelTimeOut]:
    return [s.TravelTimeOut.model_validate(t) for t in reference.travel_times(db, principal)]


@campuses_router.put("/travel-times", response_model=list[s.TravelTimeOut])
def set_travel_times(
    body: list[s.TravelTimeIn], db: DbSession, principal: PrincipalDep
) -> list[s.TravelTimeOut]:
    rows = reference.set_travel_times(
        db, principal, [(t.campus_a_id, t.campus_b_id, t.minutes) for t in body]
    )
    db.commit()
    return [s.TravelTimeOut.model_validate(t) for t in rows]


register_crud(
    campuses_router,
    reference.CAMPUSES,
    create_schema=s.CampusIn,
    patch_schema=s.CampusPatch,
    out_schema=s.CampusOut,
)

# ── buildings ──────────────────────────────────────────────────────────

buildings_router = APIRouter(prefix="/buildings", tags=["organisation"])


@buildings_router.get("", response_model=Page[s.BuildingOut])
def list_buildings(
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    q: Search = None,
    campus_id: uuid.UUID | None = None,
) -> Page[s.BuildingOut]:
    items, total = reference.list_simple(
        db,
        principal,
        Building,
        q=q,
        order=[Building.code],
        search=[Building.code, Building.name],
        filters=[Building.campus_id == campus_id] if campus_id else [],
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.BuildingOut.model_validate(i) for i in items], total, paging)


register_crud(
    buildings_router,
    reference.BUILDINGS,
    create_schema=s.BuildingIn,
    patch_schema=s.BuildingPatch,
    out_schema=s.BuildingOut,
)

# ── room types and features ────────────────────────────────────────────

room_types_router = APIRouter(prefix="/room-types", tags=["organisation"])


@room_types_router.get("", response_model=Page[s.RoomTypeOut])
def list_room_types(
    db: DbSession, principal: PrincipalDep, paging: PageDep, q: Search = None
) -> Page[s.RoomTypeOut]:
    items, total = reference.list_simple(
        db,
        principal,
        RoomType,
        q=q,
        order=[RoomType.code],
        search=[RoomType.code, RoomType.name],
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.RoomTypeOut.model_validate(i) for i in items], total, paging)


register_crud(
    room_types_router,
    reference.ROOM_TYPES,
    create_schema=s.RoomTypeIn,
    patch_schema=s.RoomTypePatch,
    out_schema=s.RoomTypeOut,
)

room_features_router = APIRouter(prefix="/room-features", tags=["organisation"])


@room_features_router.get("", response_model=Page[s.RoomFeatureOut])
def list_room_features(
    db: DbSession, principal: PrincipalDep, paging: PageDep, q: Search = None
) -> Page[s.RoomFeatureOut]:
    items, total = reference.list_simple(
        db,
        principal,
        RoomFeature,
        q=q,
        order=[RoomFeature.code],
        search=[RoomFeature.code, RoomFeature.name],
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.RoomFeatureOut.model_validate(i) for i in items], total, paging)


register_crud(
    room_features_router,
    reference.ROOM_FEATURES,
    create_schema=s.RoomFeatureIn,
    patch_schema=s.RoomFeaturePatch,
    out_schema=s.RoomFeatureOut,
)

# ── rooms ──────────────────────────────────────────────────────────────

rooms_router = APIRouter(prefix="/rooms", tags=["organisation"])


@rooms_router.get("", response_model=Page[s.RoomOut])
def list_rooms(
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    q: Search = None,
    campus_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    room_type_id: uuid.UUID | None = None,
    min_capacity: Annotated[int | None, Query(ge=1)] = None,
    active: bool | None = None,
) -> Page[s.RoomOut]:
    items, total = reference.list_rooms(
        db,
        principal,
        q=q,
        campus_id=campus_id,
        building_id=building_id,
        room_type_id=room_type_id,
        min_capacity=min_capacity,
        active=active,
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.RoomOut.model_validate(i) for i in items], total, paging)


register_crud(
    rooms_router,
    reference.ROOMS,
    create_schema=s.RoomIn,
    patch_schema=s.RoomPatch,
    out_schema=s.RoomOut,
)

# ── programmes, courses, activity types ────────────────────────────────

programmes_router = APIRouter(prefix="/programmes", tags=["catalogue"])


@programmes_router.get("", response_model=Page[s.ProgrammeOut])
def list_programmes(
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    q: Search = None,
    department_id: uuid.UUID | None = None,
) -> Page[s.ProgrammeOut]:
    items, total = reference.list_simple(
        db,
        principal,
        Programme,
        q=q,
        order=[Programme.code],
        search=[Programme.code, Programme.name],
        filters=[Programme.department_id == department_id] if department_id else [],
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.ProgrammeOut.model_validate(i) for i in items], total, paging)


register_crud(
    programmes_router,
    reference.PROGRAMMES,
    create_schema=s.ProgrammeIn,
    patch_schema=s.ProgrammePatch,
    out_schema=s.ProgrammeOut,
)

courses_router = APIRouter(prefix="/courses", tags=["catalogue"])


@courses_router.get("", response_model=Page[s.CourseOut])
def list_courses(
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    q: Search = None,
    department_id: uuid.UUID | None = None,
    active: bool | None = None,
) -> Page[s.CourseOut]:
    items, total = reference.list_courses(
        db,
        principal,
        q=q,
        department_id=department_id,
        active=active,
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.CourseOut.model_validate(i) for i in items], total, paging)


register_crud(
    courses_router,
    reference.COURSES,
    create_schema=s.CourseIn,
    patch_schema=s.CoursePatch,
    out_schema=s.CourseOut,
)

activity_types_router = APIRouter(prefix="/activity-types", tags=["catalogue"])


@activity_types_router.get("", response_model=Page[s.ActivityTypeOut])
def list_activity_types(
    db: DbSession, principal: PrincipalDep, paging: PageDep, q: Search = None
) -> Page[s.ActivityTypeOut]:
    items, total = reference.list_simple(
        db,
        principal,
        ActivityType,
        q=q,
        order=[ActivityType.position, ActivityType.code],
        search=[ActivityType.code, ActivityType.name],
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.ActivityTypeOut.model_validate(i) for i in items], total, paging)


register_crud(
    activity_types_router,
    reference.ACTIVITY_TYPES,
    create_schema=s.ActivityTypeIn,
    patch_schema=s.ActivityTypePatch,
    out_schema=s.ActivityTypeOut,
)

# ── instructors ────────────────────────────────────────────────────────

instructors_router = APIRouter(prefix="/instructors", tags=["staff"])


@instructors_router.get("", response_model=Page[s.InstructorOut])
def list_instructors(
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    q: Search = None,
    department_id: uuid.UUID | None = None,
    active: bool | None = None,
) -> Page[s.InstructorOut]:
    items, total = reference.list_instructors(
        db,
        principal,
        q=q,
        department_id=department_id,
        active=active,
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.InstructorOut.model_validate(i) for i in items], total, paging)


register_crud(
    instructors_router,
    reference.INSTRUCTORS,
    create_schema=s.InstructorIn,
    patch_schema=s.InstructorPatch,
    out_schema=s.InstructorOut,
)

# ── calendar events ────────────────────────────────────────────────────

calendar_router = APIRouter(prefix="/calendar-events", tags=["calendar"])


@calendar_router.get("", response_model=Page[s.CalendarEventOut])
def list_calendar_events(
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    q: Search = None,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
) -> Page[s.CalendarEventOut]:
    filters = []
    if year:
        from datetime import date

        filters.append(CalendarEvent.end_date >= date(year, 1, 1))
        filters.append(CalendarEvent.start_date <= date(year, 12, 31))
    items, total = reference.list_simple(
        db,
        principal,
        CalendarEvent,
        q=q,
        order=[CalendarEvent.start_date],
        search=[CalendarEvent.label],
        filters=filters,
        offset=paging.offset,
        limit=paging.page_size,
    )
    return _page([s.CalendarEventOut.model_validate(i) for i in items], total, paging)


register_crud(
    calendar_router,
    reference.CALENDAR_EVENTS,
    create_schema=s.CalendarEventIn,
    patch_schema=s.CalendarEventPatch,
    out_schema=s.CalendarEventOut,
)

routers = [
    institution_router,
    departments_router,
    campuses_router,
    buildings_router,
    room_types_router,
    room_features_router,
    rooms_router,
    programmes_router,
    courses_router,
    activity_types_router,
    instructors_router,
    calendar_router,
]
