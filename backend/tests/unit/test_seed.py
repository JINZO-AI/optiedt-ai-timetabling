"""The seed command — C-18.

What matters here is not that it creates accounts but **that it refuses**: it
runs against an installation with no authentication yet, and a convenience
script that can silently re-provision a populated system is a way to lose
control of one.
"""

from __future__ import annotations

import pytest

from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole
from optiedt.services.seed import ADMINISTRATOR, PERSON_IN_CHARGE, STUDENT, seed
from optiedt.services.users import InMemoryUserStore

TEACHERS = ("T001", "T002")


@pytest.fixture(autouse=True)
def fixed_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the password so the tests do not depend on `secrets`."""
    monkeypatch.setenv("OPTIEDT_SEED_PASSWORD", "seeded-password")


def test_it_creates_the_three_staff_accounts_and_one_per_teacher() -> None:
    store = InMemoryUserStore()
    created = seed(store, TEACHERS)

    assert [c.username for c in created] == [
        PERSON_IN_CHARGE,
        ADMINISTRATOR,
        STUDENT,
        "t001",
        "t002",
    ]
    assert len(store.all()) == 5


def test_every_teacher_account_is_linked_to_its_teacher_id() -> None:
    """⚠️ Without the link, the token cannot say whose grid this is, and
    "a teacher account obtains only its own availability" is unenforceable."""
    store = InMemoryUserStore()
    seed(store, TEACHERS)

    linked = {u.username: u.teacher for u in store.all() if u.role is UserRole.TEACHER}
    assert linked == {"t001": "T001", "t002": "T002"}


def test_the_staff_accounts_carry_no_teacher_link() -> None:
    store = InMemoryUserStore()
    seed(store, TEACHERS)

    staff = {u.username: u for u in store.all() if u.role is not UserRole.TEACHER}
    assert staff[PERSON_IN_CHARGE].role is UserRole.PERSON_IN_CHARGE
    assert staff[ADMINISTRATOR].role is UserRole.ADMINISTRATOR
    assert staff[STUDENT].role is UserRole.STUDENT
    assert all(u.teacher is None for u in staff.values())


def test_the_accounts_it_creates_can_actually_sign_in() -> None:
    """A seed that writes an unusable hash would look successful."""
    store = InMemoryUserStore()
    seed(store, TEACHERS)

    assert store.authenticate(PERSON_IN_CHARGE, "seeded-password") is not None
    assert store.authenticate(PERSON_IN_CHARGE, "wrong") is None


def test_it_refuses_an_installation_that_already_has_accounts() -> None:
    """⚠️ The behaviour this file exists for.

    It provisions a system that has no authentication until it runs. Adding to
    a populated one — creating a second `responsable` with a password printed
    to a console — is not something it should be able to do by accident.
    """
    store = InMemoryUserStore()
    store.create(User(id="existing", username="existing", role=UserRole.TEACHER), "pw")

    with pytest.raises(RuntimeError, match="already has accounts"):
        seed(store, TEACHERS)

    assert len(store.all()) == 1, "a refused seed must create nothing at all"


def test_a_generated_password_is_not_a_constant(monkeypatch: pytest.MonkeyPatch) -> None:
    """⚠️ No hardcoded fallback: a default password in a repository is a
    published credential, and this creates the account that may launch runs and
    read every teacher's week."""
    monkeypatch.delenv("OPTIEDT_SEED_PASSWORD", raising=False)

    first = seed(InMemoryUserStore(), ())[0].password
    second = seed(InMemoryUserStore(), ())[0].password

    assert first != second
    assert len(first) >= 16
