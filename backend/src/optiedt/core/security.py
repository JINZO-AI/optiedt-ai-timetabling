"""Password hashing and bearer tokens — FR-11.

⚠️ **bcrypt directly, not passlib.** `passlib[bcrypt]` was a declared dependency
from the scaffold onwards and does not work: passlib 1.7.4 (2020, unmaintained)
reads `bcrypt.__about__`, which bcrypt 5 removed, and its `hash()` raises
*"password cannot be longer than 72 bytes"* on any input at all. Measured
2026-08-04 on passlib 1.7.4 + bcrypt 5.0.0 — not a corner case, hashing simply
failed. Pinning bcrypt backwards to keep an unmaintained wrapper working is the
wrong direction when the wrapped API is four lines.

⚠️ **bcrypt truncates silently past 72 bytes, so this module refuses instead.**
That is the actual security bug the passlib error was gesturing at: a
71-character password and a 200-character one that shares its first 71
characters would hash identically, and the second user would be far weaker than
they believe. Rejecting is honest; the alternative used elsewhere — SHA-256
pre-hashing — is defensible but adds a construction nobody here needs.

This module holds no policy about WHO may do what. That is `api/deps.py` and
`docs/domain-model.md`'s rights table; here there is only "is this the password"
and "who does this token say they are".
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72
"""bcrypt's hard limit. Beyond it the tail is IGNORED, not rejected."""


class PasswordTooLongError(ValueError):
    """Raised rather than truncated. See the module docstring."""


class InvalidTokenError(Exception):
    """The token is absent, malformed, expired, or signed with another key.

    One exception for all four on purpose: telling a caller *which* of them
    went wrong tells an attacker the same thing.
    """


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            f"password is {len(encoded)} bytes; bcrypt reads only the first "
            f"{MAX_PASSWORD_BYTES} and would silently ignore the rest"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """False for a wrong password AND for a malformed hash.

    `bcrypt.checkpw` raises on a hash it cannot parse. A stored value that is
    not a bcrypt hash — a column half-migrated, a fixture with a plain string —
    must fail closed rather than propagate, or a corrupted row becomes a 500
    instead of a refused sign-in.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    subject: str,
    role: str,
    secret_key: str,
    expires_minutes: int,
    teacher_id: str | None = None,
) -> str:
    """A bearer token naming the user, their role and — for a teacher — which
    teacher they are.

    ⚠️ `teacher_id` is in the token because it is the whole of FR-11's
    acceptance criterion: *a teacher account obtains only its own availability
    and timetable*. Taking it from the path instead is exactly what Phase 4
    did, and is the line this milestone moves.
    """
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    if teacher_id is not None:
        claims["teacher"] = teacher_id
    token: str = jwt.encode(claims, secret_key, algorithm=ALGORITHM)
    return token


def read_access_token(token: str, secret_key: str) -> dict[str, Any]:
    """Claims, or `InvalidTokenError`. Expiry is checked by `jwt.decode`."""
    try:
        return dict(jwt.decode(token, secret_key, algorithms=[ALGORITHM]))
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
