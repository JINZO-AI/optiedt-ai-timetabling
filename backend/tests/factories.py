"""Builders for test records. Every value is realistic and explicit at the call site."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from optiedt.models import (
    ActivityType,
    Building,
    Campus,
    Course,
    Department,
    Instructor,
    Programme,
    RoleAssignment,
    Room,
    RoomType,
    Term,
    User,
)
from optiedt.security import passwords
from optiedt.security.permissions import Principal
from optiedt.services import terms as terms_service
from optiedt.services.auth import build_principal

PASSWORD = "correct-horse-battery"


def department(db: Session, code: str, name: str, parent: Department | None = None) -> Department:
    dept = Department(code=code, name=name, parent_id=parent.id if parent else None)
    db.add(dept)
    db.flush()
    return dept


def user(
    db: Session,
    username: str,
    roles: Sequence[tuple[str, uuid.UUID | None]] = (),
    *,
    password: str = PASSWORD,
    must_change_password: bool = False,
    instructor_id: uuid.UUID | None = None,
) -> User:
    account = User(
        username=username,
        display_name=username.replace(".", " ").title(),
        email=f"{username}@example.edu",
        password_hash=passwords.hash_password(password),
        must_change_password=must_change_password,
        instructor_id=instructor_id,
    )
    account.roles = [RoleAssignment(role=r, department_id=d) for r, d in roles]
    db.add(account)
    db.flush()
    return account


def login(client: TestClient, username: str, password: str = PASSWORD) -> dict[str, object]:
    """Sign in and make the client send the CSRF token on every later request."""
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    client.headers["X-CSRF-Token"] = str(body["csrf_token"])
    return body


# ── a small institution for term-data and scheduling tests ─────────────

TEACHING_PERIODS = (
    ("P1", time(8, 30), time(10, 0), True),
    ("P2", time(10, 10), time(11, 40), False),
    ("P3", time(13, 0), time(14, 30), True),
    ("P4", time(14, 40), time(16, 10), False),
)


@dataclass
class Institution:
    cs: Department
    math: Department
    campus: Campus
    building: Building
    lecture_hall: RoomType
    classroom: RoomType
    lab: RoomType
    lecture: ActivityType
    tutorial: ActivityType
    practical: ActivityType
    programme: Programme
    rooms: dict[str, Room] = field(default_factory=dict)
    instructors: dict[str, Instructor] = field(default_factory=dict)
    courses: dict[str, Course] = field(default_factory=dict)


def institution(db: Session) -> Institution:
    cs = department(db, "CS", "Computer Science")
    math = department(db, "MATH", "Mathematics")
    campus = Campus(code="MAIN", name="Main campus")
    db.add(campus)
    db.flush()
    building = Building(campus_id=campus.id, code="A", name="Building A")
    lecture_hall = RoomType(code="LECTURE_HALL", name="Lecture hall")
    classroom = RoomType(code="CLASSROOM", name="Classroom")
    lab = RoomType(code="COMPUTER_LAB", name="Computer lab")
    db.add_all([building, lecture_hall, classroom, lab])
    db.flush()
    lecture = ActivityType(code="LEC", name="Lecture", default_room_type_id=lecture_hall.id)
    tutorial = ActivityType(code="TUT", name="Tutorial", default_room_type_id=classroom.id)
    practical = ActivityType(code="LAB", name="Lab", default_room_type_id=lab.id)
    programme = Programme(code="BSC-CS", name="BSc Computer Science", department_id=cs.id)
    db.add_all([lecture, tutorial, practical, programme])
    result = Institution(
        cs,
        math,
        campus,
        building,
        lecture_hall,
        classroom,
        lab,
        lecture=lecture,
        tutorial=tutorial,
        practical=practical,
        programme=programme,
    )
    for code, capacity, room_type in (
        ("A-AMPHI", 180, lecture_hall),
        ("A-101", 40, classroom),
        ("A-102", 40, classroom),
        ("A-LAB1", 24, lab),
    ):
        room = Room(
            building_id=building.id, code=code, room_type_id=room_type.id, capacity=capacity
        )
        db.add(room)
        result.rooms[code] = room
    for code, first, last, dept in (
        ("T100", "Leila", "Mansouri", cs),
        ("T101", "Karim", "Gharbi", cs),
        ("T200", "Sonia", "Trabelsi", math),
    ):
        instructor = Instructor(code=code, first_name=first, last_name=last, department_id=dept.id)
        db.add(instructor)
        result.instructors[code] = instructor
    for code, title, dept in (
        ("CS201", "Algorithms", cs),
        ("CS202", "Databases", cs),
        ("MA201", "Linear Algebra", math),
    ):
        course = Course(code=code, title=title, department_id=dept.id)
        db.add(course)
        result.courses[code] = course
    db.flush()
    return result


def admin_principal(db: Session) -> Principal:
    account = user(db, f"system.{uuid.uuid4().hex[:8]}", [("system_admin", None)])
    return build_principal(db, account)


def term(
    db: Session,
    code: str = "2026-S1",
    weekdays: Sequence[int] = (0, 1, 2, 3, 4),
    open_until: date | None = None,
) -> Term:
    return terms_service.create_term(
        db,
        admin_principal(db),
        code=code,
        name=f"Semester {code}",
        academic_year="2026-2027",
        start_date=date(2026, 9, 14),
        end_date=date(2027, 1, 22),
        weekdays=list(weekdays),
        periods=[terms_service.PeriodSpec(*p) for p in TEACHING_PERIODS],
        availability_open_until=open_until,
    )
