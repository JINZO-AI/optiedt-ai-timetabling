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


def _token(client: TestClient, username: str, password: str = PASSWORD) -> str:
    response = client.post("/api/auth/token", data={"username": username, "password": password})
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


# ── Account management through the interface (Phase 11) ────────────────
#
# SRS Table 2 gives the administrator "management of the accounts and of the
# calendar". C-18 recorded that right as unimplemented in Phase 5 and said
# plainly that a green FR-11 must not be read as covering it; these are what
# make it covered.
#
# ⚠️ A store of their own, function-scoped, because these tests CREATE and
# DELETE accounts. Sharing the module fixture would let one test's new account
# change what another sees - and `test_a_removed_account_can_no_longer_sign_in`
# would be one ordering away from removing an account the others sign in with.


@pytest.fixture
def managed() -> Iterator[TestClient]:
    store = InMemoryUserStore()
    store.create(User(id="a1", username="administrateur", role=UserRole.ADMINISTRATOR), PASSWORD)
    store.create(User(id="u2", username="responsable", role=UserRole.PERSON_IN_CHARGE), PASSWORD)
    for cached in (deps.get_settings, deps.get_instance, deps.get_availability_store):
        cached.cache_clear()
    app.dependency_overrides[deps.get_user_store] = lambda: store
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _new_account(**overrides: object) -> dict[str, object]:
    account: dict[str, object] = {
        "username": "nouveau",
        "password": "a-password-long-enough",
        "role": "PERSON_IN_CHARGE",
    }
    account.update(overrides)
    return account


def test_an_administrator_creates_an_account_that_can_then_sign_in(managed: TestClient) -> None:
    """**The whole of what C-18 left owed**, end to end: an account that exists
    because an administrator made it, and works because it was really created.

    Signing in afterwards is the assertion that matters. A 201 alone would pass
    for an endpoint that stored a row nobody could authenticate against - which
    is exactly the defect the seed command shipped in Phase 5, where 47
    accounts existed and not one could sign in.
    """
    admin = _token(managed, "administrateur")

    created = managed.post("/api/accounts", json=_new_account(), headers=_auth(admin))

    assert created.status_code == 201, created.text
    assert created.json()["username"] == "nouveau"
    signed_in = managed.post(
        "/api/auth/token", data={"username": "nouveau", "password": "a-password-long-enough"}
    )
    assert signed_in.status_code == 200


def test_the_created_account_never_reports_its_credential(managed: TestClient) -> None:
    """The password goes in and does not come out, by construction.

    `domain.User` has no field for it, so this is checking a design rather than
    a filter - which is the point of the seam `services/users.py` describes.
    """
    admin = _token(managed, "administrateur")

    body = managed.post("/api/accounts", json=_new_account(), headers=_auth(admin)).json()

    assert set(body) == {"id", "username", "role", "teacher", "group"}


def test_only_an_administrator_manages_accounts(managed: TestClient) -> None:
    """⚠️ The person in charge is refused, and that is SRS Table 2 read
    literally: they have read and write on all *data*, and accounts are the
    administrator's surface. C-8 settled that Table 2 wins over the prose."""
    responsable = _token(managed, "responsable")

    assert managed.get("/api/accounts", headers=_auth(responsable)).status_code == 403
    assert (
        managed.post("/api/accounts", json=_new_account(), headers=_auth(responsable)).status_code
        == 403
    )
    assert (
        managed.delete("/api/accounts/responsable", headers=_auth(responsable)).status_code == 403
    )


def test_an_anonymous_caller_manages_nothing(managed: TestClient) -> None:
    assert managed.get("/api/accounts").status_code == 401
    assert managed.post("/api/accounts", json=_new_account()).status_code == 401


def test_a_teacher_account_must_name_a_teacher_that_exists(managed: TestClient) -> None:
    """Refused at creation rather than at first use.

    `routers/availability` refuses an unlinked teacher account every grid, so
    admitting one here would only move the failure to the moment somebody tries
    to work - and a link to a teacher the instance does not have is the same
    account wearing a plausible value.
    """
    admin = _token(managed, "administrateur")

    unlinked = managed.post(
        "/api/accounts", json=_new_account(role="TEACHER"), headers=_auth(admin)
    )
    unknown = managed.post(
        "/api/accounts",
        json=_new_account(username="autre", role="TEACHER", teacher="T999"),
        headers=_auth(admin),
    )

    assert unlinked.status_code == 422
    assert "requires a teacher" in unlinked.json()["detail"]
    assert unknown.status_code == 422
    assert "T999" in unknown.json()["detail"]


def test_a_student_account_must_name_a_group_that_exists(managed: TestClient) -> None:
    """SRS Table 2's other scoped role, refused by the same rule."""
    admin = _token(managed, "administrateur")

    unlinked = managed.post(
        "/api/accounts", json=_new_account(role="STUDENT"), headers=_auth(admin)
    )
    unknown = managed.post(
        "/api/accounts",
        json=_new_account(username="autre", role="STUDENT", group="no-such-group"),
        headers=_auth(admin),
    )

    assert unlinked.status_code == 422
    assert "requires a group" in unlinked.json()["detail"]
    assert unknown.status_code == 422


def test_a_link_the_role_does_not_carry_is_refused_rather_than_dropped(
    managed: TestClient,
) -> None:
    """A field silently ignored is a field somebody will believe was stored."""
    admin = _token(managed, "administrateur")

    response = managed.post(
        "/api/accounts",
        json=_new_account(role="ADMINISTRATOR", teacher="T001"),
        headers=_auth(admin),
    )

    assert response.status_code == 422
    assert "may not carry a teacher" in response.json()["detail"]


def test_a_short_password_is_refused(managed: TestClient) -> None:
    admin = _token(managed, "administrateur")

    response = managed.post(
        "/api/accounts", json=_new_account(password="court"), headers=_auth(admin)
    )

    assert response.status_code == 422


def test_a_duplicate_username_is_a_conflict_rather_than_a_silent_overwrite(
    managed: TestClient,
) -> None:
    """⚠️ 409, and the existing account is untouched.

    An overwrite here would let a second `POST` replace the credential of an
    account already in use - the one way an account-creation screen can become
    an account-takeover screen.
    """
    admin = _token(managed, "administrateur")

    response = managed.post(
        "/api/accounts",
        json=_new_account(username="responsable", password="another-long-password"),
        headers=_auth(admin),
    )

    assert response.status_code == 409
    assert (
        managed.post(
            "/api/auth/token", data={"username": "responsable", "password": PASSWORD}
        ).status_code
        == 200
    ), "the existing account must still authenticate with its own password"


def test_a_removed_account_can_no_longer_sign_in(managed: TestClient) -> None:
    """Removal is the other half of management, and it must actually take."""
    admin = _token(managed, "administrateur")
    managed.post("/api/accounts", json=_new_account(), headers=_auth(admin))

    removed = managed.delete("/api/accounts/nouveau", headers=_auth(admin))

    assert removed.status_code == 204
    assert (
        managed.post(
            "/api/auth/token", data={"username": "nouveau", "password": "a-password-long-enough"}
        ).status_code
        == 401
    )


def test_an_administrator_may_not_remove_their_own_account(managed: TestClient) -> None:
    """A lockout rather than a mistake: no screen creates an administrator
    except this one, and the seed command refuses a populated system (C-18)."""
    admin = _token(managed, "administrateur")

    response = managed.delete("/api/accounts/administrateur", headers=_auth(admin))

    assert response.status_code == 409
    assert managed.get("/api/accounts", headers=_auth(admin)).status_code == 200


def test_an_administrator_always_survives_every_removal(managed: TestClient) -> None:
    """⚠️ **The property the self-removal refusal actually buys**, stated once
    rather than guarded twice.

    Only an administrator reaches this endpoint and they may not remove
    themselves, so every removal leaves its caller behind and the count can
    never reach zero. A first draft of this router also carried a "this is the
    last administrator" check; writing this test is what showed it could never
    run - to be deleting the last administrator you must be deleting yourself,
    which the refusal above has already stopped. The dead branch was removed
    rather than left to look like protection.
    """
    admin = _token(managed, "administrateur")
    managed.post(
        "/api/accounts",
        json=_new_account(username="admin2", role="ADMINISTRATOR"),
        headers=_auth(admin),
    )
    second = _token(managed, "admin2", "a-password-long-enough")

    # The second administrator removes the first: permitted, and one remains.
    assert managed.delete("/api/accounts/administrateur", headers=_auth(second)).status_code == 204
    # The one that remains cannot remove itself, so none is the last state.
    assert managed.delete("/api/accounts/admin2", headers=_auth(second)).status_code == 409

    remaining = managed.get("/api/accounts", headers=_auth(second)).json()
    assert [u["username"] for u in remaining if u["role"] == "ADMINISTRATOR"] == ["admin2"]


def test_removing_an_account_that_does_not_exist_is_a_404(managed: TestClient) -> None:
    admin = _token(managed, "administrateur")

    assert managed.delete("/api/accounts/fantome", headers=_auth(admin)).status_code == 404
