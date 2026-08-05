"""FR-11 — authenticate users and restrict access by role.

    Acceptance criterion (docs/testing-strategy.md §4):
    "Connect with a teacher account → access limited to own data."

    And the criterion in docs/status.md:
    "A teacher account obtains only its own availability and timetable."

⚠️ **Real tokens, and no dependency override.** Every other suite overrides
`current_user` so that a test about the wire format is not also a test about
signing in. This one must not: overriding the dependency would test the
override. That is the same reason `tests/integration/test_rbac.py` exists and
is written the way it is - this file is the acceptance statement of it, taking
the path a person takes, sign-in included.
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

pytestmark = pytest.mark.acceptance

PASSWORD = "acceptance-password"


@pytest.fixture(scope="module")
def users() -> InMemoryUserStore:
    """One teacher and one person in charge, hashed ONCE for the module.

    bcrypt is deliberately slow - that is the point of it - so re-creating
    these per test would cost seconds for no extra confidence.

    Created directly rather than through the seed command: the seed refuses an
    installation that already has accounts (C-18), so it cannot be the way a
    suite provisions its own.
    """
    store = InMemoryUserStore()
    store.create(User(id="u1", username="t001", role=UserRole.TEACHER, teacher="T001"), PASSWORD)
    store.create(User(id="u2", username="responsable", role=UserRole.PERSON_IN_CHARGE), PASSWORD)
    return store


@pytest.fixture
def accounts(users: InMemoryUserStore) -> Iterator[TestClient]:
    for cached in (deps.get_settings, deps.get_instance, deps.get_availability_store):
        cached.cache_clear()
    app.dependency_overrides[deps.get_user_store] = lambda: users
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _token(client: TestClient, username: str) -> str:
    response = client.post("/api/auth/token", data={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_a_teacher_reads_its_own_availability(accounts: TestClient) -> None:
    token = _token(accounts, "t001")

    response = accounts.get("/api/teachers/T001/availability", headers=_auth(token))

    assert response.status_code == 200


def test_a_teacher_is_refused_another_teachers_availability(accounts: TestClient) -> None:
    """The criterion's whole content. 403, not an empty list: a teacher must
    not be left thinking another teacher has declared nothing."""
    token = _token(accounts, "t001")

    response = accounts.get("/api/teachers/T002/availability", headers=_auth(token))

    assert response.status_code == 403


def test_a_teacher_may_not_launch_a_run(accounts: TestClient) -> None:
    """Generation is the person in charge's right (SRS Table 2)."""
    token = _token(accounts, "t001")

    response = accounts.post("/api/runs", json={}, headers=_auth(token))

    assert response.status_code == 403


def test_the_person_in_charge_reads_any_teachers_availability(accounts: TestClient) -> None:
    token = _token(accounts, "responsable")

    for teacher in ("T001", "T002"):
        assert (
            accounts.get(f"/api/teachers/{teacher}/availability", headers=_auth(token)).status_code
            == 200
        )


def test_an_anonymous_caller_is_refused(accounts: TestClient) -> None:
    assert accounts.get("/api/teachers/T001/availability").status_code == 401


def test_a_wrong_password_and_an_unknown_user_are_indistinguishable(
    accounts: TestClient,
) -> None:
    """Both 401, and the same 401.

    A different status or message for "no such user" turns the login form into
    a way of enumerating who has an account.
    """
    wrong = accounts.post("/api/auth/token", data={"username": "t001", "password": "nope"})
    unknown = accounts.post("/api/auth/token", data={"username": "ghost", "password": "nope"})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_which_teacher_the_caller_is_comes_from_the_token(accounts: TestClient) -> None:
    """Not from the path, and not from a dropdown.

    Phase 4 took it from the path and said so; this is the line it left. A
    teacher's own identity must not be something the request can assert.
    """
    token = _token(accounts, "t001")

    response = accounts.get("/api/auth/me", headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["teacher"] == "T001"
