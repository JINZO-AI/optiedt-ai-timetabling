"""FastAPI dependencies: database session, authentication, CSRF and pagination."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from optiedt.config import Settings, get_settings
from optiedt.context import user_id_var
from optiedt.db.session import get_session_factory
from optiedt.errors import PermissionDenied, Unauthenticated
from optiedt.models import User, UserSession
from optiedt.security import tokens
from optiedt.security.permissions import Permission, Principal
from optiedt.services import auth

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
CSRF_HEADER = "x-csrf-token"


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True, slots=True)
class Auth:
    user: User
    session: UserSession
    principal: Principal


def _authenticate(request: Request, db: Session, settings: Settings) -> Auth | None:
    token = request.cookies.get(settings.session_cookie_name)
    resolved = auth.resolve_session(db, settings, token)
    if resolved is None:
        return None
    user, session = resolved
    if request.method not in SAFE_METHODS:
        supplied = request.headers.get(CSRF_HEADER, "")
        if not supplied or not tokens.tokens_equal(supplied, session.csrf_token):
            raise PermissionDenied("The request is missing its security token. Reload the page.")
    principal = auth.build_principal(db, user)
    user_id_var.set(str(user.id))
    return Auth(user=user, session=session, principal=principal)


def require_auth(request: Request, db: DbSession, settings: SettingsDep) -> Auth:
    result = _authenticate(request, db, settings)
    if result is None:
        raise Unauthenticated()
    if result.user.must_change_password and not request.url.path.endswith(
        ("/auth/me", "/auth/password", "/auth/logout")
    ):
        raise PermissionDenied("Change your password before continuing.")
    return result


def optional_auth(request: Request, db: DbSession, settings: SettingsDep) -> Auth | None:
    return _authenticate(request, db, settings)


AuthDep = Annotated[Auth, Depends(require_auth)]
OptionalAuthDep = Annotated[Auth | None, Depends(optional_auth)]


def principal_of(auth_: AuthDep) -> Principal:
    return auth_.principal


PrincipalDep = Annotated[Principal, Depends(principal_of)]


def requires(permission: Permission):  # type: ignore[no-untyped-def]
    """Dependency that fails fast when the caller lacks ``permission`` entirely."""

    def check(principal: PrincipalDep) -> Principal:
        principal.require(permission)
        return principal

    return Depends(check)


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: Annotated[int, Query(ge=1, le=100_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


PageDep = Annotated[PageParams, Depends(page_params)]
