"""Constraint rules and objective profiles of a term."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, FieldError, InvalidInput, NotFound, PermissionDenied
from optiedt.models import (
    Activity,
    ConstraintRule,
    Course,
    Department,
    Instructor,
    ObjectiveProfile,
    Period,
    Programme,
    StudentGroup,
)
from optiedt.problem.catalog import (
    RULE_TYPES,
    RuleDefinitionError,
    validate_objectives,
    validate_rule,
)
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import apply_changes, check_version
from optiedt.services.terms import get_term


def _referenced_departments(
    db: Session, term_id: uuid.UUID, params: dict[str, Any], scope: dict[str, Any]
) -> set[uuid.UUID | None]:
    """Departments of every record a rule targets; ``None`` stands for 'everything'."""
    errors: list[FieldError] = []
    departments: set[uuid.UUID | None] = set()
    if scope.get("all_instructors") or scope.get("all_groups"):
        departments.add(None)

    instructor_ids = [uuid.UUID(str(i)) for i in scope.get("instructor_ids", [])]
    rows = dict(
        db.execute(
            select(Instructor.id, Instructor.department_id).where(Instructor.id.in_(instructor_ids))
        ).all()
    )
    if len(rows) != len(set(instructor_ids)):
        errors.append(FieldError("scope.instructor_ids", "Unknown instructor."))
    departments.update(rows.values())

    group_ids = [uuid.UUID(str(g)) for g in scope.get("group_ids", [])]
    groups = db.execute(
        select(StudentGroup.id, Programme.department_id)
        .outerjoin(Programme, Programme.id == StudentGroup.programme_id)
        .where(StudentGroup.id.in_(group_ids), StudentGroup.term_id == term_id)
    ).all()
    if len(groups) != len(set(group_ids)):
        errors.append(FieldError("scope.group_ids", "A group does not belong to this term."))
    departments.update(dept for _, dept in groups)

    department_ids = [uuid.UUID(str(d)) for d in scope.get("department_ids", [])]
    found = set(db.scalars(select(Department.id).where(Department.id.in_(department_ids))))
    if found != set(department_ids):
        errors.append(FieldError("scope.department_ids", "Unknown department."))
    departments.update(found)

    activity_ids = [uuid.UUID(str(a)) for a in scope.get("activity_ids", [])]
    for key in ("first_activity_id", "second_activity_id"):
        if scope.get(key):
            activity_ids.append(uuid.UUID(str(scope[key])))
    activities = db.execute(
        select(Activity.id, Course.department_id)
        .join(Course, Course.id == Activity.course_id)
        .where(Activity.id.in_(activity_ids), Activity.term_id == term_id)
    ).all()
    if len(activities) != len(set(activity_ids)):
        errors.append(FieldError("scope", "An activity does not belong to this term."))
    departments.update(dept for _, dept in activities)

    term = get_term(db, term_id)
    term_periods = {str(p) for p in db.scalars(select(Period.id).where(Period.term_id == term_id))}
    period_refs = list(params.get("period_ids", []))
    if params.get("period_id"):
        period_refs.append(params["period_id"])
    for slot in params.get("slots", []):
        period_refs.append(slot["period_id"])
        if slot["weekday"] not in term.weekdays:
            errors.append(FieldError("params.slots", "A slot is not on a teaching day."))
    if any(str(p) not in term_periods for p in period_refs):
        errors.append(FieldError("params", "A period does not belong to this term."))
    if errors:
        raise InvalidInput("The rule refers to records that do not exist.", errors)
    return departments


def _require_rule_scope(principal: Principal, departments: set[uuid.UUID | None]) -> None:
    scope = principal.scope(Permission.RULES_MANAGE)
    if scope.is_empty:
        raise PermissionDenied()
    if scope.everywhere:
        return
    if None in departments or not departments or not scope.covers_all(departments):
        raise PermissionDenied("This rule targets records outside your departments.")


def _parse(
    values: dict[str, Any], current: ConstraintRule | None
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    rule_type = values.get("rule_type", current.rule_type if current else None)
    params = values.get("params", current.params if current else {})
    scope = values.get("scope", current.scope if current else {})
    try:
        clean_params, clean_scope = validate_rule(str(rule_type), params or {}, scope or {})
    except RuleDefinitionError as error:
        raise InvalidInput(
            "The rule is invalid.", [FieldError(error.field, error.message)]
        ) from error
    enforcement = values.get("enforcement", current.enforcement if current else "hard")
    if enforcement not in ("hard", "soft"):
        raise InvalidInput("Invalid enforcement.", [FieldError("enforcement", "hard or soft.")])
    return str(rule_type), clean_params, clean_scope


def list_rules(db: Session, principal: Principal, term_id: uuid.UUID) -> list[ConstraintRule]:
    principal.require(Permission.TERM_DATA_READ)
    get_term(db, term_id)
    return list(
        db.scalars(
            select(ConstraintRule)
            .where(ConstraintRule.term_id == term_id)
            .order_by(ConstraintRule.enforcement, ConstraintRule.tier, ConstraintRule.name)
        )
    )


def _get_rule(db: Session, term_id: uuid.UUID, rule_id: uuid.UUID) -> ConstraintRule:
    rule = db.get(ConstraintRule, rule_id)
    if rule is None or rule.term_id != term_id:
        raise NotFound("Rule")
    return rule


def create_rule(
    db: Session, principal: Principal, term_id: uuid.UUID, values: dict[str, Any]
) -> ConstraintRule:
    get_term(db, term_id)
    rule_type, params, scope = _parse(values, None)
    _require_rule_scope(principal, _referenced_departments(db, term_id, params, scope))
    rule = ConstraintRule(
        term_id=term_id,
        rule_type=rule_type,
        name=values.get("name") or RULE_TYPES[rule_type].name,
        enforcement=values.get("enforcement", "hard"),
        tier=values.get("tier", 2),
        weight=values.get("weight", 1),
        params=params,
        scope=scope,
        is_enabled=values.get("is_enabled", True),
        notes=values.get("notes"),
    )
    db.add(rule)
    db.flush()
    audit.record(
        db,
        principal,
        action="rule.create",
        entity_type="constraint_rule",
        entity_id=rule.id,
        term_id=term_id,
        summary=f"Created {rule.enforcement} rule '{rule.name}'",
        changes={"params": [None, params], "scope": [None, scope]},
    )
    return rule


def update_rule(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    rule_id: uuid.UUID,
    *,
    version: int,
    values: dict[str, Any],
) -> ConstraintRule:
    rule = _get_rule(db, term_id, rule_id)
    _require_rule_scope(principal, _referenced_departments(db, term_id, rule.params, rule.scope))
    check_version(rule, version, "rule")
    rule_type, params, scope = _parse(values, rule)
    _require_rule_scope(principal, _referenced_departments(db, term_id, params, scope))
    updates = {
        k: v
        for k, v in values.items()
        if k in ("name", "enforcement", "tier", "weight", "is_enabled", "notes")
    }
    updates.update(rule_type=rule_type, params=params, scope=scope)
    changes = apply_changes(rule, updates)
    db.flush()
    if changes:
        audit.record(
            db,
            principal,
            action="rule.update",
            entity_type="constraint_rule",
            entity_id=rule.id,
            term_id=term_id,
            summary=f"Updated rule '{rule.name}'",
            changes=changes,
        )
    return rule


def delete_rule(db: Session, principal: Principal, term_id: uuid.UUID, rule_id: uuid.UUID) -> None:
    rule = _get_rule(db, term_id, rule_id)
    _require_rule_scope(principal, _referenced_departments(db, term_id, rule.params, rule.scope))
    name = rule.name
    db.delete(rule)
    db.flush()
    audit.record(
        db,
        principal,
        action="rule.delete",
        entity_type="constraint_rule",
        entity_id=rule_id,
        term_id=term_id,
        summary=f"Deleted rule '{name}'",
    )


# ── objective profiles ─────────────────────────────────────────────────


def list_profiles(db: Session, principal: Principal, term_id: uuid.UUID) -> list[ObjectiveProfile]:
    principal.require(Permission.TERM_DATA_READ)
    get_term(db, term_id)
    return list(
        db.scalars(
            select(ObjectiveProfile)
            .where(ObjectiveProfile.term_id == term_id)
            .order_by(ObjectiveProfile.position, ObjectiveProfile.code)
        )
    )


def _objectives(values: dict[str, Any]) -> dict[str, Any]:
    try:
        return validate_objectives(values)
    except RuleDefinitionError as error:
        raise InvalidInput(
            "The objective profile is invalid.", [FieldError(error.field, error.message)]
        ) from error


def create_profile(
    db: Session, principal: Principal, term_id: uuid.UUID, values: dict[str, Any]
) -> ObjectiveProfile:
    principal.require_everywhere(Permission.RULES_MANAGE)
    get_term(db, term_id)
    if db.scalar(
        select(ObjectiveProfile.id).where(
            ObjectiveProfile.term_id == term_id, ObjectiveProfile.code == values["code"]
        )
    ):
        raise Conflict("A profile with this code already exists.", code="duplicate")
    profile = ObjectiveProfile(
        term_id=term_id,
        code=values["code"],
        name=values["name"],
        description=values.get("description"),
        objectives=_objectives(values.get("objectives", {})),
        position=values.get("position", 100),
    )
    db.add(profile)
    db.flush()
    audit.record(
        db,
        principal,
        action="profile.create",
        entity_type="objective_profile",
        entity_id=profile.id,
        term_id=term_id,
        summary=f"Created objective profile '{profile.name}'",
    )
    return profile


def update_profile(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    profile_id: uuid.UUID,
    *,
    version: int,
    values: dict[str, Any],
) -> ObjectiveProfile:
    principal.require_everywhere(Permission.RULES_MANAGE)
    profile = db.get(ObjectiveProfile, profile_id)
    if profile is None or profile.term_id != term_id:
        raise NotFound("Objective profile")
    check_version(profile, version, "objective profile")
    if "objectives" in values:
        values = {**values, "objectives": _objectives(values["objectives"])}
    changes = apply_changes(profile, values)
    db.flush()
    if changes:
        audit.record(
            db,
            principal,
            action="profile.update",
            entity_type="objective_profile",
            entity_id=profile.id,
            term_id=term_id,
            summary=f"Updated objective profile '{profile.name}'",
            changes=changes,
        )
    return profile


def delete_profile(
    db: Session, principal: Principal, term_id: uuid.UUID, profile_id: uuid.UUID
) -> None:
    principal.require_everywhere(Permission.RULES_MANAGE)
    profile = db.get(ObjectiveProfile, profile_id)
    if profile is None or profile.term_id != term_id:
        raise NotFound("Objective profile")
    name = profile.name
    db.delete(profile)
    db.flush()
    audit.record(
        db,
        principal,
        action="profile.delete",
        entity_type="objective_profile",
        entity_id=profile_id,
        term_id=term_id,
        summary=f"Deleted objective profile '{name}'",
    )
