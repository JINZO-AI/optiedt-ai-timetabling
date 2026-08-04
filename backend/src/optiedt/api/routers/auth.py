"""FR-11 — signing in, and asking who you are.

`POST /api/auth/token` follows the OAuth2 password-flow shape (form-encoded
`username`/`password`, a bearer token back) because FastAPI's
`OAuth2PasswordBearer` and the generated `/api/docs` both understand it for
free. It is not an OAuth2 deployment: there is no authorisation server, no
refresh token and no scope beyond the role.

⚠️ **The response is the same for an unknown username and a wrong password.**
Telling them apart tells an attacker which accounts exist.

⚠️ **No account is created here.** Provisioning is a seed command — C-18 in
`docs/open-questions.md`, recorded with what it costs: account management
through the interface is not delivered by Phase 5.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from optiedt.api.deps import CurrentUserDep, SettingsDep, UserStoreDep
from optiedt.api.schemas import TokenOut, UserOut
from optiedt.core.security import create_access_token

router = APIRouter(tags=["auth"])


@router.post("/auth/token", response_model=TokenOut, summary="Sign in; returns a bearer token")
def sign_in(
    store: UserStoreDep,
    settings: SettingsDep,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenOut:
    user = store.authenticate(form.username, form.password)
    if user is None:
        # One message for both cases - see the module docstring.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(
        access_token=create_access_token(
            subject=user.username,
            role=user.role.value,
            secret_key=settings.secret_key,
            expires_minutes=settings.access_token_expire_minutes,
            teacher_id=user.teacher,
        ),
        token_type="bearer",
    )


@router.get("/auth/me", response_model=UserOut, summary="The signed-in account")
def me(user: CurrentUserDep) -> UserOut:
    """What the interface needs to decide which screens to offer.

    It decides what to OFFER, never what is permitted: every endpoint checks
    the role for itself, because a client that hides a control has not
    prevented the request.
    """
    return UserOut.of(user)
