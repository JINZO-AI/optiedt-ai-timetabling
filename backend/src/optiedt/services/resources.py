"""Create, update and delete for reference-data records.

Each record type is described once by a ``Resource``: its write permission, whether that
permission is department-scoped, how to name a record in the audit trail, and a validation
hook for rules the database cannot express. The functions below apply those rules uniformly:
optimistic concurrency, scope checks, audit entries, and readable errors for duplicates and
records still in use.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from psycopg import errors as pg_errors
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from optiedt.db.base import Base
from optiedt.errors import Conflict
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import apply_changes, check_version, get_or_404

Validator = Callable[[Session, Any, dict[str, Any]], None]
"""(db, existing record or None, proposed values) → raises InvalidInput/Conflict."""

TABLE_LABELS = {
    "activities": "activities",
    "activity_rooms": "activity room preferences",
    "activity_groups": "activities",
    "activity_instructors": "activities",
    "activity_features": "activities",
    "activity_types": "activity types",
    "availability_grids": "availability grids",
    "buildings": "buildings",
    "courses": "courses",
    "departments": "departments",
    "fixed_placements": "fixed placements",
    "instructors": "instructors",
    "programmes": "programmes",
    "role_assignments": "role assignments",
    "room_feature_links": "rooms",
    "rooms": "rooms",
    "student_groups": "student groups",
    "users": "user accounts",
}


@dataclass(frozen=True, slots=True)
class Resource:
    model: type[Base]
    label: str
    audit_type: str
    write_permission: Permission
    describe: Callable[[Any], str]
    duplicate_message: str
    department_of: Callable[[Any], uuid.UUID | None] | None = None
    """Set when the write permission is department-scoped by the record's department."""
    validate: Validator | None = None
    extra_fields: tuple[str, ...] = field(default_factory=tuple)
    """Values handled by ``apply_extra`` rather than plain attribute assignment."""
    apply_extra: Callable[[Session, Any, dict[str, Any]], dict[str, list[Any]]] | None = None


def _require_write(
    principal: Principal, resource: Resource, department_id: uuid.UUID | None
) -> None:
    if resource.department_of is None:
        principal.require_everywhere(resource.write_permission)
    else:
        principal.require(resource.write_permission, department_id)
        if department_id is None:
            principal.require_everywhere(resource.write_permission)


def _translate_integrity(error: IntegrityError, resource: Resource) -> Conflict:
    original = error.orig
    if isinstance(original, pg_errors.UniqueViolation):
        return Conflict(resource.duplicate_message, code="duplicate")
    if isinstance(original, pg_errors.ForeignKeyViolation):
        table = getattr(getattr(original, "diag", None), "table_name", None) or ""
        constraint = getattr(getattr(original, "diag", None), "constraint_name", None) or ""
        referencing = next(
            (label for name, label in TABLE_LABELS.items() if constraint.startswith(f"fk_{name}_")),
            TABLE_LABELS.get(table, "other records"),
        )
        return Conflict(
            f"This {resource.label} is still used by {referencing}. Remove those references "
            "first, or deactivate it instead.",
            code="in_use",
        )
    return Conflict(f"The {resource.label} could not be saved because of conflicting data.")


def _split(resource: Resource, values: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    plain = {k: v for k, v in values.items() if k not in resource.extra_fields}
    extra = {k: v for k, v in values.items() if k in resource.extra_fields}
    return plain, extra


def create(db: Session, principal: Principal, resource: Resource, values: dict[str, Any]) -> Any:
    department_id = values.get("department_id") if resource.department_of else None
    _require_write(principal, resource, department_id)
    if resource.validate:
        resource.validate(db, None, values)
    plain, extra = _split(resource, values)
    record = resource.model(**plain)
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
    except IntegrityError as error:
        raise _translate_integrity(error, resource) from error
    if resource.apply_extra and extra:
        resource.apply_extra(db, record, extra)
        db.flush()
    audit.record(
        db,
        principal,
        action=f"{resource.audit_type}.create",
        entity_type=resource.audit_type,
        entity_id=record.id,  # type: ignore[attr-defined]
        summary=f"Created {resource.label} {resource.describe(record)}",
        changes=audit.field_changes({}, values),
        department_ids=[department_id] if department_id else [],
    )
    return record


def update(
    db: Session,
    principal: Principal,
    resource: Resource,
    record_id: uuid.UUID,
    *,
    version: int,
    values: Mapping[str, Any],
) -> Any:
    record = get_or_404(db, resource.model, record_id, resource.label.capitalize())
    current_department = resource.department_of(record) if resource.department_of else None
    _require_write(principal, resource, current_department)
    if resource.department_of and "department_id" in values:
        _require_write(principal, resource, values["department_id"])
    check_version(record, version, resource.label)
    if resource.validate:
        resource.validate(db, record, dict(values))
    plain, extra = _split(resource, dict(values))
    try:
        with db.begin_nested():
            changes = apply_changes(record, plain)
            if resource.apply_extra and extra:
                extra_changes = resource.apply_extra(db, record, extra)
                if extra_changes:
                    changes.update(extra_changes)
                    # Touching a column issues an UPDATE, so a relationship-only edit (such as
                    # a room's features) still increments the record's version.
                    record.updated_at = datetime.now(UTC)  # type: ignore[attr-defined]
            db.flush()
    except IntegrityError as error:
        raise _translate_integrity(error, resource) from error
    if changes:
        audit.record(
            db,
            principal,
            action=f"{resource.audit_type}.update",
            entity_type=resource.audit_type,
            entity_id=record_id,
            summary=f"Updated {resource.label} {resource.describe(record)}",
            changes=changes,
            department_ids=[
                d for d in {current_department, resource.department_of(record)} if d is not None
            ]
            if resource.department_of
            else [],
        )
    return record


def delete(db: Session, principal: Principal, resource: Resource, record_id: uuid.UUID) -> None:
    record = get_or_404(db, resource.model, record_id, resource.label.capitalize())
    department_id = resource.department_of(record) if resource.department_of else None
    _require_write(principal, resource, department_id)
    description = resource.describe(record)
    try:
        with db.begin_nested():
            db.delete(record)
            db.flush()
    except IntegrityError as error:
        raise _translate_integrity(error, resource) from error
    audit.record(
        db,
        principal,
        action=f"{resource.audit_type}.delete",
        entity_type=resource.audit_type,
        entity_id=record_id,
        summary=f"Deleted {resource.label} {description}",
        department_ids=[department_id] if department_id else [],
    )
