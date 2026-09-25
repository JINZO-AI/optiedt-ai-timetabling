"""User accounts and role assignments (institution-wide user management)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from optiedt.api.deps import DbSession, PageDep, PrincipalDep
from optiedt.api.schemas.common import Page
from optiedt.api.schemas.users import (
    PasswordResetOut,
    RoleIn,
    SessionsRevokedOut,
    StudentGroupsIn,
    UserCreatedOut,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)
from optiedt.services import users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserOut])
def list_users(
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: str | None = None,
    active: bool | None = None,
) -> Page[UserOut]:
    items, total = users.list_users(
        db,
        principal,
        q=q,
        role=role,
        active=active,
        offset=paging.offset,
        limit=paging.page_size,
    )
    return Page(
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.post("", response_model=UserCreatedOut, status_code=201)
def create_user(body: UserCreateIn, db: DbSession, principal: PrincipalDep) -> UserCreatedOut:
    user, generated = users.create_user(
        db,
        principal,
        users.NewUser(
            username=body.username,
            display_name=body.display_name,
            email=body.email,
            password=body.password,
            roles=[users.RoleSpec(r.role, r.department_id) for r in body.roles],
            instructor_id=body.instructor_id,
            locale=body.locale,
        ),
    )
    db.commit()
    out = UserCreatedOut.model_validate(user)
    out.temporary_password = generated
    return out


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> UserOut:
    return UserOut.model_validate(users.get_user(db, principal, user_id))


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID, body: UserUpdateIn, db: DbSession, principal: PrincipalDep
) -> UserOut:
    values = body.model_dump(exclude_unset=True, exclude={"version"})
    user = users.update_user(db, principal, user_id, version=body.version, values=values)
    db.commit()
    return UserOut.model_validate(user)


@router.put("/{user_id}/roles", response_model=UserOut)
def set_roles(
    user_id: uuid.UUID, body: list[RoleIn], db: DbSession, principal: PrincipalDep
) -> UserOut:
    user = users.set_roles(
        db, principal, user_id, [users.RoleSpec(r.role, r.department_id) for r in body]
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/{user_id}/reset-password", response_model=PasswordResetOut)
def reset_password(user_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> PasswordResetOut:
    password = users.reset_password(db, principal, user_id)
    db.commit()
    return PasswordResetOut(temporary_password=password)


@router.delete("/{user_id}/sessions", response_model=SessionsRevokedOut)
def revoke_sessions(
    user_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> SessionsRevokedOut:
    count = users.revoke_sessions(db, principal, user_id)
    db.commit()
    return SessionsRevokedOut(revoked=count)


@router.get("/{user_id}/student-groups", response_model=list[uuid.UUID])
def get_student_groups(
    user_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> list[uuid.UUID]:
    users.get_user(db, principal, user_id)
    return users.student_group_ids(db, user_id)


@router.put("/{user_id}/student-groups", status_code=204)
def set_student_groups(
    user_id: uuid.UUID, body: StudentGroupsIn, db: DbSession, principal: PrincipalDep
) -> None:
    users.set_student_groups(db, principal, user_id, body.group_ids)
    db.commit()
