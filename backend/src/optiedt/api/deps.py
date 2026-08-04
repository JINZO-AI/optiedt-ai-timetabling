"""Shared dependencies: settings, the loaded instance, the stores.

The instance is read from the 13 CSVs **once per process** and cached. It is a
frozen dataclass, so sharing one copy between requests is safe, and re-reading
36 KB of CSV on every request would be waste that hides itself.

⚠️ `Settings.instance_path` defaults to `"../data/instance"`, which is relative
to `backend/`. Resolving it against the current working directory would make
the API work under `uvicorn` started from `backend/` and fail under pytest
started from the repository root — a difference that shows up as "the instance
is missing" rather than as a path bug. It is resolved against this file's
location instead, so it does not depend on where the process was started.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from optiedt.core.config import Settings
from optiedt.core.security import InvalidTokenError, read_access_token
from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole
from optiedt.domain.instance import Instance
from optiedt.instance.loader import load_instance
from optiedt.instance.loader import resolve_instance_path as loader_instance_path
from optiedt.services.availability import AvailabilityStore, apply_declarations
from optiedt.services.runs import RunStore
from optiedt.services.stores import (
    build_availability_store,
    build_run_store,
    build_user_store,
)
from optiedt.services.users import UserStore
from optiedt.tasks.executor import RunExecutor, cp_sat_factory

_BACKEND_ROOT = Path(__file__).resolve().parents[3]

API_PREFIX = "/api"
"""Duplicated from `api.main` on purpose: importing it from there would be
circular, since main imports the routers and the routers import this module.
Only the OAuth2 token URL needs it here."""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def resolve_instance_path(settings: Settings) -> Path:
    """Kept as a thin alias: the logic moved to `instance.loader` when
    `services/seed.py` came to need it too."""
    return loader_instance_path(settings.instance_path)


@lru_cache(maxsize=1)
def get_instance() -> Instance:
    """The reference instance, loaded once.

    Deliberately NOT the instance a run solves — that one carries the teachers'
    declarations on top (`services.availability.apply_declarations`). Keeping
    the loaded instance pristine means a declaration can be withdrawn.
    """
    return load_instance(resolve_instance_path(get_settings()))


@lru_cache(maxsize=1)
def get_availability_store() -> AvailabilityStore:
    """Database-backed by default (FR-19, Phase 5 M3).

    Built through `services.stores` rather than named here: this layer may not
    import `optiedt.db` at all (`.importlinter`,
    `api-cannot-reach-the-database`), and the module map gives it `domain` and
    `services` only.
    """
    return build_availability_store(get_settings())


@lru_cache(maxsize=1)
def get_run_store() -> RunStore:
    """The run record — FR-19. Database-backed unless `persistence = memory`."""
    return build_run_store(get_settings())


def solve_instance() -> Instance:
    """The instance a run actually solves: the loaded one plus declarations.

    This is where FR-2 meets FR-13 — the reason the availability grid is not a
    screen that writes to nothing. Resolved per run rather than cached, so a
    declaration made between two runs is picked up by the second.
    """
    return apply_declarations(get_instance(), get_availability_store())


@lru_cache(maxsize=1)
def get_executor() -> RunExecutor:
    """One executor per process, one solve at a time.

    The solver factory comes from `tasks`, not from here: this layer may not
    import the solver at all (`.importlinter`). The API asks for an executor
    and never names CP-SAT.
    """
    settings = get_settings()
    return RunExecutor(
        store=get_run_store(),
        instance_provider=solve_instance,
        solver_factory=cp_sat_factory(
            workers=settings.solver_workers,
            wall_clock_ceiling_seconds=settings.solver_wall_clock_ceiling_seconds,
        ),
    )


@lru_cache(maxsize=1)
def get_user_store() -> UserStore:
    """Accounts — FR-11. Database-backed unless `persistence = memory`."""
    return build_user_store(get_settings())


# ── Authentication and rights (FR-11) ──────────────────────────────────

_bearer = OAuth2PasswordBearer(tokenUrl=f"{API_PREFIX}/auth/token", auto_error=False)
"""`auto_error=False` so a missing token reaches `current_user` and gets the
same 401 as a bad one. With the default, FastAPI raises a 403 for "no header"
and this layer raises 401 for "bad token" - two status codes for one situation,
and the interface would have to know both."""


def current_user(
    settings: SettingsDep,
    store: Annotated[UserStore, Depends(get_user_store)],
    token: Annotated[str | None, Depends(_bearer)] = None,
) -> User:
    """The signed-in account, or 401.

    ⚠️ The user is re-read from the store on every request rather than
    reconstructed from the token's claims. A token stays valid until it
    expires, so an account deleted or given a different role would otherwise
    keep its old rights for the rest of the token's life.
    """
    if token is None:
        raise _unauthorised()
    try:
        claims = read_access_token(token, settings.secret_key)
    except InvalidTokenError as exc:
        raise _unauthorised() from exc

    username = claims.get("sub")
    user = store.by_username(username) if isinstance(username, str) else None
    if user is None:
        raise _unauthorised()
    return user


def _unauthorised() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(*roles: UserRole) -> Callable[[User], User]:
    """A dependency admitting only these roles. 403, not 404.

    The rights are `docs/domain-model.md`'s table, which SRS Table 2 governs
    (C-8). Declared per endpoint rather than centrally: a router that has to
    name who may call it cannot acquire a caller by accident, which a
    middleware pattern-matching on paths can.
    """

    allowed = frozenset(roles)

    def check(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"role {user.role.value} may not do this; "
                    f"requires one of {', '.join(sorted(r.value for r in allowed))}"
                ),
            )
        return user

    return check


SettingsDep = Annotated[Settings, Depends(get_settings)]
InstanceDep = Annotated[Instance, Depends(get_instance)]
AvailabilityStoreDep = Annotated[AvailabilityStore, Depends(get_availability_store)]
RunStoreDep = Annotated[RunStore, Depends(get_run_store)]
UserStoreDep = Annotated[UserStore, Depends(get_user_store)]
ExecutorDep = Annotated[RunExecutor, Depends(get_executor)]
CurrentUserDep = Annotated[User, Depends(current_user)]

PersonInChargeDep = Annotated[User, Depends(require_role(UserRole.PERSON_IN_CHARGE))]
"""Read and write on ALL data; launch runs; compare; publish (SRS Table 2)."""

ManagesDataDep = Annotated[
    User, Depends(require_role(UserRole.PERSON_IN_CHARGE, UserRole.ADMINISTRATOR))
]
"""The two roles that may see the whole instance rather than their own slice."""
