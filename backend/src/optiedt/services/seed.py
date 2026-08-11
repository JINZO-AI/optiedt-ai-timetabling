"""Create the first accounts — C-18.

    uv run python -m optiedt.services.seed

⚠️ **A development and demonstration tool, not a deployment mechanism.** It
creates accounts with known roles on an installation that has no authentication
until it runs, so it **refuses outright if any account already exists** rather
than adding to a populated system. Re-provisioning a live installation is not
something a convenience script should be able to do by accident.

⚠️ **This command creates the FIRST accounts; it is not how accounts are
managed.** SRS Table 2 gives the administrator that right, C-18 recorded it as
owed by Phase 5, and ✅ **Phase 11 delivered it** — `api/routers/accounts.py`.
This command remains because a management screen cannot create the account that
reaches it.

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
from optiedt.domain.enums import GroupLevel, UserRole
from optiedt.domain.instance import Instance
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
    group: str | None = None


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


def seed(
    store: UserStore,
    teacher_ids: tuple[str, ...],
    password: str | None = None,
    student_group: str | None = None,
) -> list[Created]:
    """Create the accounts. Raises if any account already exists.

    ⚠️ ``password`` is a parameter because deriving it here AND in the caller
    was a defect, not a redundancy. `_password()` returns a fresh
    `secrets.token_urlsafe(16)` whenever OPTIEDT_SEED_PASSWORD is unset - the
    default path - so `main()` printing its own call's result while this
    function stored a different one meant **every account was created with a
    password nobody was ever shown**. The command reported success, 47 accounts
    existed, and not one could sign in.

    Every test pinned OPTIEDT_SEED_PASSWORD, so both calls agreed and the
    divergence was invisible; `main()` is `# pragma: no cover`, so nothing
    exercised the path at all. Found 2026-08-06 while writing the demonstration
    script, whose first step is "seed the accounts and sign in".

    Passing None keeps the old behaviour for a caller that only wants accounts
    and does not need to report the credential.
    """
    if store.all():
        raise RuntimeError(
            "This installation already has accounts. The seed command creates the FIRST "
            "ones and refuses to touch a populated system - re-provisioning is not "
            "something a convenience script should do by accident."
        )

    if password is None:
        password, _generated = _password()
    created: list[Created] = []

    for username, role in (
        (PERSON_IN_CHARGE, UserRole.PERSON_IN_CHARGE),
        (ADMINISTRATOR, UserRole.ADMINISTRATOR),
        (STUDENT, UserRole.STUDENT),
    ):
        # ⚠️ The student is given a GROUP, and only the student. SRS Table 2
        # grants that role "the timetable of their group", and
        # `routers/student` refuses an account that cannot say which group it
        # belongs to - a seeded student with no link would create exactly the
        # account the demonstration cannot use.
        group = student_group if role is UserRole.STUDENT else None
        store.create(User(id=username, username=username, role=role, group=group), password)
        created.append(Created(username=username, role=role, password=password, group=group))

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

    return created


def _teacher_ids(settings: Settings) -> tuple[str, ...]:
    """Read straight from the CSVs. `services` may reach the loader; reaching
    up into `api.deps` for its cached copy would invert the module map."""
    instance = load_instance(resolve_instance_path(settings.instance_path))
    return tuple(t.id for t in instance.teachers)


def smallest_group(instance: Instance) -> str | None:
    """The finest group a student can belong to, chosen deterministically.

    A student belongs to a laboratory subgroup, which is the bottom of the
    promotion -> tutorial group -> subgroup chain; the timetable shown for it
    already includes its ancestors' sessions, so the finest link is also the
    most complete week (`services/timetables.py`).

    ⚠️ **Deterministic, not arbitrary**: the first TP group by id, so two seeds
    of the same instance produce the same account. Returns None on an instance
    with no subgroups rather than inventing one - the seed then creates a
    student with no group, which `routers/student` refuses in the open, instead
    of silently attaching it to a promotion.
    """
    subgroups = sorted(g.id for g in instance.groups if g.level is GroupLevel.TP)
    return subgroups[0] if subgroups else None


def _student_group(settings: Settings) -> str | None:
    instance = load_instance(resolve_instance_path(settings.instance_path))
    return smallest_group(instance)


def main() -> int:  # pragma: no cover - the console entry point
    settings = Settings()
    password, generated = _password()

    print(f"Seeding accounts into {settings.database_url.rsplit('@', 1)[-1]}")
    try:
        # ⚠️ The password derived above is PASSED IN, not re-derived. Letting
        # `seed()` call `_password()` again meant it stored a different token
        # from the one printed here whenever OPTIEDT_SEED_PASSWORD was unset.
        created = seed(
            build_user_store(settings),
            _teacher_ids(settings),
            password=password,
            student_group=_student_group(settings),
        )
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
