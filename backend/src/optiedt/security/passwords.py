"""Password hashing (Argon2id) and password policy."""

from __future__ import annotations

import contextlib

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_LENGTH = 12
MAX_LENGTH = 256

# Parameters follow RFC 9106's second recommended option (64 MiB, 3 passes, 4 lanes).
_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=4)

# A short denylist of the passwords most often tried first; longer lists belong to a
# breached-password service, which an on-premise deployment cannot rely on.
_COMMON = frozenset(
    {
        "password1234",
        "123456789012",
        "qwertyuiop12",
        "motdepasse12",
        "azertyuiop12",
        "changeme1234",
        "welcome12345",
        "administrator",
        "password12345",
        "letmein12345",
    }
)

_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-password")


def policy_violations(password: str, *, username: str | None = None) -> list[str]:
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"Use at least {MIN_LENGTH} characters.")
    if len(password) > MAX_LENGTH:
        problems.append(f"Use at most {MAX_LENGTH} characters.")
    if password.lower() in _COMMON:
        problems.append("This password is too common.")
    if username and username.lower() in password.lower():
        problems.append("The password must not contain the username.")
    if len(set(password)) < 5:
        problems.append("Use a less repetitive password.")
    return problems


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Constant work whether or not the account exists."""
    if password_hash is None:
        with contextlib.suppress(VerificationError):
            _hasher.verify(_DUMMY_HASH, password)
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)
