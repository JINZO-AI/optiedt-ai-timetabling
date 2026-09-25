from __future__ import annotations

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.models import AuditEvent
from tests import factories

API = "/api/v1"


def _as(client: TestClient, db: Session, role: str, department_id: uuid.UUID | None = None) -> None:
    factories.user(db, f"{role.replace('_', '.')}.user", [(role, department_id)])
    factories.login(client, f"{role.replace('_', '.')}.user")


def _create(client: TestClient, path: str, body: dict[str, object]) -> dict[str, Any]:
    response = client.post(f"{API}/{path}", json=body)
    assert response.status_code == 201, response.text
    result: dict[str, object] = response.json()
    return result


def _campus_building_type(client: TestClient) -> tuple[str, str, str]:
    campus = _create(client, "campuses", {"code": "MAIN", "name": "Main campus"})
    building = _create(
        client, "buildings", {"campus_id": campus["id"], "code": "B", "name": "Building B"}
    )
    room_type = _create(client, "room-types", {"code": "CLASSROOM", "name": "Classroom"})
    return str(campus["id"]), str(building["id"]), str(room_type["id"])


def test_room_lifecycle_with_features(client: TestClient, db: Session) -> None:
    _as(client, db, "institution_admin")
    _, building_id, type_id = _campus_building_type(client)
    projector = _create(client, "room-features", {"code": "PROJECTOR", "name": "Projector"})
    room = _create(
        client,
        "rooms",
        {
            "building_id": building_id,
            "code": "B-204",
            "name": "Seminar room",
            "room_type_id": type_id,
            "capacity": 36,
            "feature_ids": [projector["id"]],
        },
    )
    assert [f["code"] for f in room["features"]] == ["PROJECTOR"]

    patched = client.patch(
        f"{API}/rooms/{room['id']}", json={"version": room["version"], "feature_ids": []}
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["features"] == []
    assert patched.json()["version"] == room["version"] + 1

    listed = client.get(f"{API}/rooms", params={"min_capacity": 30, "q": "B-2"}).json()
    assert listed["total"] == 1

    actions = db.scalars(
        select(AuditEvent.action).where(AuditEvent.entity_id == str(room["id"]))
    ).all()
    assert actions == ["room.create", "room.update"]


def test_duplicate_room_code_in_same_building(client: TestClient, db: Session) -> None:
    _as(client, db, "institution_admin")
    _, building_id, type_id = _campus_building_type(client)
    body = {"building_id": building_id, "code": "A1", "room_type_id": type_id, "capacity": 20}
    _create(client, "rooms", body)
    duplicate = client.post(f"{API}/rooms", json=body)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate"
    assert "already exists in the building" in duplicate.json()["detail"]


def test_unknown_reference_is_a_field_error(client: TestClient, db: Session) -> None:
    _as(client, db, "institution_admin")
    _, building_id, _ = _campus_building_type(client)
    response = client.post(
        f"{API}/rooms",
        json={
            "building_id": building_id,
            "code": "X",
            "room_type_id": "00000000-0000-0000-0000-000000000001",
            "capacity": 10,
        },
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "room_type_id"


def test_room_type_in_use_cannot_be_deleted(client: TestClient, db: Session) -> None:
    _as(client, db, "institution_admin")
    _, building_id, type_id = _campus_building_type(client)
    _create(
        client,
        "rooms",
        {"building_id": building_id, "code": "L1", "room_type_id": type_id, "capacity": 20},
    )
    response = client.delete(f"{API}/room-types/{type_id}")
    assert response.status_code == 409
    assert response.json()["code"] == "in_use"
    assert "rooms" in response.json()["detail"]


def test_department_cycle_is_rejected(client: TestClient, db: Session) -> None:
    _as(client, db, "institution_admin")
    faculty = _create(client, "departments", {"code": "FS", "name": "Faculty of Science"})
    dept = _create(
        client,
        "departments",
        {"code": "CS", "name": "Computer Science", "parent_id": faculty["id"]},
    )
    response = client.patch(
        f"{API}/departments/{faculty['id']}",
        json={"version": faculty["version"], "parent_id": dept["id"]},
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "parent_id"


def test_required_field_cannot_be_cleared(client: TestClient, db: Session) -> None:
    _as(client, db, "institution_admin")
    campus = _create(client, "campuses", {"code": "NORTH", "name": "North"})
    response = client.patch(
        f"{API}/campuses/{campus['id']}", json={"version": campus["version"], "name": None}
    )
    assert response.status_code == 422


def test_officer_scope_limits_instructor_management(client: TestClient, db: Session) -> None:
    faculty = factories.department(db, "FS", "Faculty of Science")
    cs = factories.department(db, "CS", "Computer Science", faculty)
    math = factories.department(db, "MATH", "Mathematics")
    _as(client, db, "scheduling_officer", faculty.id)

    allowed = client.post(
        f"{API}/instructors",
        json={
            "code": "T-1001",
            "first_name": "Leila",
            "last_name": "Mansouri",
            "department_id": str(cs.id),
        },
    )
    assert allowed.status_code == 201, allowed.text

    denied = client.post(
        f"{API}/instructors",
        json={
            "code": "T-1002",
            "first_name": "Karim",
            "last_name": "Gharbi",
            "department_id": str(math.id),
        },
    )
    assert denied.status_code == 403

    moved = client.patch(
        f"{API}/instructors/{allowed.json()['id']}",
        json={"version": allowed.json()["version"], "department_id": str(math.id)},
    )
    assert moved.status_code == 403


def test_viewer_reads_but_cannot_write(client: TestClient, db: Session) -> None:
    _as(client, db, "viewer")
    assert client.get(f"{API}/rooms").status_code == 200
    assert client.post(f"{API}/campuses", json={"code": "X", "name": "X"}).status_code == 403


def test_students_cannot_read_reference_lists(client: TestClient, db: Session) -> None:
    _as(client, db, "student")
    assert client.get(f"{API}/instructors").status_code == 403
    assert client.get(f"{API}/institution").status_code == 200


def test_travel_times_are_normalised_and_validated(client: TestClient, db: Session) -> None:
    _as(client, db, "institution_admin")
    a = _create(client, "campuses", {"code": "A", "name": "Campus A"})
    b = _create(client, "campuses", {"code": "B", "name": "Campus B"})
    saved = client.put(
        f"{API}/campuses/travel-times",
        json=[{"campus_a_id": b["id"], "campus_b_id": a["id"], "minutes": 25}],
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()[0]["minutes"] == 25
    duplicate = client.put(
        f"{API}/campuses/travel-times",
        json=[
            {"campus_a_id": a["id"], "campus_b_id": b["id"], "minutes": 25},
            {"campus_a_id": b["id"], "campus_b_id": a["id"], "minutes": 30},
        ],
    )
    assert duplicate.status_code == 422


def test_institution_settings(client: TestClient, db: Session) -> None:
    _as(client, db, "institution_admin")
    current = client.get(f"{API}/institution").json()
    bad_zone = client.patch(
        f"{API}/institution", json={"version": current["version"], "timezone": "Mars/Base"}
    )
    assert bad_zone.status_code == 422
    bad_locale = client.patch(
        f"{API}/institution",
        json={"version": current["version"], "enabled_locales": ["en"], "default_locale": "fr"},
    )
    assert bad_locale.status_code == 422
    ok = client.patch(
        f"{API}/institution",
        json={
            "version": current["version"],
            "name": "Université de Carthage — Faculté des Sciences",
            "short_name": "FSC",
            "timezone": "Africa/Tunis",
            "week_start": 0,
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["timezone"] == "Africa/Tunis"


def test_calendar_event_dates_must_be_ordered(client: TestClient, db: Session) -> None:
    _as(client, db, "institution_admin")
    response = client.post(
        f"{API}/calendar-events",
        json={"start_date": "2026-03-20", "end_date": "2026-03-19", "label": "Eid al-Fitr"},
    )
    assert response.status_code == 422
