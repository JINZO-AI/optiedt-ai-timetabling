from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from optiedt.models import AuditEvent
from tests import factories


def _admin(client: TestClient, db: Session, role: str = "institution_admin") -> None:
    factories.user(db, "registrar", [(role, None)])
    factories.login(client, "registrar")


def test_institution_admin_creates_scoped_officer(client: TestClient, db: Session) -> None:
    _admin(client, db)
    cs = factories.department(db, "CS", "Computer Science")
    response = client.post(
        "/api/v1/users",
        json={
            "username": "yassine.trabelsi",
            "display_name": "Yassine Trabelsi",
            "email": "y.trabelsi@example.edu",
            "roles": [{"role": "scheduling_officer", "department_id": str(cs.id)}],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["must_change_password"] is True
    assert len(body["temporary_password"]) >= 12
    assert body["roles"] == [{"role": "scheduling_officer", "department_id": str(cs.id)}]
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "user.create"))
    assert event is not None
    assert event.actor_label.startswith("Registrar")


def test_institution_admin_cannot_grant_system_admin(client: TestClient, db: Session) -> None:
    _admin(client, db)
    response = client.post(
        "/api/v1/users",
        json={
            "username": "sneaky",
            "display_name": "Sneaky",
            "roles": [{"role": "system_admin"}],
        },
    )
    assert response.status_code == 403


def test_admin_roles_cannot_be_department_scoped(client: TestClient, db: Session) -> None:
    _admin(client, db, "system_admin")
    cs = factories.department(db, "CS", "Computer Science")
    response = client.post(
        "/api/v1/users",
        json={
            "username": "scoped.admin",
            "display_name": "Scoped",
            "roles": [{"role": "institution_admin", "department_id": str(cs.id)}],
        },
    )
    assert response.status_code == 422


def test_officer_cannot_manage_users(client: TestClient, db: Session) -> None:
    factories.user(db, "officer", [("scheduling_officer", None)])
    factories.login(client, "officer")
    assert client.get("/api/v1/users").status_code == 403


def test_update_rejects_stale_version(client: TestClient, db: Session) -> None:
    _admin(client, db)
    target = factories.user(db, "target.user")
    loaded_version = target.version
    first = client.patch(
        f"/api/v1/users/{target.id}", json={"version": loaded_version, "display_name": "A"}
    )
    assert first.status_code == 200
    assert first.json()["version"] == loaded_version + 1
    stale = client.patch(
        f"/api/v1/users/{target.id}", json={"version": loaded_version, "display_name": "B"}
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_version"


def test_last_system_admin_is_protected(client: TestClient, db: Session) -> None:
    _admin(client, db, "system_admin")
    me = client.get("/api/v1/auth/me").json()
    response = client.put(f"/api/v1/users/{me['id']}/roles", json=[])
    assert response.status_code == 409


def test_deactivation_ends_sessions(client: TestClient, db: Session, app) -> None:  # type: ignore[no-untyped-def]
    _admin(client, db)
    target = factories.user(db, "leaving.user", [("viewer", None)])
    other = TestClient(app)
    factories.login(other, "leaving.user")
    response = client.patch(
        f"/api/v1/users/{target.id}", json={"version": target.version, "is_active": False}
    )
    assert response.status_code == 200
    assert other.get("/api/v1/auth/me").status_code == 401


def test_password_reset_returns_temporary_password(client: TestClient, db: Session) -> None:
    _admin(client, db)
    target = factories.user(db, "forgetful.user")
    response = client.post(f"/api/v1/users/{target.id}/reset-password")
    assert response.status_code == 200
    temporary = response.json()["temporary_password"]
    other_client = client.__class__(client.app)
    signed_in = factories.login(other_client, "forgetful.user", temporary)
    assert signed_in["must_change_password"] is True


def test_audit_events_are_append_only(db: Session) -> None:
    db.add(AuditEvent(actor_label="test", action="x", entity_type="t", entity_id="1", summary="s"))
    db.flush()
    with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
        db.execute(text("UPDATE audit_events SET summary = 'changed'"))


def test_audit_listing_is_scoped_by_department(client: TestClient, db: Session) -> None:
    cs = factories.department(db, "CS", "Computer Science")
    math = factories.department(db, "MATH", "Mathematics")
    db.add_all(
        [
            AuditEvent(
                actor_label="t",
                action="room.update",
                entity_type="room",
                entity_id="1",
                summary="cs change",
                department_ids=[cs.id],
            ),
            AuditEvent(
                actor_label="t",
                action="room.update",
                entity_type="room",
                entity_id="2",
                summary="math change",
                department_ids=[math.id],
            ),
        ]
    )
    factories.user(db, "cs.head", [("department_head", cs.id)])
    factories.login(client, "cs.head")
    response = client.get("/api/v1/audit-events", params={"action": "room."})
    assert response.status_code == 200
    summaries = [e["summary"] for e in response.json()["items"]]
    assert summaries == ["cs change"]
