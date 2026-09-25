from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from optiedt.api.schemas.common import Name, Out, Schema


class RoleIn(Schema):
    role: str
    department_id: uuid.UUID | None = None


class UserCreateIn(Schema):
    username: str = Field(min_length=3, max_length=64)
    display_name: Name
    email: EmailStr | None = None
    password: str | None = Field(default=None, max_length=256)
    roles: list[RoleIn] = Field(default_factory=list, max_length=20)
    instructor_id: uuid.UUID | None = None
    locale: str | None = Field(default=None, pattern=r"^(en|fr|ar)$")


class UserUpdateIn(Schema):
    version: int
    display_name: Name | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    instructor_id: uuid.UUID | None = None
    locale: str | None = Field(default=None, pattern=r"^(en|fr|ar)$")


class UserRoleOut(Out):
    role: str
    department_id: uuid.UUID | None


class UserOut(Out):
    id: uuid.UUID
    username: str
    display_name: str
    email: str | None
    is_active: bool
    must_change_password: bool
    locale: str | None
    instructor_id: uuid.UUID | None
    last_login_at: datetime | None
    created_at: datetime
    version: int
    roles: list[UserRoleOut]


class UserCreatedOut(UserOut):
    temporary_password: str | None = None
    """Shown once when the account was created without a password."""


class PasswordResetOut(Schema):
    temporary_password: str


class StudentGroupsIn(Schema):
    group_ids: list[uuid.UUID] = Field(max_length=50)


class SessionsRevokedOut(Schema):
    revoked: int
