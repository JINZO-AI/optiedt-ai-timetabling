"""Student groups of a term: a tree with partition keys (ADR 0011)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, FieldError, InvalidInput, NotFound
from optiedt.models import Programme, StudentGroup, activity_groups
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import apply_changes, check_version
from optiedt.services.terms import get_term

PARTITION_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")


def department_of_group(db: Session, group: StudentGroup) -> uuid.UUID | None:
    if group.programme_id is None:
        return None
    return db.scalar(select(Programme.department_id).where(Programme.id == group.programme_id))


def _department_of_programme(db: Session, programme_id: uuid.UUID | None) -> uuid.UUID | None:
    if programme_id is None:
        return None
    department = db.scalar(select(Programme.department_id).where(Programme.id == programme_id))
    if department is None:
        raise InvalidInput("Unknown programme.", [FieldError("programme_id", "Not found.")])
    return department


def _require(principal: Principal, department_id: uuid.UUID | None) -> None:
    if department_id is None:
        principal.require_everywhere(Permission.TERM_DATA_MANAGE)
    else:
        principal.require(Permission.TERM_DATA_MANAGE, department_id)


def _get(db: Session, term_id: uuid.UUID, group_id: uuid.UUID) -> StudentGroup:
    group = db.get(StudentGroup, group_id)
    if group is None or group.term_id != term_id:
        raise NotFound("Student group")
    return group


def _validate(
    db: Session, term_id: uuid.UUID, group: StudentGroup | None, values: dict[str, Any]
) -> None:
    errors = []
    key = values.get("partition_key")
    if key is not None and not PARTITION_PATTERN.match(key):
        errors.append(
            FieldError("partition_key", "Use lowercase letters, digits, dashes or underscores.")
        )
    parent_id = values.get("parent_id", group.parent_id if group else None)
    if parent_id is not None:
        parent = db.get(StudentGroup, parent_id)
        if parent is None or parent.term_id != term_id:
            errors.append(FieldError("parent_id", "No such group in this term."))
        elif group is not None:
            seen: set[uuid.UUID] = set()
            current: uuid.UUID | None = parent_id
            while current is not None and current not in seen:
                if current == group.id:
                    errors.append(
                        FieldError("parent_id", "A group cannot be placed under its own subgroup.")
                    )
                    break
                seen.add(current)
                current = db.scalar(
                    select(StudentGroup.parent_id).where(StudentGroup.id == current)
                )
    if errors:
        raise InvalidInput("The student group is invalid.", errors)


def list_groups(db: Session, principal: Principal, term_id: uuid.UUID) -> list[StudentGroup]:
    principal.require(Permission.TERM_DATA_READ)
    get_term(db, term_id)
    return list(
        db.scalars(
            select(StudentGroup).where(StudentGroup.term_id == term_id).order_by(StudentGroup.code)
        )
    )


def create_group(
    db: Session, principal: Principal, term_id: uuid.UUID, values: dict[str, Any]
) -> StudentGroup:
    get_term(db, term_id)
    _require(principal, _department_of_programme(db, values.get("programme_id")))
    _validate(db, term_id, None, values)
    if db.scalar(
        select(StudentGroup.id).where(
            StudentGroup.term_id == term_id, StudentGroup.code == values["code"]
        )
    ):
        raise Conflict("A group with this code already exists in the term.", code="duplicate")
    group = StudentGroup(term_id=term_id, **values)
    db.add(group)
    db.flush()
    audit.record(
        db,
        principal,
        action="group.create",
        entity_type="student_group",
        entity_id=group.id,
        term_id=term_id,
        summary=f"Created student group {group.code} ({group.size} students)",
        department_ids=[department_of_group(db, group)],
    )
    return group


def update_group(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    group_id: uuid.UUID,
    *,
    version: int,
    values: dict[str, Any],
) -> StudentGroup:
    group = _get(db, term_id, group_id)
    _require(principal, department_of_group(db, group))
    if "programme_id" in values:
        _require(principal, _department_of_programme(db, values["programme_id"]))
    check_version(group, version, "student group")
    _validate(db, term_id, group, values)
    if "code" in values and values["code"] != group.code:
        clash = db.scalar(
            select(StudentGroup.id).where(
                StudentGroup.term_id == term_id, StudentGroup.code == values["code"]
            )
        )
        if clash:
            raise Conflict("A group with this code already exists in the term.", code="duplicate")
    changes = apply_changes(group, values)
    db.flush()
    if changes:
        audit.record(
            db,
            principal,
            action="group.update",
            entity_type="student_group",
            entity_id=group.id,
            term_id=term_id,
            summary=f"Updated student group {group.code}",
            changes=changes,
            department_ids=[department_of_group(db, group)],
        )
    return group


def delete_group(
    db: Session, principal: Principal, term_id: uuid.UUID, group_id: uuid.UUID
) -> None:
    group = _get(db, term_id, group_id)
    department = department_of_group(db, group)
    _require(principal, department)
    if db.scalar(select(StudentGroup.id).where(StudentGroup.parent_id == group.id).limit(1)):
        raise Conflict("Delete or move this group's subgroups first.", code="in_use")
    in_use = db.scalar(
        select(activity_groups.c.activity_id).where(activity_groups.c.group_id == group.id).limit(1)
    )
    if in_use:
        raise Conflict(
            "This group attends activities. Remove it from those activities first.",
            code="in_use",
        )
    code = group.code
    db.delete(group)
    db.flush()
    audit.record(
        db,
        principal,
        action="group.delete",
        entity_type="student_group",
        entity_id=group_id,
        term_id=term_id,
        summary=f"Deleted student group {code}",
        department_ids=[department],
    )


def partition_warnings(groups: Sequence[StudentGroup]) -> list[str]:
    """Sizes of disjoint children should add up to their parent's size."""
    by_id = {g.id: g for g in groups}
    children: dict[tuple[uuid.UUID, str], list[StudentGroup]] = {}
    for group in groups:
        if group.parent_id is not None:
            children.setdefault((group.parent_id, group.partition_key), []).append(group)
    warnings = []
    for (parent_id, key), members in sorted(children.items(), key=lambda kv: str(kv[0])):
        parent = by_id[parent_id]
        total = sum(member.size for member in members)
        if total != parent.size:
            warnings.append(
                f"Partition '{key}' of {parent.code}: subgroups total {total} students, "
                f"the group has {parent.size}."
            )
    return warnings
