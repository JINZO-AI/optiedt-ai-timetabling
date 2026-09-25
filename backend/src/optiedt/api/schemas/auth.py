from __future__ import annotations

import uuid

from pydantic import Field

from optiedt.api.schemas.common import Out, Schema


class LoginIn(Schema):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeIn(Schema):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class RoleOut(Out):
    role: str
    department_id: uuid.UUID | None


class MeOut(Out):
    id: uuid.UUID
    username: str
    display_name: str
    email: str | None
    locale: str | None
    instructor_id: uuid.UUID | None
    must_change_password: bool
    roles: list[RoleOut]
    permissions: dict[str, list[str] | None]
    """Permission → department ids it covers, or null when it applies everywhere."""
    csrf_token: str
