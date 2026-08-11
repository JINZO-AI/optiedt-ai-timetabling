"""Accounts and authentication — FR-11.

⚠️ **The password hash never leaves this seam.** `authenticate()` takes a
password and returns a `User` that carries no credential at all, so no router,
schema, log line or assistant payload can hold one by accident. That is why
there is no `get_hash()` here and why `domain.User` has no hash field: the
safest place for a secret is one nobody can reach.

The **first** accounts come from a seed command rather than a registration
screen — no requirement describes registration, and the instance carries no
user data (**C-18**). ✅ **Since Phase 11 the administrator manages accounts
through the interface**, which is SRS Table 2's own grant and what C-18 said
the seed command stood in for; the seed still exists, and still refuses to run
on a populated system, because a management screen needs somebody able to sign
in before it can be reached.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Protocol

from optiedt.core.security import hash_password, verify_password
from optiedt.domain.entities import TeacherId, User
from optiedt.domain.enums import UserRole


class UserStore(Protocol):
    """Accounts by username. `SqlUserStore` is the production implementation."""

    def by_username(self, username: str) -> User | None: ...

    def authenticate(self, username: str, password: str) -> User | None:
        """The user, or None for an unknown username OR a wrong password.

        One answer for both, deliberately: distinguishing them tells an
        attacker which usernames exist.
        """
        ...

    def create(self, user: User, password: str) -> None: ...

    def delete(self, username: str) -> bool:
        """Remove an account. True if it existed, False if it never did.

        ⚠️ **Removal is why `api/deps.current_user` re-reads the store on every
        request** rather than trusting the token's claims: a token stays valid
        until it expires, so a deleted account would otherwise keep its rights
        for the rest of that token's life.
        `integration/test_rbac.py::test_a_token_for_a_deleted_account_stops_working`
        is the test that holds it.
        """
        ...

    def all(self) -> tuple[User, ...]: ...


@dataclass(frozen=True, slots=True)
class NewAccount:
    """What the seed command asks for. Carries a password exactly once."""

    username: str
    password: str
    role: UserRole
    teacher: TeacherId | None = None


class InMemoryUserStore:
    """Dict-backed, for tests and for `persistence = memory`.

    Hashes for real rather than storing plaintext: a test double that skips
    hashing cannot catch a verification bug, and this one is asserted against
    the same contract as the database store.
    """

    def __init__(self) -> None:
        self._users: dict[str, tuple[User, str]] = {}
        self._lock = threading.Lock()

    def by_username(self, username: str) -> User | None:
        with self._lock:
            found = self._users.get(username)
            return found[0] if found else None

    def authenticate(self, username: str, password: str) -> User | None:
        with self._lock:
            found = self._users.get(username)
        if found is None:
            return None
        user, hashed = found
        return user if verify_password(password, hashed) else None

    def create(self, user: User, password: str) -> None:
        with self._lock:
            if user.username in self._users:
                raise KeyError(f"user {user.username} already exists")
            self._users[user.username] = (user, hash_password(password))

    def delete(self, username: str) -> bool:
        with self._lock:
            return self._users.pop(username, None) is not None

    def all(self) -> tuple[User, ...]:
        with self._lock:
            return tuple(
                user for user, _ in sorted(self._users.values(), key=lambda p: p[0].username)
            )
