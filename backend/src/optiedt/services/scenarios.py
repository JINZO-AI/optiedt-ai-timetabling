"""Scenarios: named ways of solving a term (objective profiles, scope, base solution and
solver settings). Runs are requested from a scenario."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.config import get_settings
from optiedt.errors import FieldError, InvalidInput, NotFound, PermissionDenied
from optiedt.models import Department, ObjectiveProfile, Scenario, Solution
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import apply_changes, check_version
from optiedt.services.terms import get_term

EDITABLE = (
    "name",
    "description",
    "profile_codes",
    "scope_department_ids",
    "base_solution_id",
    "minimize_changes",
    "solver_mode",
    "time_limit_seconds",
    "seed",
)
MODES = ("fastest", "reproducible")


def require_read(principal: Principal) -> None:
    if not (principal.can(Permission.SOLUTIONS_READ) or principal.can(Permission.SCHEDULING_RUN)):
        raise PermissionDenied()


def require_scheduling(principal: Principal, scope_department_ids: Sequence[uuid.UUID]) -> None:
    """Solving the whole term needs institution-wide scheduling rights; a scenario limited to
    departments needs scheduling rights over each of them."""
    grant = principal.scope(Permission.SCHEDULING_RUN)
    if grant.is_empty:
        raise PermissionDenied()
    if grant.everywhere:
        return
    if not scope_department_ids:
        raise PermissionDenied(
            "Scheduling the whole term needs institution-wide rights. Limit the scenario to "
            "your departments."
        )
    if not grant.covers_all(scope_department_ids):
        raise PermissionDenied("The scenario includes departments outside your scope.")


def get_scenario(db: Session, scenario_id: uuid.UUID) -> Scenario:
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise NotFound("Scenario")
    return scenario


def list_scenarios(
    db: Session, principal: Principal, term_id: uuid.UUID, *, include_archived: bool = False
) -> list[Scenario]:
    require_read(principal)
    get_term(db, term_id)
    statement = select(Scenario).where(Scenario.term_id == term_id)
    if not include_archived:
        statement = statement.where(Scenario.archived_at.is_(None))
    return list(db.scalars(statement.order_by(Scenario.created_at)))


def _validate(db: Session, term_id: uuid.UUID, values: dict[str, Any]) -> None:
    errors: list[FieldError] = []
    codes = list(values["profile_codes"])
    known = set(
        db.scalars(select(ObjectiveProfile.code).where(ObjectiveProfile.term_id == term_id))
    )
    if not codes:
        errors.append(FieldError("profile_codes", "Choose at least one objective profile."))
    elif len(set(codes)) != len(codes):
        errors.append(FieldError("profile_codes", "A profile is listed twice."))
    elif any(code not in known for code in codes):
        errors.append(FieldError("profile_codes", "Unknown objective profile for this term."))

    base_id = values["base_solution_id"]
    if base_id is not None:
        base = db.get(Solution, base_id)
        if base is None or base.term_id != term_id:
            errors.append(FieldError("base_solution_id", "No such timetable in this term."))

    scope = list(values["scope_department_ids"])
    found = set(db.scalars(select(Department.id).where(Department.id.in_(scope))))
    if found != set(scope):
        errors.append(FieldError("scope_department_ids", "Unknown department."))
    if scope and base_id is None:
        errors.append(
            FieldError(
                "base_solution_id",
                "A scenario limited to some departments needs a base timetable: the sessions "
                "of other departments stay where it puts them.",
            )
        )
    if values["minimize_changes"] and base_id is None:
        errors.append(
            FieldError("minimize_changes", "Keeping changes small needs a base timetable.")
        )
    if values["solver_mode"] not in MODES:
        errors.append(FieldError("solver_mode", "Use 'fastest' or 'reproducible'."))
    limit = int(values["time_limit_seconds"])
    ceiling = get_settings().solver_max_time_limit_seconds
    if not 5 <= limit <= ceiling:
        errors.append(FieldError("time_limit_seconds", f"Choose between 5 and {ceiling} seconds."))
    if int(values["seed"]) < 0:
        errors.append(FieldError("seed", "The seed cannot be negative."))
    if not str(values["name"]).strip():
        errors.append(FieldError("name", "A name is required."))
    if errors:
        raise InvalidInput("The scenario is invalid.", errors)


def create_scenario(
    db: Session, principal: Principal, term_id: uuid.UUID, values: dict[str, Any]
) -> Scenario:
    get_term(db, term_id)
    values = {
        "description": None,
        "scope_department_ids": [],
        "base_solution_id": None,
        "minimize_changes": False,
        "solver_mode": "fastest",
        "time_limit_seconds": 120,
        "seed": 1,
        **values,
    }
    require_scheduling(principal, values["scope_department_ids"])
    _validate(db, term_id, values)
    scenario = Scenario(term_id=term_id, created_by_id=principal.user_id, **values)
    db.add(scenario)
    db.flush()
    audit.record(
        db,
        principal,
        action="scenario.create",
        entity_type="scenario",
        entity_id=scenario.id,
        summary=f"Created scenario {scenario.name}",
        term_id=term_id,
        department_ids=values["scope_department_ids"],
    )
    return scenario


def update_scenario(
    db: Session,
    principal: Principal,
    scenario_id: uuid.UUID,
    *,
    version: int,
    values: dict[str, Any],
) -> Scenario:
    scenario = get_scenario(db, scenario_id)
    require_scheduling(principal, scenario.scope_department_ids)
    check_version(scenario, version, "scenario")
    merged = {name: values.get(name, getattr(scenario, name)) for name in EDITABLE}
    require_scheduling(principal, merged["scope_department_ids"])
    _validate(db, scenario.term_id, merged)
    changes = apply_changes(scenario, {k: v for k, v in values.items() if k in EDITABLE})
    if changes:
        db.flush()
        audit.record(
            db,
            principal,
            action="scenario.update",
            entity_type="scenario",
            entity_id=scenario.id,
            summary=f"Updated scenario {scenario.name}",
            changes=changes,
            term_id=scenario.term_id,
            department_ids=scenario.scope_department_ids,
        )
    return scenario


def archive_scenario(db: Session, principal: Principal, scenario_id: uuid.UUID) -> Scenario:
    scenario = get_scenario(db, scenario_id)
    require_scheduling(principal, scenario.scope_department_ids)
    if scenario.archived_at is None:
        scenario.archived_at = datetime.now(UTC)
        db.flush()
        audit.record(
            db,
            principal,
            action="scenario.archive",
            entity_type="scenario",
            entity_id=scenario.id,
            summary=f"Archived scenario {scenario.name}",
            term_id=scenario.term_id,
            department_ids=scenario.scope_department_ids,
        )
    return scenario
