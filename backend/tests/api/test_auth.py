from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.models import AuditEvent, UserSession
from tests import factories


def test_login_sets_http_only_cookie_and_returns_permissions(
    client: TestClient, db: Session
) -> None:
    factories.user(db, "amira.haddad", [("scheduling_officer", None)])
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "Amira.Haddad", "password": factories.PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "amira.haddad"
    assert body["permissions"]["scheduling.run"] is None  # institution-wide
    assert "users.manage" not in body["permissions"]
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "auth.login")) is not None


def test_wrong_password_and_unknown_user_are_indistinguishable(
    client: TestClient, db: Session
) -> None:
    factories.user(db, "amira.haddad")
    wrong = client.post(
        "/api/v1/auth/login", json={"username": "amira.haddad", "password": "wrong-password-1"}
    )
    unknown = client.post(
        "/api/v1/auth/login", json={"username": "nobody.here", "password": "wrong-password-1"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_repeated_failures_lock_the_account(client: TestClient, db: Session) -> None:
    factories.user(db, "amira.haddad")
    for _ in range(5):
        client.post(
            "/api/v1/auth/login", json={"username": "amira.haddad", "password": "wrong-password-1"}
        )
    locked = client.post(
        "/api/v1/auth/login", json={"username": "amira.haddad", "password": factories.PASSWORD}
    )
    assert locked.status_code == 429
    assert int(locked.headers["retry-after"]) > 0


def test_protected_endpoint_requires_session(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_state_change_requires_csrf_token(client: TestClient, db: Session) -> None:
    factories.user(db, "amira.haddad")
    factories.login(client, "amira.haddad")
    token = client.headers.pop("X-CSRF-Token")
    rejected = client.post("/api/v1/auth/logout")
    assert rejected.status_code == 403
    client.headers["X-CSRF-Token"] = token
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_idle_session_expires(client: TestClient, db: Session) -> None:
    account = factories.user(db, "amira.haddad")
    factories.login(client, "amira.haddad")
    session = db.scalar(select(UserSession).where(UserSession.user_id == account.id))
    assert session is not None
    session.last_seen_at = datetime.now(UTC) - timedelta(hours=3)
    db.flush()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_password_change_enforces_policy_and_revokes_other_sessions(
    client: TestClient, db: Session, app: FastAPI
) -> None:
    factories.user(db, "amira.haddad")
    other = TestClient(app)
    factories.login(other, "amira.haddad")
    factories.login(client, "amira.haddad")

    weak = client.post(
        "/api/v1/auth/password",
        json={"current_password": factories.PASSWORD, "new_password": "short"},
    )
    assert weak.status_code == 422
    assert weak.json()["errors"][0]["field"] == "new_password"

    ok = client.post(
        "/api/v1/auth/password",
        json={"current_password": factories.PASSWORD, "new_password": "a-much-better-passphrase"},
    )
    assert ok.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 200
    assert other.get("/api/v1/auth/me").status_code == 401


def test_must_change_password_blocks_other_endpoints(client: TestClient, db: Session) -> None:
    factories.user(db, "new.user", [("system_admin", None)], must_change_password=True)
    factories.login(client, "new.user")
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.get("/api/v1/users").status_code == 403
