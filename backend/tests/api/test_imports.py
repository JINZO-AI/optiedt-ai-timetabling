"""Staged imports over HTTP: parsing, mapping suggestions, validation reports, commits."""

from __future__ import annotations

import io
import uuid
from typing import Any

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.models import AuditEvent, Instructor, Room, StudentGroup
from tests import factories

API = "/api/v1"


def _officer(client: TestClient, db: Session) -> None:
    factories.user(db, "officer", [("scheduling_officer", None), ("institution_admin", None)])
    factories.login(client, "officer")


def _upload(
    client: TestClient,
    entity_type: str,
    name: str,
    content: bytes,
    term_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    data = {"entity_type": entity_type}
    if term_id is not None:
        data["term_id"] = str(term_id)
    response = client.post(f"{API}/imports", data=data, files={"file": (name, content)})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_rooms_from_a_french_semicolon_csv(client: TestClient, db: Session) -> None:
    factories.institution(db)
    _officer(client, db)
    content = (
        "Salle;Bâtiment;Type;Capacité;Équipements\n"
        "A-201;A;CLASSROOM;32;\n"
        "A-202;A;CLASSROOM;28\n"
        "Z-1;Z;CLASSROOM;20;\n"
    ).encode("cp1252")
    batch = _upload(client, "rooms", "salles.csv", content)
    assert batch["mapping"]["columns"] == {
        "code": 0,
        "building": 1,
        "room_type": 2,
        "capacity": 3,
        "features": 4,
    }
    assert batch["report"]["counts"] == {"create": 2, "update": 0, "unchanged": 0, "error": 1}
    problem = batch["report"]["rows"][-1]
    assert problem["row"] == 4
    assert problem["errors"] == [{"field": "building", "message": "Unknown building 'Z'."}]

    refused = client.post(f"{API}/imports/{batch['id']}/commit")
    assert refused.status_code == 409
    assert refused.json()["code"] == "import_has_errors"
    assert db.scalar(select(Room.id).where(Room.code == "A-201")) is None


def test_commit_creates_then_updates(client: TestClient, db: Session) -> None:
    factories.institution(db)
    _officer(client, db)
    first = _upload(
        client,
        "rooms",
        "rooms.csv",
        b"code,building,room_type,capacity,features\nA-201,A,CLASSROOM,32,\nA-202,A,LECTURE_HALL,90,\n",
    )
    committed = client.post(f"{API}/imports/{first['id']}/commit")
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "committed"
    assert db.scalars(select(Room.capacity).where(Room.code == "A-202")).one() == 90

    second = _upload(
        client,
        "rooms",
        "rooms.csv",
        b"code,building,room_type,capacity\nA-201,A,CLASSROOM,32\nA-202,A,LECTURE_HALL,120\n",
    )
    assert second["report"]["counts"]["update"] >= 1
    assert client.post(f"{API}/imports/{second['id']}/commit").status_code == 200
    db.expire_all()
    assert db.scalars(select(Room.capacity).where(Room.code == "A-202")).one() == 120
    summaries = db.scalars(
        select(AuditEvent.summary).where(AuditEvent.action == "import.commit")
    ).all()
    assert len(summaries) == 2


def test_instructors_from_xlsx_with_a_corrected_mapping(client: TestClient, db: Session) -> None:
    factories.institution(db)
    _officer(client, db)
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["Matricule", "Prénom", "Surname", "Dept", "Charge"])
    sheet.append(["T900", "Nour", "Ben Salah", "CS", 12])
    sheet.append(["T901", "Youssef", "Trabelsi", "MATH", 10.0])
    buffer = io.BytesIO()
    workbook.save(buffer)
    batch = _upload(client, "instructors", "staff.xlsx", buffer.getvalue())
    columns = batch["mapping"]["columns"]
    assert columns["code"] == 0
    assert columns["first_name"] == 1
    assert columns["last_name"] == 2
    assert "max_weekly_periods" not in columns
    columns["max_weekly_periods"] = 4
    mapped = client.put(f"{API}/imports/{batch['id']}/mapping", json={"columns": columns}).json()
    assert mapped["report"]["counts"]["create"] == 2
    assert client.post(f"{API}/imports/{batch['id']}/commit").status_code == 200
    teacher = db.scalars(select(Instructor).where(Instructor.code == "T901")).one()
    assert teacher.max_weekly_periods == 10


def test_groups_are_created_parents_first(client: TestClient, db: Session) -> None:
    inst = factories.institution(db)
    term = factories.term(db)
    _officer(client, db)
    content = (
        "code,name,size,parent,partition,programme\n"
        f"L1-G1,Group 1,30,L1,tutorial,{inst.programme.code}\n"
        f"L1-G2,Group 2,30,L1,tutorial,{inst.programme.code}\n"
        f"L1,First year,60,,,{inst.programme.code}\n"
    ).encode()
    batch = _upload(client, "groups", "groups.csv", content, term.id)
    assert batch["report"]["counts"]["create"] == 3
    assert client.post(f"{API}/imports/{batch['id']}/commit").status_code == 200
    groups = {
        g.code: g for g in db.scalars(select(StudentGroup).where(StudentGroup.term_id == term.id))
    }
    assert groups["L1-G1"].parent_id == groups["L1"].id
    assert groups["L1-G1"].partition_key == "tutorial"


def test_activities_report_unknown_references(client: TestClient, db: Session) -> None:
    _, term = factories.populated_term(db)
    _officer(client, db)
    content = (
        b"course,type,groups,instructors,duration,sessions_per_week\n"
        b"CS202,TUT,L2-CS-G2,T101,2,1\n"
        b"CS202,TUT,NOPE,T101,1,1\n"
    )
    batch = _upload(client, "activities", "activities.csv", content, term.id)
    assert batch["report"]["counts"] == {"create": 1, "update": 0, "unchanged": 0, "error": 1}
    assert batch["report"]["rows"][1]["errors"] == [
        {"field": "groups", "message": "Unknown group 'NOPE'."}
    ]


def test_templates_and_permissions(client: TestClient, db: Session) -> None:
    factories.user(db, "viewer.one", [("viewer", None)])
    factories.login(client, "viewer.one")
    assert (
        client.post(
            f"{API}/imports", data={"entity_type": "rooms"}, files={"file": ("r.csv", b"code\n")}
        ).status_code
        == 403
    )
    _officer(client, db)
    template = client.get(f"{API}/imports/templates/rooms.csv")
    assert template.status_code == 200
    assert template.text.lstrip("﻿").startswith("Code,Name,Building")
    specs = client.get(f"{API}/imports/specs").json()
    assert {s["code"] for s in specs} == {"rooms", "instructors", "courses", "groups", "activities"}
    unknown = client.post(
        f"{API}/imports", data={"entity_type": "rooms"}, files={"file": ("r.pdf", b"%PDF")}
    )
    assert unknown.status_code == 422
