"""Sign-in, sign-out, current identity and password change."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from optiedt.api.deps import AuthDep, DbSession, SettingsDep
from optiedt.api.schemas.auth import LoginIn, MeOut, PasswordChangeIn, RoleOut
from optiedt.config import Settings
from optiedt.models import User, UserSession
from optiedt.security.permissions import Principal
from optiedt.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _me(user: User, session: UserSession, principal: Principal) -> MeOut:
    return MeOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        locale=user.locale,
        instructor_id=user.instructor_id,
        must_change_password=user.must_change_password,
        roles=[RoleOut(role=r, department_id=d) for r, d in principal.roles],
        permissions={
            str(p): None if s.everywhere else sorted(str(d) for d in s.departments)
            for p, s in principal.grants.items()
        },
        csrf_token=session.csrf_token,
    )


def _set_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_absolute_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=MeOut, summary="Sign in with username and password")
def login(
    body: LoginIn, request: Request, response: Response, db: DbSession, settings: SettingsDep
) -> MeOut:
    result = auth.login(
        db,
        settings,
        username=body.username,
        password=body.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    _set_cookie(response, settings, result.token)
    principal = auth.build_principal(db, result.user)
    return _me(result.user, result.session, principal)


@router.post("/logout", status_code=204, summary="Sign out and end this session")
def logout(auth_: AuthDep, response: Response, db: DbSession, settings: SettingsDep) -> None:
    auth.logout(db, auth_.session, auth_.principal)
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=MeOut, summary="The signed-in user and their permissions")
def me(auth_: AuthDep) -> MeOut:
    return _me(auth_.user, auth_.session, auth_.principal)


@router.post("/password", status_code=204, summary="Change the signed-in user's password")
def change_password(body: PasswordChangeIn, auth_: AuthDep, db: DbSession) -> None:
    auth.change_password(
        db,
        auth_.user,
        auth_.principal,
        current=body.current_password,
        new=body.new_password,
        keep_session_id=auth_.session.id,
    )
    db.commit()
