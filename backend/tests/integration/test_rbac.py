"""FR-11 — authentication and rights, against REAL tokens.

⚠️ **Nothing here overrides `current_user`.** Every other API test does, so
that a test about the wire format or about FR-2's rules is not also a test
about signing in. This module is the one that must not: it signs in through
`POST /api/auth/token`, carries the bearer token it gets back, and lets the
real dependency decode it. Overriding the dependency here would test the
override.

The rights are `docs/domain-model.md`'s table, which SRS Table 2 governs (C-8).
The acceptance criterion this milestone serves is: **a teacher account obtains
only its own availability and timetable.**
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from optiedt.api import deps
from optiedt.api.main import app
from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole
from optiedt.services.users import InMemoryUserStore

PASSWORD = "a-password-nobody-guesses"
OTHER_TEACHER = "T002"


@pytest.fixture(scope="module")
def users() -> InMemoryUserStore:
    """Five accounts, hashed ONCE for the module.

    bcrypt is deliberately slow - that is the point of it - so re-creating
    these per test cost about 25 seconds across this file for no extra
    confidence. Nothing here mutates the store except
    `test_a_token_for_a_deleted_account_stops_working`, which creates and
    removes an account of its own rather than borrowing one of these.
    """
    store = InMemoryUserStore()
    store.create(User(id="u1", username="chef", role=UserRole.PERSON_IN_CHARGE), PASSWORD)
    store.create(User(id="u2", username="prof1", role=UserRole.TEACHER, teacher="T001"), PASSWORD)
    store.create(
        User(id="u3", username="prof2", role=UserRole.TEACHER, teacher=OTHER_TEACHER), PASSWORD
    )
    store.create(User(id="u4", username="admin", role=UserRole.ADMINISTRATOR), PASSWORD)
    # A teacher account with NO teacher link - the case that must be refused
    # rather than defaulted.
    store.create(User(id="u5", username="orphan", role=UserRole.TEACHER), PASSWORD)
    return store


@pytest.fixture
def client(users: InMemoryUserStore) -> Iterator[TestClient]:
    for cached in (deps.get_settings, deps.get_instance, deps.get_availability_store):
        cached.cache_clear()
    app.dependency_overrides[deps.get_user_store] = lambda: users
    yield TestClient(app)
    app.dependency_overrides.clear()


def token_for(client: TestClient, username: str, password: str = PASSWORD) -> str | None:
    response = client.post("/api/auth/token", data={"username": username, "password": password})
    if response.status_code != 200:
        return None
    return str(response.json()["access_token"])


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── signing in ─────────────────────────────────────────────────────────


def test_a_correct_password_returns_a_bearer_token(client: TestClient) -> None:
    response = client.post("/api/auth/token", data={"username": "chef", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_a_wrong_password_and_an_unknown_user_are_indistinguishable(
    client: TestClient,
) -> None:
    """⚠️ Telling them apart tells an attacker which accounts exist."""
    wrong = client.post("/api/auth/token", data={"username": "chef", "password": "nope"})
    unknown = client.post("/api/auth/token", data={"username": "ghost", "password": PASSWORD})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_the_token_never_carries_a_credential(client: TestClient) -> None:
    """The payload is base64, not encryption. Anyone holding the token reads it."""
    import base64
    import json

    token = token_for(client, "prof1")
    assert token is not None
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))

    assert claims["sub"] == "prof1"
    assert claims["teacher"] == "T001"
    assert not any("pass" in key.lower() or "hash" in key.lower() for key in claims)


def test_me_reports_the_account_without_a_credential(client: TestClient) -> None:
    token = token_for(client, "prof1")
    assert token is not None
    body = client.get("/api/auth/me", headers=auth(token)).json()

    assert body == {"id": "u2", "username": "prof1", "role": "TEACHER", "teacher": "T001"}


# ── no token, bad token ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/instance"),
        ("get", "/api/runs"),
        ("get", "/api/teachers/T001/availability"),
        ("post", "/api/runs"),
        ("get", "/api/auth/me"),
    ],
)
def test_every_endpoint_refuses_an_anonymous_caller(
    client: TestClient, method: str, path: str
) -> None:
    assert getattr(client, method)(path).status_code == 401


def test_a_token_signed_with_another_key_is_refused(client: TestClient) -> None:
    """The signature is the whole guarantee; a forged token must not pass."""
    from optiedt.core.security import create_access_token

    forged = create_access_token("chef", "PERSON_IN_CHARGE", "not-the-secret", 60)
    assert client.get("/api/auth/me", headers=auth(forged)).status_code == 401


def test_a_token_for_a_deleted_account_stops_working(
    client: TestClient, users: InMemoryUserStore
) -> None:
    """⚠️ Why the user is re-read on every request instead of trusted from the
    claims: a token stays valid until it expires, so an account that is removed
    would otherwise keep its rights for the rest of that token's life.

    Creates its own account rather than removing a shared one, so the module's
    other tests cannot depend on the order this runs in.
    """
    users.create(User(id="tmp", username="temporary", role=UserRole.TEACHER), PASSWORD)
    token = token_for(client, "temporary")
    assert token is not None
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 200

    users._users.pop("temporary")
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401


def test_health_stays_open(client: TestClient) -> None:
    """A liveness probe cannot hold a credential."""
    assert client.get("/api/health").status_code == 200


# ── the acceptance criterion: a teacher sees only its own ──────────────


def test_a_teacher_reads_its_own_availability(client: TestClient) -> None:
    token = token_for(client, "prof1")
    assert token is not None
    assert client.get("/api/teachers/T001/availability", headers=auth(token)).status_code == 200


def test_a_teacher_is_refused_another_teachers_availability(client: TestClient) -> None:
    """**The acceptance criterion.** Which teacher the caller is comes from the
    TOKEN; until Phase 5 it came from the path, so any caller could name any
    teacher."""
    token = token_for(client, "prof1")
    assert token is not None
    response = client.get(f"/api/teachers/{OTHER_TEACHER}/availability", headers=auth(token))

    assert response.status_code == 403
    assert "own availability" in response.json()["detail"]


def test_a_teacher_cannot_write_another_teachers_grid(client: TestClient) -> None:
    """Reading someone else's week is a leak; writing it is worse."""
    token = token_for(client, "prof1")
    assert token is not None
    response = client.put(
        f"/api/teachers/{OTHER_TEACHER}/availability",
        headers=auth(token),
        json={"semester": 2, "cells": [{"slot": 3, "state": "UNAVAILABLE"}]},
    )
    assert response.status_code == 403


def test_a_teacher_account_with_no_teacher_link_is_refused_every_grid(
    client: TestClient,
) -> None:
    """⚠️ Refused rather than defaulted. An account that cannot say whose grid
    it owns has no business editing one, and picking a default would hand it
    somebody else's."""
    token = token_for(client, "orphan")
    assert token is not None
    assert client.get("/api/teachers/T001/availability", headers=auth(token)).status_code == 403


def test_the_person_in_charge_reaches_any_teachers_grid(client: TestClient) -> None:
    """SRS Table 2: read and write on ALL data."""
    token = token_for(client, "chef")
    assert token is not None
    assert client.get("/api/teachers/T001/availability", headers=auth(token)).status_code == 200
    assert (
        client.get(f"/api/teachers/{OTHER_TEACHER}/availability", headers=auth(token)).status_code
        == 200
    )


# ── who may launch a run ───────────────────────────────────────────────


def test_only_the_person_in_charge_may_launch_a_run(client: TestClient) -> None:
    """A run costs minutes of every core and the executor serialises them, so
    letting any account launch one would let any account monopolise the engine."""
    for username in ("prof1", "admin"):
        token = token_for(client, username)
        assert token is not None
        response = client.post("/api/runs", headers=auth(token), json={})
        assert response.status_code == 403, username
        assert "may not do this" in response.json()["detail"]


def test_a_teacher_may_still_read_runs_and_the_instance(client: TestClient) -> None:
    """Rights are per endpoint, not per screen: reading is not launching."""
    token = token_for(client, "prof1")
    assert token is not None
    assert client.get("/api/runs", headers=auth(token)).status_code == 200
    assert client.get("/api/instance", headers=auth(token)).status_code == 200
