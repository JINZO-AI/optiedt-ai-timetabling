"""FR-11 — the administrator manages the accounts.

    Acceptance criterion (SRS §8.6 Table 35, transcribed in
    docs/testing-strategy.md §4):
    "Connect with a teacher account → access limited to own data."

    Rights (SRS Table 2, transcribed in docs/domain-model.md, authoritative by
    C-8): the administrator manages *"the accounts and the calendar"*.

⚠️ **This is what C-18 recorded as owed, delivered.** Phase 5 provisioned the
first accounts with a seed command because no requirement describes
registration and the instance carries no user data; C-18 said plainly that the
administrator's Table 2 right *"stays unimplemented"* and that a green FR-11
must not be read as covering it. The seed command remains and still refuses to
run on a populated system — it creates the account that reaches this screen,
which is the one thing a management screen cannot do for itself.

⚠️ **No password is ever read back.** It arrives on `AccountIn`, goes into
`UserStore.create`, and is hashed inside the store; `domain.User` has no field
to carry it out again (`services/users.py`). There is no endpoint here that
returns, resets or compares a credential.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from optiedt.api.deps import AdministratorDep, InstanceDep, UserStoreDep
from optiedt.api.schemas import AccountIn, UserOut
from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole

router = APIRouter(tags=["accounts"])

MINIMUM_PASSWORD_LENGTH = 12
"""Long enough that the check is not decoration.

Chosen to match what the seed command generates — `secrets.token_urlsafe(16)`
— rather than picked freely: two different notions of "long enough" in one
application is how the weaker one becomes the real one.
"""


@router.get("/accounts", response_model=list[UserOut], summary="Every account, by username")
def list_accounts(store: UserStoreDep, _user: AdministratorDep) -> list[UserOut]:
    """⚠️ Administrator only. Knowing which accounts exist is itself a right:
    `POST /auth/token` answers identically for an unknown username and a wrong
    password precisely so that this list cannot be reconstructed by guessing."""
    return [UserOut.of(u) for u in store.all()]


@router.post(
    "/accounts",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def create_account(
    instance: InstanceDep,
    store: UserStoreDep,
    _user: AdministratorDep,
    payload: AccountIn,
) -> UserOut:
    """Create one account, with the link its role requires.

    ⚠️ **A TEACHER without a teacher link, or a STUDENT without a group, is
    refused at creation rather than at first use.** `routers/availability`
    already refuses an unlinked teacher account every grid — *"an account that
    cannot say whose grid it owns has no business editing one"* — so admitting
    one here would only move the failure to the moment somebody tries to work.
    The student's link is the same rule for SRS Table 2's other scoped role.
    """
    username = payload.username.strip()
    if not username:
        raise _unprocessable("A username is required")
    if len(payload.password) < MINIMUM_PASSWORD_LENGTH:
        raise _unprocessable(
            f"A password of at least {MINIMUM_PASSWORD_LENGTH} characters is required"
        )

    teacher = _link_for_role(payload.role, UserRole.TEACHER, payload.teacher, "teacher")
    group = _link_for_role(payload.role, UserRole.STUDENT, payload.group, "group")
    if teacher is not None and not any(t.id == teacher for t in instance.teachers):
        raise _unprocessable(f"No teacher {teacher!r} in the instance")
    if group is not None and not any(g.id == group for g in instance.groups):
        raise _unprocessable(f"No group {group!r} in the instance")

    try:
        store.create(
            # `id = username`, as `services/seed.py` already does. A second
            # identifier nobody types would have to be generated, displayed and
            # explained for no question it answers.
            User(id=username, username=username, role=payload.role, teacher=teacher, group=group),
            payload.password,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Account {username!r} already exists"
        ) from exc

    created = store.by_username(username)
    assert created is not None  # written immediately above
    return UserOut.of(created)


@router.delete(
    "/accounts/{username}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an account",
)
def delete_account(store: UserStoreDep, user: AdministratorDep, username: str) -> None:
    """Remove an account. One refusal, and it is the one that matters.

    ⚠️ **Refusing self-removal is what keeps an administrator in existence**,
    and the argument is worth writing out because it is easy to add a second,
    redundant guard for it. Only an administrator reaches this endpoint, and
    they may not remove themselves — so every removal leaves its caller behind,
    and **the number of administrators can never reach zero**. A "this is the
    last administrator" check would therefore be code that can never run: the
    only way to be deleting the last one is to be deleting yourself.

    That matters because there is no registration screen and the seed command
    refuses to run on a populated system (C-18): an installation with no
    administrator has no way back to one short of a database edit.

    Everything else is permitted — a departed teacher's account SHOULD be
    removable, and `api/deps.current_user` re-reads the store on every request
    exactly so that removal takes effect before the token expires.

    A publication keeps the username of whoever published it as text rather
    than as a foreign key, so removing an account never erases the record of
    what it did.
    """
    if username == user.username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An administrator may not remove their own account. Nothing else could "
                "then manage the accounts or the calendar, and no screen creates an "
                "administrator."
            ),
        )

    if store.by_username(username) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No account {username!r}"
        )

    store.delete(username)


def _link_for_role(role: UserRole, requires: UserRole, value: str | None, name: str) -> str | None:
    """The link this role must carry, or the refusal to carry one it must not.

    Refusing a `teacher` on a STUDENT rather than ignoring it: a field that is
    silently dropped is a field somebody will believe was stored.
    """
    if role is requires:
        if value is None or not value.strip():
            raise _unprocessable(f"A {role.value} account requires a {name}")
        return value.strip()
    if value is not None and value.strip():
        raise _unprocessable(f"A {role.value} account may not carry a {name}")
    return None


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
