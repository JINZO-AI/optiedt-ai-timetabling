"""Request and response shapes of the REST surface.

These are the wire format, deliberately separate from `optiedt.domain`. The
domain layer is pure and must stay free of framework imports (.importlinter
forbids `domain -> fastapi`), so it cannot carry Pydantic models itself; and a
wire format that IS the domain model cannot be evolved without changing the
domain.

Two rules the frontend depends on:

1. **Field names are camelCase on the wire**, matching
   `frontend/src/types/domain.ts`. The alias generator does this once here
   rather than each model spelling it out.

2. **Enum values are the French literals**, unchanged: `Amphi`, `Salle`,
   `Lab_Info`, `Lab_Sciences`, `CM`, `TD`, `TP`, `PROMO`. They are the literals
   in the instance CSVs (CLAUDE.md, "Conventions"), and translating them at the
   API boundary would create the mapping layer the project exists without.
   `StrEnum` gives this for free, and `tests/unit/test_api_schemas.py` pins it
   so a later "tidy-up" cannot quietly anglicise the wire format.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from optiedt.domain.entities import (
    Availability,
    ConstraintDefinition,
    Course,
    Group,
    Programme,
    Promotion,
    Room,
    Session,
    Slot,
    Teacher,
)
from optiedt.domain.enums import (
    AvailabilityState,
    ConstraintKind,
    DeclarationSource,
    GroupLevel,
    RoomType,
    SessionType,
    TeacherRank,
)
from optiedt.domain.instance import Instance


class ApiModel(BaseModel):
    """Base for every wire model: camelCase aliases, immutable."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


# ── Structure of the teaching ──────────────────────────────────────────


class ProgrammeOut(ApiModel):
    id: str
    code: str
    label: str
    degree_cycle: str
    department: str

    @classmethod
    def of(cls, p: Programme) -> ProgrammeOut:
        return cls(
            id=p.id,
            code=p.code,
            label=p.label,
            degree_cycle=p.degree_cycle,
            department=p.department,
        )


class PromotionOut(ApiModel):
    id: str
    programme: str
    level: str
    academic_year: str
    student_count: int

    @classmethod
    def of(cls, p: Promotion) -> PromotionOut:
        return cls(
            id=p.id,
            programme=p.programme,
            level=p.level,
            academic_year=p.academic_year,
            student_count=p.student_count,
        )


class GroupOut(ApiModel):
    id: str
    promotion: str
    parent_group: str | None
    level: GroupLevel
    label: str
    size: int

    @classmethod
    def of(cls, g: Group) -> GroupOut:
        return cls(
            id=g.id,
            promotion=g.promotion,
            parent_group=g.parent_group,
            level=g.level,
            label=g.label,
            size=g.size,
        )


class TeacherOut(ApiModel):
    id: str
    department: str
    rank: TeacherRank
    max_hours_per_week: int

    @classmethod
    def of(cls, t: Teacher) -> TeacherOut:
        return cls(
            id=t.id,
            department=t.department,
            rank=t.rank,
            max_hours_per_week=t.max_hours_per_week,
        )


class CourseOut(ApiModel):
    id: str
    code: str
    department: str
    programme: str
    level: str
    semester: int
    credits: int

    @classmethod
    def of(cls, c: Course) -> CourseOut:
        return cls(
            id=c.id,
            code=c.code,
            department=c.department,
            programme=c.programme,
            level=c.level,
            semester=c.semester,
            credits=c.credits,
        )


class SessionOut(ApiModel):
    id: str
    course: str
    group: str
    teacher: str
    type: SessionType
    duration_periods: int
    occurrences_per_week: int
    required_room_type: RoomType
    locked: bool

    @classmethod
    def of(cls, s: Session) -> SessionOut:
        return cls(
            id=s.id,
            course=s.course,
            group=s.group,
            teacher=s.teacher,
            type=s.type,
            duration_periods=s.duration_periods,
            occurrences_per_week=s.occurrences_per_week,
            required_room_type=s.required_room_type,
            locked=s.locked,
        )


class RoomOut(ApiModel):
    id: str
    building: str
    code: str
    capacity: int
    type: RoomType
    equipment: list[str]

    @classmethod
    def of(cls, r: Room) -> RoomOut:
        return cls(
            id=r.id,
            building=r.building,
            code=r.code,
            capacity=r.capacity,
            type=r.type,
            equipment=list(r.equipment),
        )


# ── Time and calendar ──────────────────────────────────────────────────


class SlotOut(ApiModel):
    """One cell of the weekly grid.

    Hours are rendered "HH:MM" rather than as ISO times: they are displayed,
    never computed with. `is_open` is driven by the calendar configuration and
    H9 (ADR-003) — the interface reads it and must never special-case a closed
    day of its own accord, which is invariant 7.
    """

    index: int
    day_index: int
    period_index: int
    start_hour: str
    end_hour: str
    is_open: bool

    @classmethod
    def of(cls, s: Slot) -> SlotOut:
        return cls(
            index=s.index,
            day_index=s.day_index,
            period_index=s.period_index,
            start_hour=s.start_hour.strftime("%H:%M"),
            end_hour=s.end_hour.strftime("%H:%M"),
            is_open=s.is_open,
        )


class AvailabilityOut(ApiModel):
    """A declaration. `source` distinguishes a generated row from a real one.

    That distinction is a requirement, not a convenience (docs/domain-model.md):
    generated declarations exist only so the instance is solvable before any
    teacher has connected, and the grid must be able to show which is which.
    """

    teacher: str
    slot: int
    state: AvailabilityState
    semester: int
    source: DeclarationSource

    @classmethod
    def of(cls, a: Availability) -> AvailabilityOut:
        return cls(
            teacher=a.teacher,
            slot=a.slot,
            state=a.state,
            semester=a.semester,
            source=a.source,
        )


class ConstraintOut(ApiModel):
    code: str
    name: str
    kind: ConstraintKind
    default_weight: float
    xhstt_reference: str | None

    @classmethod
    def of(cls, c: ConstraintDefinition) -> ConstraintOut:
        return cls(
            code=c.code,
            name=c.name,
            kind=c.kind,
            default_weight=c.default_weight,
            xhstt_reference=c.xhstt_reference,
        )


# ── The instance as one payload ────────────────────────────────────────


class InstanceOut(ApiModel):
    """Everything a screen needs to render placements and the grid.

    Sent whole rather than paged: the reference instance is 218 sessions, 51
    groups, 44 teachers, 20 rooms and 30 slots, so the payload is small and one
    request removes a class of loading states from every screen.
    """

    programmes: list[ProgrammeOut]
    promotions: list[PromotionOut]
    groups: list[GroupOut]
    teachers: list[TeacherOut]
    courses: list[CourseOut]
    sessions: list[SessionOut]
    rooms: list[RoomOut]
    slots: list[SlotOut]
    constraints: list[ConstraintOut]
    calendar_config: dict[str, str]

    @classmethod
    def of(cls, instance: Instance) -> InstanceOut:
        return cls(
            programmes=[ProgrammeOut.of(p) for p in instance.programmes],
            promotions=[PromotionOut.of(p) for p in instance.promotions],
            groups=[GroupOut.of(g) for g in instance.groups],
            teachers=[TeacherOut.of(t) for t in instance.teachers],
            courses=[CourseOut.of(c) for c in instance.courses],
            sessions=[SessionOut.of(s) for s in instance.sessions],
            rooms=[RoomOut.of(r) for r in instance.rooms],
            slots=[SlotOut.of(s) for s in instance.slots],
            constraints=[ConstraintOut.of(c) for c in instance.constraints],
            calendar_config=dict(instance.calendar_config),
        )


# ── Availability declaration ───────────────────────────────────────────


class AvailabilityCellIn(ApiModel):
    """One cell the teacher marked. Only non-AVAILABLE cells need be sent.

    ⚠️ `state` admits PREFERRED because the enum does, but the instance schema
    carries no representation for it (C-12): `teacher_availability.csv` has a
    boolean. Whether the grid offers two states or three is an open decision
    for Phase 4 — see C-12 in docs/open-questions.md. The wire format is left
    able to express three so that resolving it does not become an API change.
    """

    slot: int
    state: AvailabilityState


class AvailabilityIn(ApiModel):
    semester: int
    cells: list[AvailabilityCellIn]
