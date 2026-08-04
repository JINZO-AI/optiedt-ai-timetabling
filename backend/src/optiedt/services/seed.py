"""Create the first accounts — C-18.

    uv run python -m optiedt.services.seed

⚠️ **A development and demonstration tool, not a deployment mechanism.** It
creates accounts with known roles on an installation that has no authentication
until it runs, so it **refuses outright if any account already exists** rather
than adding to a populated system. Re-provisioning a live installation is not
something a convenience script should be able to do by accident.

⚠️ **Account management through the interface is NOT delivered by Phase 5.**
SRS Table 2 gives the administrator that right; C-18 records why this command
exists instead and what it leaves owed. Do not read a working sign-in as
covering it.

Lives in `services/`, not in `db/`: it needs the instance loader and the store
factory, and `db` depends on `domain` alone. C-18 originally named
`optiedt.db.seed` — corrected here, because writing it there would have added
two upward imports to make a script's name prettier.
"""

from __future__ import annotations

import os
import secrets
import sys
from dataclasses import dataclass

from optiedt.core.config import Settings
from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole
from optiedt.instance.loader import load_instance, resolve_instance_path
from optiedt.services.stores import build_user_store
from optiedt.services.users import UserStore

PERSON_IN_CHARGE = "responsable"
ADMINISTRATOR = "administrateur"
STUDENT = "etudiant"

_ENV_PASSWORD = "OPTIEDT_SEED_PASSWORD"


@dataclass(frozen=True, slots=True)
class Created:
    username: str
    role: UserRole
    password: str
    teacher: str | None = None


def _password() -> tuple[str, bool]:
    """The configured password, or a generated one. Never a default.

    A hardcoded fallback in a repository is a published credential, and this
    command creates the account that may launch runs and read every teacher's
    week.
    """
    configured = os.environ.get(_ENV_PASSWORD)
    if configured:
        return configured, False
    return secrets.token_urlsafe(16), True


def seed(store: UserStore, teacher_ids: tuple[str, ...]) -> list[Created]:
    """Create the accounts. Raises if any account already exists."""
    if store.all():
        raise RuntimeError(
            "This installation already has accounts. The seed command creates the FIRST "
            "ones and refuses to touch a populated system - re-provisioning is not "
            "something a convenience script should do by accident."
        )

    password, generated = _password()
    created: list[Created] = []

    for username, role in (
        (PERSON_IN_CHARGE, UserRole.PERSON_IN_CHARGE),
        (ADMINISTRATOR, UserRole.ADMINISTRATOR),
        (STUDENT, UserRole.STUDENT),
    ):
        store.create(User(id=username, username=username, role=role), password)
        created.append(Created(username=username, role=role, password=password))

    # One account per teacher in the instance. The link is what makes "a
    # teacher account obtains only its own availability" expressible at all -
    # without it the token cannot say whose grid this is.
    for teacher_id in teacher_ids:
        username = teacher_id.lower()
        store.create(
            User(
                id=username,
                username=username,
                role=UserRole.TEACHER,
                teacher=teacher_id,
            ),
            password,
        )
        created.append(
            Created(
                username=username,
                role=UserRole.TEACHER,
                password=password,
                teacher=teacher_id,
            )
        )

    del generated  # reported by the caller, which owns the output
    return created


def _teacher_ids(settings: Settings) -> tuple[str, ...]:
    """Read straight from the CSVs. `services` may reach the loader; reaching
    up into `api.deps` for its cached copy would invert the module map."""
    instance = load_instance(resolve_instance_path(settings.instance_path))
    return tuple(t.id for t in instance.teachers)


def main() -> int:  # pragma: no cover - the console entry point
    settings = Settings()
    password, generated = _password()

    print(f"Seeding accounts into {settings.database_url.rsplit('@', 1)[-1]}")
    try:
        created = seed(build_user_store(settings), _teacher_ids(settings))
    except RuntimeError as exc:
        print(f"\nRefused: {exc}", file=sys.stderr)
        return 1

    teachers = [c for c in created if c.role is UserRole.TEACHER]
    print(f"\nCreated {len(created)} accounts: 3 staff + {len(teachers)} teachers.")
    print("\n  username        role")
    for entry in created[:3]:
        print(f"  {entry.username:<15} {entry.role.value}")
    if teachers:
        print(f"  {teachers[0].username:<15} {teachers[0].role.value} -> {teachers[0].teacher}")
        print(f"  ... and {len(teachers) - 1} more, one per teacher id, lowercased")

    if generated:
        print(f"\n  PASSWORD (generated, shown once): {password}")
        print(f"  Set {_ENV_PASSWORD} to choose it instead.")
    else:
        print(f"\n  Password: as set in {_ENV_PASSWORD}.")
    # ASCII only in printed output: the Windows console is cp1252, and a
    # warning sign here crashed the command AFTER it had created 47 accounts
    # (measured 2026-08-04) - a non-zero exit that reads as a failed seed but
    # was not. Comments and docstrings may use any character; stdout may not.
    print("\n!! Every account shares one password. Development and demonstration only.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
