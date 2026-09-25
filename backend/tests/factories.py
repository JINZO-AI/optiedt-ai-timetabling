"""Builders for test records. Every value is realistic and explicit at the call site."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, time

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.models import (
    ActivityType,
    Building,
    Campus,
    Course,
    Department,
    Instructor,
    Period,
    Programme,
    RoleAssignment,
    Room,
    RoomType,
    Solution,
    Term,
    User,
)
from optiedt.security import passwords
from optiedt.security.permissions import Principal
from optiedt.services import activities as activity_service
from optiedt.services import availability as availability_service
from optiedt.services import groups as group_service
from optiedt.services import rules as rule_service
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


def populated_term(db: Session) -> tuple[Institution, Term]:
    """A term with a cohort and two tutorial groups, a lecture twice a week and a double
    tutorial, one instructor's availability and one soft rule: small but schedulable."""
    inst = institution(db)
    new_term = term(db)
    admin = admin_principal(db)
    cohort = group_service.create_group(
        db,
        admin,
        new_term.id,
        {"code": "L2-CS", "name": "L2 CS", "size": 60, "programme_id": inst.programme.id},
    )
    g1 = group_service.create_group(
        db,
        admin,
        new_term.id,
        {
            "code": "L2-CS-G1",
            "name": "G1",
            "size": 30,
            "parent_id": cohort.id,
            "partition_key": "tut",
        },
    )
    group_service.create_group(
        db,
        admin,
        new_term.id,
        {
            "code": "L2-CS-G2",
            "name": "G2",
            "size": 30,
            "parent_id": cohort.id,
            "partition_key": "tut",
        },
    )
    activity_service.create_activity(
        db,
        admin,
        new_term.id,
        {
            "course_id": inst.courses["CS201"].id,
            "activity_type_id": inst.lecture.id,
            "group_ids": [cohort.id],
            "instructor_ids": [inst.instructors["T100"].id],
            "sessions_per_week": 2,
        },
    )
    activity_service.create_activity(
        db,
        admin,
        new_term.id,
        {
            "course_id": inst.courses["CS201"].id,
            "activity_type_id": inst.tutorial.id,
            "group_ids": [g1.id],
            "instructor_ids": [inst.instructors["T101"].id],
            "duration": 2,
        },
    )
    periods = list(
        db.scalars(select(Period).where(Period.term_id == new_term.id).order_by(Period.position))
    )
    availability_service.put_grid(
        db,
        admin,
        new_term.id,
        "instructor",
        inst.instructors["T100"].id,
        version=None,
        cells=[
            availability_service.Cell(0, periods[0].id, "unavailable"),
            availability_service.Cell(1, periods[3].id, "undesirable"),
        ],
        today=new_term.start_date,
    )
    rule_service.create_rule(
        db,
        admin,
        new_term.id,
        {
            "rule_type": "break_in_window",
            "enforcement": "soft",
            "tier": 2,
            "params": {"period_ids": [str(periods[1].id), str(periods[2].id)], "min_free": 1},
            "scope": {"department_ids": [str(inst.cs.id)]},
        },
    )
    return inst, new_term


def solved_draft(db: Session, term_id: uuid.UUID, seconds: float = 3.0) -> Solution:
    """A draft timetable of the term's current data, solved in process (no worker)."""
    from optiedt.problem.encoding import Codec
    from optiedt.problem.model import build_problem
    from optiedt.problem.solution import ObjectiveConfig
    from optiedt.services.snapshots import compile_snapshot, store_snapshot
    from optiedt.services.solutions import create_solution
    from optiedt.solver.domains import build_context
    from optiedt.solver.engine import Engine, ProfileSpec, SolveSettings

    snapshot = compile_snapshot(db, term_id)
    stored = store_snapshot(db, term_id, snapshot)
    problem = build_problem(snapshot)
    profile = next(p for p in snapshot.profiles if p.code == "balanced")
    config = ObjectiveConfig.from_profile(profile)
    result = Engine(
        build_context(problem),
        [ProfileSpec("balanced", "Balanced", config)],
        SolveSettings(mode="reproducible", time_limit_seconds=seconds, workers=2, seed=1),
    ).run()
    placements = Codec(problem).encode(result.profiles[0].placements)
    return create_solution(
        db,
        term_id=term_id,
        snapshot_id=stored.id,
        name="Draft",
        origin="solver",
        objective_config={"objectives": {k: list(v) for k, v in config.objectives.items()}},
        placements=placements,
        profile_code="balanced",
    )


def term_periods(db: Session, term_id: uuid.UUID) -> list[Period]:
    return list(
        db.scalars(select(Period).where(Period.term_id == term_id).order_by(Period.position))
    )


def room_id(db: Session, code: str) -> uuid.UUID:
    return db.scalars(select(Room.id).where(Room.code == code)).one()
