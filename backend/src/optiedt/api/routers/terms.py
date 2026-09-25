"""Terms and their data: time grid, timing variants, groups, activities, availability, rules,
objective profiles, and copying from another term."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path

from optiedt.api.deps import DbSession, PageDep, PrincipalDep
from optiedt.api.schemas import terms as s
from optiedt.api.schemas.common import Page
from optiedt.api.schemas.validation import IssueOut, ValidationOut
from optiedt.models import AvailabilityGrid
from optiedt.problem.catalog import OBJECTIVES, RULE_TYPES
from optiedt.problem.issues import Issue
from optiedt.security.permissions import Permission
from optiedt.services import (
    activities,
    availability,
    groups,
    rules,
    term_copy,
    terms,
    validation_report,
)
from optiedt.services.activities import ActivityDetails, FixedSpec

router = APIRouter(prefix="/terms", tags=["terms"])
catalog_router = APIRouter(prefix="/catalog", tags=["rules"])


# ── terms ──────────────────────────────────────────────────────────────


@router.get("", response_model=Page[s.TermOut])
def list_terms(db: DbSession, principal: PrincipalDep, paging: PageDep) -> Page[s.TermOut]:
    items, total = terms.list_terms(db, principal, offset=paging.offset, limit=paging.page_size)
    return Page(
        items=[s.TermOut.model_validate(t) for t in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.post("", response_model=s.TermOut, status_code=201)
def create_term(body: s.TermIn, db: DbSession, principal: PrincipalDep) -> s.TermOut:
    term = terms.create_term(
        db,
        principal,
        code=body.code,
        name=body.name,
        academic_year=body.academic_year,
        start_date=body.start_date,
        end_date=body.end_date,
        weekdays=body.weekdays,
        periods=[
            terms.PeriodSpec(p.label, p.start_time, p.end_time, p.joins_next) for p in body.periods
        ],
        availability_open_until=body.availability_open_until,
        room_capacity_ratio=body.room_capacity_ratio,
    )
    db.commit()
    db.refresh(term)
    return s.TermOut.model_validate(term)


@router.get("/{term_id}", response_model=s.TermOut)
def get_term(term_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.TermOut:
    terms.require_term_read(principal)
    return s.TermOut.model_validate(terms.get_term(db, term_id))


@router.patch("/{term_id}", response_model=s.TermOut)
def update_term(
    term_id: uuid.UUID, body: s.TermPatch, db: DbSession, principal: PrincipalDep
) -> s.TermOut:
    term = terms.update_term(db, principal, term_id, version=body.version, values=body.changes())
    db.commit()
    db.refresh(term)
    return s.TermOut.model_validate(term)


@router.delete("/{term_id}", status_code=204)
def delete_term(term_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> None:
    terms.delete_term(db, principal, term_id)
    db.commit()


@router.post("/{term_id}/copy-from", response_model=s.CopyTermOut)
def copy_from(
    term_id: uuid.UUID, body: s.CopyTermIn, db: DbSession, principal: PrincipalDep
) -> s.CopyTermOut:
    copied, skipped = term_copy.copy_term(db, principal, term_id, body.source_term_id, body.include)
    db.commit()
    return s.CopyTermOut(copied=copied, skipped=skipped)


# ── time grid ──────────────────────────────────────────────────────────


def _grid_out(grid: terms.TimeGrid) -> s.TimeGridOut:
    return s.TimeGridOut(
        term_version=grid.term.version,
        weekdays=list(grid.term.weekdays),
        periods=[s.PeriodOut.model_validate(p) for p in grid.periods],
        slots=[s.SlotOut.model_validate(x) for x in grid.slots],
    )


@router.get("/{term_id}/time-grid", response_model=s.TimeGridOut)
def get_time_grid(term_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.TimeGridOut:
    terms.require_term_read(principal)
    return _grid_out(terms.get_time_grid(db, term_id))


@router.put("/{term_id}/time-grid", response_model=s.TimeGridOut)
def put_time_grid(
    term_id: uuid.UUID, body: s.TimeGridIn, db: DbSession, principal: PrincipalDep
) -> s.TimeGridOut:
    grid = terms.put_time_grid(
        db,
        principal,
        term_id,
        version=body.version,
        weekdays=body.weekdays,
        periods=[
            terms.PeriodSpec(p.label, p.start_time, p.end_time, p.joins_next, p.id)
            for p in body.periods
        ],
        slots=[
            terms.SlotSpec(
                x.weekday,
                x.period_index,
                x.is_closed,
                x.closed_reason,
                x.start_time,
                x.end_time,
                x.penalty,
            )
            for x in body.slots
        ],
    )
    db.commit()
    return _grid_out(grid)


@router.get("/{term_id}/timing-variants", response_model=list[s.TimingVariantOut])
def list_timing_variants(
    term_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> list[s.TimingVariantOut]:
    terms.require_term_read(principal)
    return [s.TimingVariantOut.model_validate(v) for v in terms.list_timing_variants(db, term_id)]


@router.post("/{term_id}/timing-variants", response_model=s.TimingVariantOut, status_code=201)
def create_timing_variant(
    term_id: uuid.UUID, body: s.TimingVariantIn, db: DbSession, principal: PrincipalDep
) -> s.TimingVariantOut:
    variant = terms.put_timing_variant(
        db,
        principal,
        term_id,
        variant_id=None,
        version=None,
        name=body.name,
        start_date=body.start_date,
        end_date=body.end_date,
        periods=[(p.period_id, p.start_time, p.end_time) for p in body.periods],
    )
    db.commit()
    db.refresh(variant)
    return s.TimingVariantOut.model_validate(variant)


@router.put("/{term_id}/timing-variants/{variant_id}", response_model=s.TimingVariantOut)
def update_timing_variant(
    term_id: uuid.UUID,
    variant_id: uuid.UUID,
    body: s.TimingVariantIn,
    db: DbSession,
    principal: PrincipalDep,
) -> s.TimingVariantOut:
    variant = terms.put_timing_variant(
        db,
        principal,
        term_id,
        variant_id=variant_id,
        version=body.version,
        name=body.name,
        start_date=body.start_date,
        end_date=body.end_date,
        periods=[(p.period_id, p.start_time, p.end_time) for p in body.periods],
    )
    db.commit()
    db.refresh(variant)
    return s.TimingVariantOut.model_validate(variant)


@router.delete("/{term_id}/timing-variants/{variant_id}", status_code=204)
def delete_timing_variant(
    term_id: uuid.UUID, variant_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> None:
    terms.delete_timing_variant(db, principal, term_id, variant_id)
    db.commit()


# ── student groups ─────────────────────────────────────────────────────


@router.get("/{term_id}/groups", response_model=s.GroupListOut)
def list_groups(term_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> s.GroupListOut:
    items = groups.list_groups(db, principal, term_id)
    return s.GroupListOut(
        items=[s.GroupOut.model_validate(g) for g in items],
        warnings=groups.partition_warnings(items),
    )


@router.post("/{term_id}/groups", response_model=s.GroupOut, status_code=201)
def create_group(
    term_id: uuid.UUID, body: s.GroupIn, db: DbSession, principal: PrincipalDep
) -> s.GroupOut:
    group = groups.create_group(db, principal, term_id, body.model_dump())
    db.commit()
    db.refresh(group)
    return s.GroupOut.model_validate(group)


@router.patch("/{term_id}/groups/{group_id}", response_model=s.GroupOut)
def update_group(
    term_id: uuid.UUID,
    group_id: uuid.UUID,
    body: s.GroupPatch,
    db: DbSession,
    principal: PrincipalDep,
) -> s.GroupOut:
    group = groups.update_group(
        db, principal, term_id, group_id, version=body.version, values=body.changes()
    )
    db.commit()
    db.refresh(group)
    return s.GroupOut.model_validate(group)


@router.delete("/{term_id}/groups/{group_id}", status_code=204)
def delete_group(
    term_id: uuid.UUID, group_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> None:
    groups.delete_group(db, principal, term_id, group_id)
    db.commit()


# ── activities ─────────────────────────────────────────────────────────


def _activity_out(details: ActivityDetails) -> s.ActivityOut:
    a = details.activity
    return s.ActivityOut(
        id=a.id,
        course_id=a.course_id,
        activity_type_id=a.activity_type_id,
        label=a.label,
        duration=a.duration,
        sessions_per_week=a.sessions_per_week,
        different_days=a.different_days,
        delivery_mode=a.delivery_mode,
        room_type_id=a.room_type_id,
        min_capacity=a.min_capacity,
        campus_id=a.campus_id,
        building_id=a.building_id,
        notes=a.notes,
        group_ids=details.group_ids,
        instructor_ids=details.instructor_ids,
        feature_ids=details.feature_ids,
        rooms=[s.ActivityRoomOut(room_id=r, kind=k) for r, k in details.rooms],
        fixed=[
            s.FixedOut(
                occurrence=f.occurrence, weekday=f.weekday, period_id=f.period_id, room_id=f.room_id
            )
            for f in details.fixed
        ],
        version=a.version,
    )


def _activity_values(body: s.ActivityIn | s.ActivityPatch) -> dict[str, object]:
    if isinstance(body, s.ActivityPatch):
        values = body.changes()
        present = body.model_fields_set
    else:
        values = body.model_dump()
        present = set(values)
    if "rooms" in present and body.rooms is not None:
        values["rooms"] = [(r.room_id, r.kind) for r in body.rooms]
    if "fixed" in present and body.fixed is not None:
        values["fixed"] = [
            FixedSpec(f.occurrence, f.weekday, f.period_id, f.room_id) for f in body.fixed
        ]
    return values


@router.get("/{term_id}/activities", response_model=list[s.ActivityOut])
def list_activities(
    term_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    department_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
    instructor_id: uuid.UUID | None = None,
) -> list[s.ActivityOut]:
    return [
        _activity_out(d)
        for d in activities.list_activities(
            db,
            principal,
            term_id,
            department_id=department_id,
            course_id=course_id,
            group_id=group_id,
            instructor_id=instructor_id,
        )
    ]


@router.post("/{term_id}/activities", response_model=s.ActivityOut, status_code=201)
def create_activity(
    term_id: uuid.UUID, body: s.ActivityIn, db: DbSession, principal: PrincipalDep
) -> s.ActivityOut:
    details = activities.create_activity(db, principal, term_id, _activity_values(body))
    db.commit()
    return _activity_out(details)


@router.get("/{term_id}/activities/{activity_id}", response_model=s.ActivityOut)
def get_activity(
    term_id: uuid.UUID, activity_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> s.ActivityOut:
    return _activity_out(activities.get_activity(db, principal, term_id, activity_id))


@router.patch("/{term_id}/activities/{activity_id}", response_model=s.ActivityOut)
def update_activity(
    term_id: uuid.UUID,
    activity_id: uuid.UUID,
    body: s.ActivityPatch,
    db: DbSession,
    principal: PrincipalDep,
) -> s.ActivityOut:
    details = activities.update_activity(
        db, principal, term_id, activity_id, version=body.version, values=_activity_values(body)
    )
    db.commit()
    return _activity_out(details)


@router.delete("/{term_id}/activities/{activity_id}", status_code=204)
def delete_activity(
    term_id: uuid.UUID, activity_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> None:
    activities.delete_activity(db, principal, term_id, activity_id)
    db.commit()


# ── availability ───────────────────────────────────────────────────────

Kind = Annotated[str, Path(pattern="^(instructor|group|room|activity)$")]


def _grid(grid: AvailabilityGrid | None, resource_id: uuid.UUID) -> s.GridOut:
    if grid is None:
        return s.GridOut(
            resource_id=resource_id, cells=[], source=None, version=None, updated_at=None
        )
    return s.GridOut(
        resource_id=resource_id,
        cells=[s.CellIn.model_validate(c) for c in grid.cells],
        source=grid.source,
        version=grid.version,
        updated_at=grid.updated_at,
    )


@router.get("/{term_id}/availability/{kind}", response_model=list[s.GridOut])
def list_availability(
    term_id: uuid.UUID, kind: Kind, db: DbSession, principal: PrincipalDep
) -> list[s.GridOut]:
    result = []
    for grid in availability.list_grids(db, principal, term_id, kind):
        resource_id = getattr(grid, f"{kind}_id")
        result.append(_grid(grid, resource_id))
    return result


@router.get("/{term_id}/availability/{kind}/{resource_id}", response_model=s.GridOut)
def get_availability(
    term_id: uuid.UUID, kind: Kind, resource_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> s.GridOut:
    return _grid(availability.get_grid(db, principal, term_id, kind, resource_id), resource_id)


@router.put("/{term_id}/availability/{kind}/{resource_id}", response_model=s.GridOut)
def put_availability(
    term_id: uuid.UUID,
    kind: Kind,
    resource_id: uuid.UUID,
    body: s.GridIn,
    db: DbSession,
    principal: PrincipalDep,
) -> s.GridOut:
    grid = availability.put_grid(
        db,
        principal,
        term_id,
        kind,
        resource_id,
        version=body.version,
        cells=[availability.Cell(c.weekday, c.period_id, c.state) for c in body.cells],
        today=date.today(),
    )
    db.commit()
    return _grid(grid, resource_id)


# ── rules and profiles ─────────────────────────────────────────────────


@router.get("/{term_id}/rules", response_model=list[s.RuleOut])
def list_rules(term_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> list[s.RuleOut]:
    return [s.RuleOut.model_validate(r) for r in rules.list_rules(db, principal, term_id)]


@router.post("/{term_id}/rules", response_model=s.RuleOut, status_code=201)
def create_rule(
    term_id: uuid.UUID, body: s.RuleIn, db: DbSession, principal: PrincipalDep
) -> s.RuleOut:
    rule = rules.create_rule(db, principal, term_id, body.model_dump())
    db.commit()
    db.refresh(rule)
    return s.RuleOut.model_validate(rule)


@router.patch("/{term_id}/rules/{rule_id}", response_model=s.RuleOut)
def update_rule(
    term_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: s.RulePatch,
    db: DbSession,
    principal: PrincipalDep,
) -> s.RuleOut:
    rule = rules.update_rule(
        db, principal, term_id, rule_id, version=body.version, values=body.changes()
    )
    db.commit()
    db.refresh(rule)
    return s.RuleOut.model_validate(rule)


@router.delete("/{term_id}/rules/{rule_id}", status_code=204)
def delete_rule(
    term_id: uuid.UUID, rule_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> None:
    rules.delete_rule(db, principal, term_id, rule_id)
    db.commit()


@router.get("/{term_id}/objective-profiles", response_model=list[s.ProfileOut])
def list_profiles(term_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> list[s.ProfileOut]:
    return [s.ProfileOut.model_validate(p) for p in rules.list_profiles(db, principal, term_id)]


@router.post("/{term_id}/objective-profiles", response_model=s.ProfileOut, status_code=201)
def create_profile(
    term_id: uuid.UUID, body: s.ProfileIn, db: DbSession, principal: PrincipalDep
) -> s.ProfileOut:
    profile = rules.create_profile(db, principal, term_id, body.model_dump())
    db.commit()
    db.refresh(profile)
    return s.ProfileOut.model_validate(profile)


@router.patch("/{term_id}/objective-profiles/{profile_id}", response_model=s.ProfileOut)
def update_profile(
    term_id: uuid.UUID,
    profile_id: uuid.UUID,
    body: s.ProfilePatch,
    db: DbSession,
    principal: PrincipalDep,
) -> s.ProfileOut:
    profile = rules.update_profile(
        db, principal, term_id, profile_id, version=body.version, values=body.changes()
    )
    db.commit()
    db.refresh(profile)
    return s.ProfileOut.model_validate(profile)


@router.delete("/{term_id}/objective-profiles/{profile_id}", status_code=204)
def delete_profile(
    term_id: uuid.UUID, profile_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> None:
    rules.delete_profile(db, principal, term_id, profile_id)
    db.commit()


@catalog_router.get("", response_model=s.CatalogOut)
def catalog(principal: PrincipalDep) -> s.CatalogOut:
    principal.require(Permission.TERM_DATA_READ)
    return s.CatalogOut(
        rules=[
            s.CatalogRuleOut(
                code=r.code,
                name=r.name,
                description=r.description,
                scope=r.scope.value,
                unit=r.unit,
                params_schema=r.params.model_json_schema(),
            )
            for r in RULE_TYPES.values()
        ],
        objectives=[
            s.CatalogObjectiveOut(code=o.code, name=o.name, description=o.description, unit=o.unit)
            for o in OBJECTIVES.values()
        ],
    )


def _issue(issue: Issue) -> IssueOut:
    return IssueOut(
        severity=issue.severity,
        code=issue.code,
        message=issue.message,
        entity_type=issue.entity_type,
        entity_ids=list(issue.entity_ids),
        figures=dict(issue.figures),
    )


@router.get("/{term_id}/validation", response_model=ValidationOut)
def validate_term(term_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> ValidationOut:
    """Data-quality checks and feasibility pre-checks on the term's current data."""
    report = validation_report.build_report(db, principal, term_id)
    return ValidationOut(
        snapshot_hash=report.snapshot_hash,
        counts=report.counts,
        errors=report.errors,
        warnings=report.warnings,
        data_issues=[_issue(i) for i in report.data_issues],
        feasibility_issues=[_issue(i) for i in report.feasibility_issues],
        elapsed_ms=report.elapsed_ms,
    )
