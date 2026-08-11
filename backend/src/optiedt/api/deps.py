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

from optiedt.assistant.service import DefaultAssistant, assistant_from_settings
from optiedt.core.config import Settings
from optiedt.core.security import InvalidTokenError, read_access_token
from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole
from optiedt.domain.instance import Instance
from optiedt.instance.loader import load_instance
from optiedt.instance.loader import resolve_instance_path as loader_instance_path
from optiedt.services.availability import AvailabilityStore, apply_declarations
from optiedt.services.calendar import CalendarStore, apply_calendar
from optiedt.services.publications import PublicationStore
from optiedt.services.runs import RunStore
from optiedt.services.stores import (
    build_availability_store,
    build_calendar_store,
    build_publication_store,
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


@lru_cache(maxsize=1)
def get_calendar_store() -> CalendarStore:
    """The administrator's calendar — FR-9. Database-backed by default."""
    return build_calendar_store(get_settings())


def effective_instance() -> Instance:
    """The loaded instance with the administrator's calendar applied (FR-9).

    ⚠️ **Not cached, and `get_instance()` is left pristine.** Layering rather
    than editing is what lets a closed half-day be withdrawn — the same reason
    FR-2's declarations are layered — and caching this would mean a calendar
    saved through the interface took effect only after a restart.

    This is what every screen reads, so a slot the administrator closed shows
    as closed on the availability grid and in every timetable view, and it is
    what the pre-analysis measures its occupancy against.
    """
    return apply_calendar(get_instance(), get_calendar_store())


def solve_instance() -> Instance:
    """The instance a run actually solves: the calendar, plus declarations.

    This is where FR-2 meets FR-13 — the reason the availability grid is not a
    screen that writes to nothing — and, since Phase 11, where FR-9 meets them
    both. Resolved per run rather than cached, so a declaration or a closure
    made between two runs is picked up by the second.

    ⚠️ **Order matters and is not arbitrary.** The calendar is applied first so
    that declarations are laid over the week as the institution actually has
    it; the reverse would be indistinguishable here (they touch different
    fields) and would stop being so the day a rule reads both.
    """
    return apply_declarations(effective_instance(), get_availability_store())


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
def get_publication_store() -> PublicationStore:
    """Publications — FR-19's trace. Database-backed unless `persistence = memory`."""
    return build_publication_store(get_settings())


@lru_cache(maxsize=1)
def get_user_store() -> UserStore:
    """Accounts — FR-11. Database-backed unless `persistence = memory`."""
    return build_user_store(get_settings())


@lru_cache(maxsize=1)
def get_assistant() -> DefaultAssistant:
    """The language service — FR-22, FR-24, FR-25.

    ⚠️ **Off by default**, and the default is the interesting case: every other
    route works with it off, which is invariant 5 exercised by the ordinary
    configuration rather than by a special test.

    ⚠️ **It is handed no store, and that is invariant 4.** A router assembles
    `RunFacts` from the run record and passes values; the assistant looks
    nothing up and holds no connection. `.importlinter` forbids
    `assistant -> db` so the boundary fails the build rather than a review.
    """
    settings = get_settings()
    return assistant_from_settings(
        enabled=settings.assistant_enabled,
        base_url=settings.assistant_base_url,
        api_key=settings.assistant_api_key,
        model=settings.assistant_model,
        timeout_seconds=settings.assistant_timeout_seconds,
    )


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
InstanceDep = Annotated[Instance, Depends(effective_instance)]
"""The instance as the administrator's calendar leaves it (FR-9).

⚠️ **`effective_instance`, not `get_instance`.** Every router that renders or
validates against the week must see the calendar in force; a screen reading the
pristine CSVs would show a half-day the administrator closed as open, and a
teacher could declare availability on it. `get_instance()` stays pristine and
is reached only through the layering functions, which is what keeps a closure
withdrawable.
"""

PristineInstanceDep = Annotated[Instance, Depends(get_instance)]
"""The 13 CSVs as loaded, before any calendar edit — for the administration
screen, which must show what it is editing away from."""

AvailabilityStoreDep = Annotated[AvailabilityStore, Depends(get_availability_store)]
CalendarStoreDep = Annotated[CalendarStore, Depends(get_calendar_store)]
RunStoreDep = Annotated[RunStore, Depends(get_run_store)]
UserStoreDep = Annotated[UserStore, Depends(get_user_store)]
PublicationStoreDep = Annotated[PublicationStore, Depends(get_publication_store)]
ExecutorDep = Annotated[RunExecutor, Depends(get_executor)]
AssistantDep = Annotated[DefaultAssistant, Depends(get_assistant)]
CurrentUserDep = Annotated[User, Depends(current_user)]

PersonInChargeDep = Annotated[User, Depends(require_role(UserRole.PERSON_IN_CHARGE))]
"""Read and write on ALL data; launch runs; compare; publish (SRS Table 2)."""

AdministratorDep = Annotated[User, Depends(require_role(UserRole.ADMINISTRATOR))]
"""Management of the accounts and of the calendar (SRS Table 2) — FR-9, FR-11.

⚠️ **The administrator alone, and not the person in charge.** Table 2 gives
these two surfaces to one actor and C-8 already settled that Table 2 wins where
the prose disagrees. Widening it to "whoever has the most rights elsewhere"
would be this layer deciding a right the specification assigns.
"""

StudentDep = Annotated[User, Depends(require_role(UserRole.STUDENT))]
"""Read the timetable of their group (SRS Table 2), and nothing else."""

WorksOnTimetablesDep = Annotated[
    User,
    Depends(require_role(UserRole.PERSON_IN_CHARGE, UserRole.TEACHER, UserRole.ADMINISTRATOR)),
]
"""Everyone whose work is the timetable itself — every role except the student.

⚠️ **This is the first right in the project stated by exclusion, and the reason
is in SRS Table 2.** The student's row is *"read the timetable of their group"*:
a run carries every group's draft timetables, so an account that could read one
would be reading forty-nine groups' weeks and every candidate that was never
published. Phase 9's audit recorded that `GET /runs/{id}` took any authenticated
caller; that was harmless while every role worked on timetables, and the student
is the role for which it stopped being so.

**It is not a substitute for the narrower checks.** A teacher still reaches only
their own availability (`routers/availability._require_own_grid`) and only the
person in charge may launch a run or publish.
"""
