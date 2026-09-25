"""Roles, permissions and department scopes.

A role assignment grants the role's permissions either institution-wide or within one
department subtree. ``Principal`` answers, per permission, whether the user holds it and over
which departments. Every service call receives the principal and checks it; the interface
only mirrors these answers.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from optiedt.errors import PermissionDenied


class Permission(StrEnum):
    REFERENCE_READ = "reference.read"
    INSTITUTION_MANAGE = "institution.manage"
    ORGANIZATION_MANAGE = "organization.manage"
    CATALOGUE_MANAGE = "catalogue.manage"
    TERMS_MANAGE = "terms.manage"
    STAFF_MANAGE = "staff.manage"
    COURSES_MANAGE = "courses.manage"
    TERM_DATA_READ = "term_data.read"
    TERM_DATA_MANAGE = "term_data.manage"
    AVAILABILITY_MANAGE = "availability.manage"
    AVAILABILITY_SELF = "availability.self"
    RULES_MANAGE = "rules.manage"
    SCHEDULING_RUN = "scheduling.run"
    SOLUTIONS_READ = "solutions.read"
    SOLUTIONS_EDIT = "solutions.edit"
    SOLUTIONS_APPROVE = "solutions.approve"
    PUBLICATIONS_READ = "publications.read"
    PUBLICATIONS_PUBLISH = "publications.publish"
    EXCEPTIONS_MANAGE = "exceptions.manage"
    PORTAL_SELF = "portal.self"
    IMPORTS_RUN = "imports.run"
    EXPORTS_RUN = "exports.run"
    USERS_MANAGE = "users.manage"
    AUDIT_READ = "audit.read"
    SYSTEM_READ = "system.read"
    ASSISTANT_USE = "assistant.use"


P = Permission

ROLE_PERMISSIONS: Mapping[str, frozenset[Permission]] = {
    "system_admin": frozenset(Permission),
    "institution_admin": frozenset(
        {
            P.REFERENCE_READ,
            P.INSTITUTION_MANAGE,
            P.ORGANIZATION_MANAGE,
            P.CATALOGUE_MANAGE,
            P.TERMS_MANAGE,
            P.STAFF_MANAGE,
            P.COURSES_MANAGE,
            P.TERM_DATA_READ,
            P.SOLUTIONS_READ,
            P.PUBLICATIONS_READ,
            P.IMPORTS_RUN,
            P.EXPORTS_RUN,
            P.USERS_MANAGE,
            P.AUDIT_READ,
            P.ASSISTANT_USE,
        }
    ),
    "scheduling_officer": frozenset(
        {
            P.REFERENCE_READ,
            P.STAFF_MANAGE,
            P.COURSES_MANAGE,
            P.TERM_DATA_READ,
            P.TERM_DATA_MANAGE,
            P.AVAILABILITY_MANAGE,
            P.RULES_MANAGE,
            P.SCHEDULING_RUN,
            P.SOLUTIONS_READ,
            P.SOLUTIONS_EDIT,
            P.PUBLICATIONS_READ,
            P.PUBLICATIONS_PUBLISH,
            P.EXCEPTIONS_MANAGE,
            P.IMPORTS_RUN,
            P.EXPORTS_RUN,
            P.AUDIT_READ,
            P.ASSISTANT_USE,
        }
    ),
    "department_head": frozenset(
        {
            P.REFERENCE_READ,
            P.TERM_DATA_READ,
            P.AVAILABILITY_MANAGE,
            P.SOLUTIONS_READ,
            P.SOLUTIONS_APPROVE,
            P.PUBLICATIONS_READ,
            P.EXPORTS_RUN,
            P.AUDIT_READ,
            P.ASSISTANT_USE,
        }
    ),
    "instructor": frozenset({P.PORTAL_SELF, P.AVAILABILITY_SELF}),
    "student": frozenset({P.PORTAL_SELF}),
    "viewer": frozenset({P.REFERENCE_READ, P.TERM_DATA_READ, P.PUBLICATIONS_READ, P.EXPORTS_RUN}),
}

ADMIN_ROLES = frozenset({"system_admin", "institution_admin"})


@dataclass(frozen=True, slots=True)
class Scope:
    """Where a permission applies: everywhere, or within a set of departments."""

    everywhere: bool = False
    departments: frozenset[uuid.UUID] = frozenset()

    def covers(self, department_id: uuid.UUID | None) -> bool:
        if self.everywhere:
            return True
        return department_id is not None and department_id in self.departments

    def covers_all(self, department_ids: Iterable[uuid.UUID | None]) -> bool:
        return all(self.covers(d) for d in department_ids)

    @property
    def is_empty(self) -> bool:
        return not self.everywhere and not self.departments


NO_SCOPE = Scope()
EVERYWHERE = Scope(everywhere=True)


def expand_departments(
    roots: Iterable[uuid.UUID], parent_of: Mapping[uuid.UUID, uuid.UUID | None]
) -> frozenset[uuid.UUID]:
    """Every department in the subtrees rooted at ``roots``."""
    children: dict[uuid.UUID, list[uuid.UUID]] = {}
    for dept, parent in parent_of.items():
        if parent is not None:
            children.setdefault(parent, []).append(dept)
    result: set[uuid.UUID] = set()
    stack = list(roots)
    while stack:
        current = stack.pop()
        if current in result:
            continue
        result.add(current)
        stack.extend(children.get(current, ()))
    return frozenset(result)


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: uuid.UUID
    username: str
    display_name: str
    roles: tuple[tuple[str, uuid.UUID | None], ...]
    instructor_id: uuid.UUID | None = None
    grants: Mapping[Permission, Scope] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        user_id: uuid.UUID,
        username: str,
        display_name: str,
        roles: Iterable[tuple[str, uuid.UUID | None]],
        instructor_id: uuid.UUID | None,
        parent_of: Mapping[uuid.UUID, uuid.UUID | None],
    ) -> Principal:
        roles = tuple(roles)
        everywhere: set[Permission] = set()
        roots: dict[Permission, set[uuid.UUID]] = {}
        for role, department_id in roles:
            for permission in ROLE_PERMISSIONS.get(role, frozenset()):
                if department_id is None:
                    everywhere.add(permission)
                else:
                    roots.setdefault(permission, set()).add(department_id)
        grants: dict[Permission, Scope] = {}
        for permission in set(everywhere) | set(roots):
            if permission in everywhere:
                grants[permission] = EVERYWHERE
            else:
                grants[permission] = Scope(
                    departments=expand_departments(roots[permission], parent_of)
                )
        return cls(
            user_id=user_id,
            username=username,
            display_name=display_name,
            roles=roles,
            instructor_id=instructor_id,
            grants=grants,
        )

    def can(self, permission: Permission) -> bool:
        return permission in self.grants

    def scope(self, permission: Permission) -> Scope:
        return self.grants.get(permission, NO_SCOPE)

    def require(self, permission: Permission, department_id: uuid.UUID | None = None) -> None:
        """Holds ``permission`` at all, or for ``department_id`` when one is given."""
        scope = self.scope(permission)
        if scope.is_empty:
            raise PermissionDenied()
        if department_id is not None and not scope.covers(department_id):
            raise PermissionDenied("This record belongs to a department outside your scope.")

    def require_everywhere(self, permission: Permission) -> None:
        if not self.scope(permission).everywhere:
            raise PermissionDenied("This action needs institution-wide rights.")

    @property
    def role_names(self) -> frozenset[str]:
        return frozenset(role for role, _ in self.roles)

    @property
    def label(self) -> str:
        return f"{self.display_name} ({self.username})"
