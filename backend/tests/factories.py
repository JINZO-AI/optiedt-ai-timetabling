"""Builders for test records. Every value is realistic and explicit at the call site."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from optiedt.models import Department, RoleAssignment, User
from optiedt.security import passwords

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
