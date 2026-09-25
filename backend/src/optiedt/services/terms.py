"""Terms, their period grid, slot settings and timing variants."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, FieldError, InvalidInput, PermissionDenied
from optiedt.models import (
    Activity,
    AvailabilityGrid,
    Course,
    FixedPlacement,
    ObjectiveProfile,
    Period,
    Publication,
    SlotSetting,
    Term,
    TimingVariant,
    TimingVariantPeriod,
)
from optiedt.problem.catalog import BUILT_IN_PROFILES
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import apply_changes, check_version, get_or_404, page

MAX_PERIODS = 24
TERM_STATUSES = ("planning", "active", "closed")


@dataclass(frozen=True, slots=True)
class PeriodSpec:
    label: str
    start_time: time
    end_time: time
    joins_next: bool = True
    id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class SlotSpec:
    weekday: int
    period_index: int
    is_closed: bool = False
    closed_reason: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    penalty: int = 0


def _validate_weekdays(weekdays: Sequence[int]) -> list[int]:
    if not weekdays:
        raise InvalidInput("Choose at least one teaching day.", [FieldError("weekdays", "Empty.")])
    if len(set(weekdays)) != len(weekdays) or any(d < 0 or d > 6 for d in weekdays):
        raise InvalidInput(
            "Teaching days must be distinct values from 0 (Monday) to 6 (Sunday).",
            [FieldError("weekdays", "Invalid.")],
        )
    return list(weekdays)


def _validate_periods(periods: Sequence[PeriodSpec]) -> None:
    errors = []
    if not periods:
        errors.append(FieldError("periods", "Define at least one period."))
    if len(periods) > MAX_PERIODS:
        errors.append(FieldError("periods", f"At most {MAX_PERIODS} periods per day."))
    labels = [p.label.strip() for p in periods]
    if any(not label for label in labels):
        errors.append(FieldError("periods", "Every period needs a label."))
    if len(set(labels)) != len(labels):
        errors.append(FieldError("periods", "Period labels must be unique."))
    for index, period in enumerate(periods):
        if period.end_time <= period.start_time:
            errors.append(FieldError(f"periods.{index}.end_time", "Must be after the start."))
        if index and period.start_time < periods[index - 1].end_time:
            errors.append(
                FieldError(
                    f"periods.{index}.start_time",
                    "Periods must be in chronological order without overlapping.",
                )
            )
    if errors:
        raise InvalidInput("The period grid is invalid.", errors)


def _validate_dates(start: date, end: date) -> None:
    if end <= start:
        raise InvalidInput(
            "The term must end after it starts.", [FieldError("end_date", "Before start.")]
        )


def _seed_profiles(db: Session, term: Term) -> None:
    for position, (code, name, description, objectives) in enumerate(BUILT_IN_PROFILES):
        db.add(
            ObjectiveProfile(
                term_id=term.id,
                code=code,
                name=name,
                description=description,
                objectives=objectives,
                position=position,
            )
        )


def create_term(
    db: Session,
    principal: Principal,
    *,
    code: str,
    name: str,
    academic_year: str,
    start_date: date,
    end_date: date,
    weekdays: Sequence[int],
    periods: Sequence[PeriodSpec],
    availability_open_until: date | None = None,
    room_capacity_ratio: float = 4.0,
) -> Term:
    principal.require_everywhere(Permission.TERMS_MANAGE)
    _validate_dates(start_date, end_date)
    weekdays = _validate_weekdays(weekdays)
    _validate_periods(periods)
    if db.scalar(select(Term.id).where(Term.code == code)) is not None:
        raise Conflict("A term with this code already exists.", code="duplicate")
    term = Term(
        code=code,
        name=name,
        academic_year=academic_year,
        start_date=start_date,
        end_date=end_date,
        weekdays=weekdays,
        availability_open_until=availability_open_until,
        room_capacity_ratio=room_capacity_ratio,
        status="planning",
    )
    db.add(term)
    db.flush()
    for position, spec in enumerate(periods):
        db.add(
            Period(
                term_id=term.id,
                position=position,
                label=spec.label.strip(),
                start_time=spec.start_time,
                end_time=spec.end_time,
                joins_next=spec.joins_next and position < len(periods) - 1,
            )
        )
    _seed_profiles(db, term)
    db.flush()
    audit.record(
        db,
        principal,
        action="term.create",
        entity_type="term",
        entity_id=term.id,
        term_id=term.id,
        summary=f"Created term {code} ({name})",
    )
    return term


def update_term(
    db: Session, principal: Principal, term_id: uuid.UUID, *, version: int, values: dict[str, Any]
) -> Term:
    principal.require_everywhere(Permission.TERMS_MANAGE)
    term = get_or_404(db, Term, term_id, "Term")
    check_version(term, version, "term")
    start = values.get("start_date", term.start_date)
    end = values.get("end_date", term.end_date)
    _validate_dates(start, end)
    if "status" in values and values["status"] not in TERM_STATUSES:
        raise InvalidInput("Unknown status.", [FieldError("status", "Invalid.")])
    changes = apply_changes(term, values)
    db.flush()
    if changes:
        audit.record(
            db,
            principal,
            action="term.update",
            entity_type="term",
            entity_id=term.id,
            term_id=term.id,
            summary=f"Updated term {term.code}",
            changes=changes,
        )
    return term


def delete_term(db: Session, principal: Principal, term_id: uuid.UUID) -> None:
    principal.require_everywhere(Permission.TERMS_MANAGE)
    term = get_or_404(db, Term, term_id, "Term")
    if db.scalar(select(Publication.id).where(Publication.term_id == term.id).limit(1)):
        raise Conflict(
            "A term with published timetables cannot be deleted; close it instead.",
            code="in_use",
        )
    code = term.code
    db.delete(term)
    db.flush()
    audit.record(
        db,
        principal,
        action="term.delete",
        entity_type="term",
        entity_id=term_id,
        summary=f"Deleted term {code}",
    )


def require_term_read(principal: Principal) -> None:
    """Every signed-in role that sees any timetable may see the list of terms."""
    if not (
        principal.can(Permission.TERM_DATA_READ)
        or principal.can(Permission.PORTAL_SELF)
        or principal.can(Permission.PUBLICATIONS_READ)
    ):
        raise PermissionDenied()


def list_terms(
    db: Session, principal: Principal, *, offset: int, limit: int
) -> tuple[Sequence[Term], int]:
    require_term_read(principal)
    statement = select(Term).order_by(Term.start_date.desc())
    return page(db, statement, offset=offset, limit=limit)


def get_term(db: Session, term_id: uuid.UUID) -> Term:
    return get_or_404(db, Term, term_id, "Term")


# ── time grid ──────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TimeGrid:
    term: Term
    periods: list[Period]
    slots: list[SlotSetting]


def get_time_grid(db: Session, term_id: uuid.UUID) -> TimeGrid:
    term = get_term(db, term_id)
    periods = list(
        db.scalars(select(Period).where(Period.term_id == term_id).order_by(Period.position))
    )
    slots = list(
        db.scalars(
            select(SlotSetting)
            .where(SlotSetting.term_id == term_id)
            .order_by(SlotSetting.weekday, SlotSetting.period_id)
        )
    )
    return TimeGrid(term=term, periods=periods, slots=slots)


def put_time_grid(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    *,
    version: int,
    weekdays: Sequence[int],
    periods: Sequence[PeriodSpec],
    slots: Sequence[SlotSpec],
) -> TimeGrid:
    """Replace the grid. Existing periods keep their identity when submitted with their id."""
    principal.require_everywhere(Permission.TERMS_MANAGE)
    term = get_term(db, term_id)
    check_version(term, version, "term")
    weekdays = _validate_weekdays(weekdays)
    _validate_periods(periods)

    existing = {p.id: p for p in db.scalars(select(Period).where(Period.term_id == term_id))}
    submitted_ids = {p.id for p in periods if p.id is not None}
    unknown = submitted_ids - set(existing)
    if unknown:
        raise InvalidInput(
            "A submitted period does not belong to this term.",
            [FieldError("periods", "Unknown period id.")],
        )
    removed_periods = set(existing) - submitted_ids
    removed_weekdays = set(term.weekdays) - set(weekdays)
    _refuse_orphaned_fixed_placements(db, term_id, removed_periods, removed_weekdays)

    slot_errors = []
    for index, slot in enumerate(slots):
        if slot.weekday not in weekdays:
            slot_errors.append(FieldError(f"slots.{index}.weekday", "Not a teaching day."))
        if not 0 <= slot.period_index < len(periods):
            slot_errors.append(FieldError(f"slots.{index}.period_index", "No such period."))
        if (slot.start_time is None) != (slot.end_time is None):
            slot_errors.append(FieldError(f"slots.{index}", "Give both start and end times."))
        elif slot.start_time and slot.end_time and slot.end_time <= slot.start_time:
            slot_errors.append(FieldError(f"slots.{index}.end_time", "Must be after the start."))
        if not 0 <= slot.penalty <= 3:
            slot_errors.append(FieldError(f"slots.{index}.penalty", "Between 0 and 3."))
    if slot_errors:
        raise InvalidInput("Some slot settings are invalid.", slot_errors)

    # Positions are unique per term: move every kept period out of the way first.
    for offset, period in enumerate(existing.values()):
        period.position = MAX_PERIODS * 4 + offset
    db.flush()
    for removed in removed_periods:
        db.delete(existing[removed])
    db.flush()

    final: list[Period] = []
    for position, spec in enumerate(periods):
        if spec.id is not None:
            period = existing[spec.id]
        else:
            period = Period(term_id=term_id)
            db.add(period)
        period.position = position
        period.label = spec.label.strip()
        period.start_time = spec.start_time
        period.end_time = spec.end_time
        period.joins_next = spec.joins_next and position < len(periods) - 1
        final.append(period)
    db.flush()

    db.execute(delete(SlotSetting).where(SlotSetting.term_id == term_id))
    for slot in slots:
        if not (slot.is_closed or slot.start_time or slot.penalty):
            continue
        db.add(
            SlotSetting(
                term_id=term_id,
                weekday=slot.weekday,
                period_id=final[slot.period_index].id,
                is_closed=slot.is_closed,
                closed_reason=(slot.closed_reason or "").strip() or None,
                start_time=slot.start_time,
                end_time=slot.end_time,
                penalty=slot.penalty,
            )
        )

    before_days = list(term.weekdays)
    term.weekdays = weekdays
    term.updated_at = datetime.now(UTC)
    _prune_availability_cells(db, term_id, {p.id for p in final}, set(weekdays))
    db.flush()
    audit.record(
        db,
        principal,
        action="term.time_grid",
        entity_type="term",
        entity_id=term.id,
        term_id=term.id,
        summary=f"Updated the time grid of {term.code}",
        changes={
            "weekdays": [before_days, weekdays],
            "periods": [len(existing), len(final)],
            "slot_settings": [
                None,
                len([s for s in slots if s.is_closed or s.start_time or s.penalty]),
            ],
        },
    )
    return get_time_grid(db, term_id)


def _refuse_orphaned_fixed_placements(
    db: Session, term_id: uuid.UUID, periods: set[uuid.UUID], weekdays: set[int]
) -> None:
    if not periods and not weekdays:
        return
    conditions = []
    if periods:
        conditions.append(FixedPlacement.period_id.in_(periods))
    if weekdays:
        conditions.append(FixedPlacement.weekday.in_(weekdays))
    affected = db.execute(
        select(Course.code, FixedPlacement.occurrence)
        .join(Activity, Activity.id == FixedPlacement.activity_id)
        .join(Course, Course.id == Activity.course_id)
        .where(Activity.term_id == term_id, or_(*conditions))
        .limit(10)
    ).all()
    if affected:
        listed = ", ".join(f"{code} (occurrence {occ})" for code, occ in affected)
        raise Conflict(
            "Removing these periods or days would drop fixed placements of: "
            f"{listed}. Change those placements first.",
            code="in_use",
        )


def _prune_availability_cells(
    db: Session, term_id: uuid.UUID, period_ids: set[uuid.UUID], weekdays: set[int]
) -> None:
    valid_periods = {str(p) for p in period_ids}
    for grid in db.scalars(select(AvailabilityGrid).where(AvailabilityGrid.term_id == term_id)):
        kept = [
            cell
            for cell in grid.cells
            if cell.get("period_id") in valid_periods and cell.get("weekday") in weekdays
        ]
        if len(kept) != len(grid.cells):
            grid.cells = kept


# ── timing variants ────────────────────────────────────────────────────


def put_timing_variant(
    db: Session,
    principal: Principal,
    term_id: uuid.UUID,
    *,
    variant_id: uuid.UUID | None,
    version: int | None,
    name: str,
    start_date: date,
    end_date: date,
    periods: Sequence[tuple[uuid.UUID, time, time]],
) -> TimingVariant:
    principal.require_everywhere(Permission.TERMS_MANAGE)
    term = get_term(db, term_id)
    errors = []
    if end_date < start_date:
        errors.append(FieldError("end_date", "Must be on or after the start date."))
    if start_date < term.start_date or end_date > term.end_date:
        errors.append(FieldError("start_date", "The variant must lie within the term."))
    term_periods = set(db.scalars(select(Period.id).where(Period.term_id == term_id)))
    for index, (period_id, start, end) in enumerate(periods):
        if period_id not in term_periods:
            errors.append(FieldError(f"periods.{index}.period_id", "Not a period of this term."))
        if end <= start:
            errors.append(FieldError(f"periods.{index}.end_time", "Must be after the start."))
    if len({p[0] for p in periods}) != len(periods):
        errors.append(FieldError("periods", "A period appears twice."))
    if errors:
        raise InvalidInput("The timing variant is invalid.", errors)

    if variant_id is None:
        variant = TimingVariant(
            term_id=term_id, name=name, start_date=start_date, end_date=end_date
        )
        db.add(variant)
        action = "timing_variant.create"
    else:
        variant = get_or_404(db, TimingVariant, variant_id, "Timing variant")
        if variant.term_id != term_id:
            raise InvalidInput("The variant belongs to another term.")
        check_version(variant, version or 0, "timing variant")
        variant.name, variant.start_date, variant.end_date = name, start_date, end_date
        variant.updated_at = datetime.now(UTC)
        action = "timing_variant.update"
    variant.periods = [
        TimingVariantPeriod(period_id=p, start_time=s, end_time=e) for p, s, e in periods
    ]
    db.flush()
    audit.record(
        db,
        principal,
        action=action,
        entity_type="timing_variant",
        entity_id=variant.id,
        term_id=term_id,
        summary=f"Saved timing variant {name} ({start_date} to {end_date})",
    )
    return variant


def delete_timing_variant(
    db: Session, principal: Principal, term_id: uuid.UUID, variant_id: uuid.UUID
) -> None:
    principal.require_everywhere(Permission.TERMS_MANAGE)
    variant = get_or_404(db, TimingVariant, variant_id, "Timing variant")
    if variant.term_id != term_id:
        raise InvalidInput("The variant belongs to another term.")
    name = variant.name
    db.delete(variant)
    db.flush()
    audit.record(
        db,
        principal,
        action="timing_variant.delete",
        entity_type="timing_variant",
        entity_id=variant_id,
        term_id=term_id,
        summary=f"Deleted timing variant {name}",
    )


def list_timing_variants(db: Session, term_id: uuid.UUID) -> list[TimingVariant]:
    return list(
        db.scalars(
            select(TimingVariant)
            .where(TimingVariant.term_id == term_id)
            .order_by(TimingVariant.start_date)
        )
    )
