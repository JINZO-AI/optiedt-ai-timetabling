"""User accounts and role assignments."""

from __future__ import annotations

import re
import secrets
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, FieldError, InvalidInput, NotFound, PermissionDenied
from optiedt.models import (
    Department,
    Instructor,
    RoleAssignment,
    StudentGroup,
    StudentMembership,
    User,
    UserSession,
)
from optiedt.models.identity import ROLES
from optiedt.security import passwords
from optiedt.security.permissions import ADMIN_ROLES, Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import apply_changes, check_version, get_or_404, page

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


@dataclass(frozen=True, slots=True)
class RoleSpec:
    role: str
    department_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class NewUser:
    username: str
    display_name: str
    email: str | None
    password: str | None
    roles: Sequence[RoleSpec]
    instructor_id: uuid.UUID | None = None
    locale: str | None = None


def _require_manager(principal: Principal) -> None:
    principal.require_everywhere(Permission.USERS_MANAGE)


def _is_system_admin(principal: Principal) -> bool:
    return "system_admin" in principal.role_names


def _validate_roles(db: Session, principal: Principal, roles: Sequence[RoleSpec]) -> None:
    errors = []
    seen = set()
    for index, spec in enumerate(roles):
        key = (spec.role, spec.department_id)
        if key in seen:
            errors.append(FieldError(f"roles.{index}", "Duplicate role assignment."))
        seen.add(key)
        if spec.role not in ROLES:
            errors.append(FieldError(f"roles.{index}.role", f"Unknown role {spec.role!r}."))
            continue
        if spec.role in ADMIN_ROLES and spec.department_id is not None:
            errors.append(
                FieldError(f"roles.{index}.department_id", "Administrator roles are not scoped.")
            )
        if spec.role == "system_admin" and not _is_system_admin(principal):
            raise PermissionDenied("Only a system administrator can grant that role.")
        if spec.department_id is not None and db.get(Department, spec.department_id) is None:
            errors.append(FieldError(f"roles.{index}.department_id", "Unknown department."))
    if errors:
        raise InvalidInput("Some role assignments are invalid.", errors)


def _check_instructor_link(
    db: Session, instructor_id: uuid.UUID | None, user_id: uuid.UUID | None
) -> None:
    if instructor_id is None:
        return
    if db.get(Instructor, instructor_id) is None:
        raise InvalidInput("Unknown instructor.", [FieldError("instructor_id", "Not found.")])
    linked = db.scalar(select(User.id).where(User.instructor_id == instructor_id))
    if linked is not None and linked != user_id:
        raise Conflict("This instructor is already linked to another account.")


def _active_system_admins(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(func.distinct(User.id)))
            .join(RoleAssignment, RoleAssignment.user_id == User.id)
            .where(RoleAssignment.role == "system_admin", User.is_active.is_(True))
        )
        or 0
    )


def temporary_password() -> str:
    return secrets.token_urlsafe(12)


def create_user(db: Session, principal: Principal, data: NewUser) -> tuple[User, str | None]:
    """Returns the user and, when no password was given, the generated temporary password."""
    _require_manager(principal)
    username = data.username.strip().lower()
    if not USERNAME_PATTERN.match(username):
        raise InvalidInput(
            "Invalid username.",
            [
                FieldError(
                    "username",
                    "Use 3 to 64 lowercase letters, digits, dots, dashes or underscores.",
                )
            ],
        )
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise Conflict("That username is already taken.", code="duplicate")
    _validate_roles(db, principal, data.roles)
    _check_instructor_link(db, data.instructor_id, None)

    generated = None
    password = data.password
    if password is None:
        generated = password = temporary_password()
    else:
        problems = passwords.policy_violations(password, username=username)
        if problems:
            raise InvalidInput(
                "The password does not meet the policy.",
                [FieldError("password", p) for p in problems],
            )

    user = User(
        username=username,
        display_name=data.display_name.strip(),
        email=(data.email or "").strip() or None,
        password_hash=passwords.hash_password(password),
        must_change_password=True,
        instructor_id=data.instructor_id,
        locale=data.locale,
    )
    user.roles = [
        RoleAssignment(role=r.role, department_id=r.department_id, created_by_id=principal.user_id)
        for r in data.roles
    ]
    db.add(user)
    db.flush()
    audit.record(
        db,
        principal,
        action="user.create",
        entity_type="user",
        entity_id=user.id,
        summary=f"Created account {username}",
        changes={"roles": [[r.role, r.department_id] for r in data.roles]},
    )
    return user, generated


def update_user(
    db: Session,
    principal: Principal,
    user_id: uuid.UUID,
    *,
    version: int,
    values: dict[str, object],
) -> User:
    _require_manager(principal)
    user = get_or_404(db, User, user_id, "User")
    check_version(user, version, "user")
    if "instructor_id" in values:
        _check_instructor_link(db, values["instructor_id"], user.id)  # type: ignore[arg-type]
    if values.get("is_active") is False and user.is_active:
        if user.id == principal.user_id:
            raise Conflict("You cannot deactivate your own account.")
        is_admin = any(r.role == "system_admin" for r in user.roles)
        if is_admin and _active_system_admins(db) <= 1:
            raise Conflict("The last active system administrator cannot be deactivated.")
    changes = apply_changes(user, values)
    if values.get("is_active") is False:
        _revoke_all(db, user.id)
    if changes:
        audit.record(
            db,
            principal,
            action="user.update",
            entity_type="user",
            entity_id=user.id,
            summary=f"Updated account {user.username}",
            changes=changes,
        )
    return user


def set_roles(
    db: Session, principal: Principal, user_id: uuid.UUID, roles: Sequence[RoleSpec]
) -> User:
    _require_manager(principal)
    user = get_or_404(db, User, user_id, "User")
    _validate_roles(db, principal, roles)
    had_admin = any(r.role == "system_admin" for r in user.roles)
    keeps_admin = any(r.role == "system_admin" for r in roles)
    if had_admin != keeps_admin and not _is_system_admin(principal):
        raise PermissionDenied("Only a system administrator can change that role.")
    if had_admin and not keeps_admin and _active_system_admins(db) <= 1:
        raise Conflict("The last system administrator cannot lose that role.")
    before = sorted((r.role, str(r.department_id or "")) for r in user.roles)
    user.roles.clear()
    db.flush()
    user.roles.extend(
        RoleAssignment(role=r.role, department_id=r.department_id, created_by_id=principal.user_id)
        for r in roles
    )
    db.flush()
    after = sorted((r.role, str(r.department_id or "")) for r in roles)
    if before != after:
        audit.record(
            db,
            principal,
            action="user.roles",
            entity_type="user",
            entity_id=user.id,
            summary=f"Changed roles of {user.username}",
            changes={"roles": [before, after]},
        )
    return user


def _revoke_all(db: Session, user_id: uuid.UUID) -> int:
    result = db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


def reset_password(db: Session, principal: Principal, user_id: uuid.UUID) -> str:
    _require_manager(principal)
    user = get_or_404(db, User, user_id, "User")
    if any(r.role == "system_admin" for r in user.roles) and not _is_system_admin(principal):
        raise PermissionDenied("Only a system administrator can reset that account.")
    password = temporary_password()
    user.password_hash = passwords.hash_password(password)
    user.must_change_password = True
    user.password_changed_at = datetime.now(UTC)
    _revoke_all(db, user.id)
    audit.record(
        db,
        principal,
        action="user.password_reset",
        entity_type="user",
        entity_id=user.id,
        summary=f"Reset the password of {user.username}",
    )
    return password


def revoke_sessions(db: Session, principal: Principal, user_id: uuid.UUID) -> int:
    _require_manager(principal)
    user = get_or_404(db, User, user_id, "User")
    count = _revoke_all(db, user.id)
    audit.record(
        db,
        principal,
        action="user.sessions_revoked",
        entity_type="user",
        entity_id=user.id,
        summary=f"Ended {count} session(s) of {user.username}",
    )
    return count


def set_student_groups(
    db: Session, principal: Principal, user_id: uuid.UUID, group_ids: Sequence[uuid.UUID]
) -> None:
    _require_manager(principal)
    user = get_or_404(db, User, user_id, "User")
    unknown = set(group_ids) - set(
        db.scalars(select(StudentGroup.id).where(StudentGroup.id.in_(group_ids)))
    )
    if unknown:
        raise InvalidInput("Unknown student group.", [FieldError("group_ids", "Not found.")])
    db.execute(delete(StudentMembership).where(StudentMembership.user_id == user.id))
    db.add_all(StudentMembership(user_id=user.id, group_id=g) for g in set(group_ids))
    audit.record(
        db,
        principal,
        action="user.student_groups",
        entity_type="user",
        entity_id=user.id,
        summary=f"Set the student groups of {user.username}",
        changes={"group_ids": [None, sorted(str(g) for g in group_ids)]},
    )


def student_group_ids(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(select(StudentMembership.group_id).where(StudentMembership.user_id == user_id))
    )


def list_users(
    db: Session,
    principal: Principal,
    *,
    q: str | None,
    role: str | None,
    active: bool | None,
    offset: int,
    limit: int,
) -> tuple[Sequence[User], int]:
    _require_manager(principal)
    statement = select(User).order_by(User.username)
    if q:
        like = f"%{q.strip().lower()}%"
        statement = statement.where(
            or_(
                User.username.ilike(like),
                User.display_name.ilike(like),
                User.email.ilike(like),
            )
        )
    if role:
        statement = statement.where(
            User.id.in_(select(RoleAssignment.user_id).where(RoleAssignment.role == role))
        )
    if active is not None:
        statement = statement.where(User.is_active.is_(active))
    return page(db, statement, offset=offset, limit=limit)


def get_user(db: Session, principal: Principal, user_id: uuid.UUID) -> User:
    _require_manager(principal)
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("User")
    return user
