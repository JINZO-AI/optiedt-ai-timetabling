"""Request and response bodies for term data."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Annotated, Any, ClassVar, Literal

from pydantic import Field, field_validator

from optiedt.api.schemas.common import Code, LongText, Name, Out, Patch, Schema

Weekday = Annotated[int, Field(ge=0, le=6)]


# ── terms ──────────────────────────────────────────────────────────────


class PeriodIn(Schema):
    id: uuid.UUID | None = None
    label: Annotated[str, Field(min_length=1, max_length=32)]
    start_time: time
    end_time: time
    joins_next: bool = True


class TermIn(Schema):
    code: Code
    name: Name
    academic_year: Annotated[str, Field(min_length=4, max_length=16)]
    start_date: date
    end_date: date
    weekdays: Annotated[list[Weekday], Field(min_length=1, max_length=7)]
    periods: Annotated[list[PeriodIn], Field(min_length=1, max_length=24)]
    availability_open_until: date | None = None
    room_capacity_ratio: Annotated[float, Field(ge=1.0, le=100.0)] = 4.0


class TermPatch(Patch):
    required_fields: ClassVar[frozenset[str]] = frozenset(
        {"code", "name", "academic_year", "start_date", "end_date", "status", "room_capacity_ratio"}
    )
    code: Code | None = None
    name: Name | None = None
    academic_year: Annotated[str, Field(min_length=4, max_length=16)] | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: Literal["planning", "active", "closed"] | None = None
    availability_open_until: date | None = None
    room_capacity_ratio: Annotated[float, Field(ge=1.0, le=100.0)] | None = None


class TermOut(Out):
    id: uuid.UUID
    code: str
    name: str
    academic_year: str
    start_date: date
    end_date: date
    status: str
    weekdays: list[int]
    availability_open_until: date | None
    room_capacity_ratio: float
    version: int
    updated_at: datetime


class PeriodOut(Out):
    id: uuid.UUID
    position: int
    label: str
    start_time: time
    end_time: time
    joins_next: bool


class SlotIn(Schema):
    weekday: Weekday
    period_index: Annotated[int, Field(ge=0, le=23)]
    is_closed: bool = False
    closed_reason: Annotated[str, Field(max_length=200)] | None = None
    start_time: time | None = None
    end_time: time | None = None
    penalty: Annotated[int, Field(ge=0, le=3)] = 0


class SlotOut(Out):
    weekday: int
    period_id: uuid.UUID
    is_closed: bool
    closed_reason: str | None
    start_time: time | None
    end_time: time | None
    penalty: int


class TimeGridIn(Schema):
    version: int
    weekdays: Annotated[list[Weekday], Field(min_length=1, max_length=7)]
    periods: Annotated[list[PeriodIn], Field(min_length=1, max_length=24)]
    slots: Annotated[list[SlotIn], Field(max_length=7 * 24)] = []


class TimeGridOut(Schema):
    term_version: int
    weekdays: list[int]
    periods: list[PeriodOut]
    slots: list[SlotOut]


class VariantPeriodIn(Schema):
    period_id: uuid.UUID
    start_time: time
    end_time: time


class TimingVariantIn(Schema):
    version: int | None = None
    name: Name
    start_date: date
    end_date: date
    periods: Annotated[list[VariantPeriodIn], Field(min_length=1, max_length=24)]


class VariantPeriodOut(Out):
    period_id: uuid.UUID
    start_time: time
    end_time: time


class TimingVariantOut(Out):
    id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    periods: list[VariantPeriodOut]
    version: int


# ── groups ─────────────────────────────────────────────────────────────


class GroupIn(Schema):
    code: Annotated[str, Field(min_length=1, max_length=48, pattern=r"^\S+$")]
    name: Name
    parent_id: uuid.UUID | None = None
    partition_key: Annotated[str, Field(min_length=1, max_length=32)] = "default"
    size: Annotated[int, Field(ge=0, le=100_000)]
    programme_id: uuid.UUID | None = None
    notes: LongText | None = None


class GroupPatch(Patch):
    required_fields: ClassVar[frozenset[str]] = frozenset({"code", "name", "partition_key", "size"})
    code: Annotated[str, Field(min_length=1, max_length=48, pattern=r"^\S+$")] | None = None
    name: Name | None = None
    parent_id: uuid.UUID | None = None
    partition_key: Annotated[str, Field(min_length=1, max_length=32)] | None = None
    size: Annotated[int, Field(ge=0, le=100_000)] | None = None
    programme_id: uuid.UUID | None = None
    notes: LongText | None = None


class GroupOut(Out):
    id: uuid.UUID
    code: str
    name: str
    parent_id: uuid.UUID | None
    partition_key: str
    size: int
    programme_id: uuid.UUID | None
    notes: str | None
    version: int


class GroupListOut(Schema):
    items: list[GroupOut]
    warnings: list[str]


# ── activities ─────────────────────────────────────────────────────────


class ActivityRoomIn(Schema):
    room_id: uuid.UUID
    kind: Literal["allowed", "preferred", "avoided"]


class FixedIn(Schema):
    occurrence: Annotated[int, Field(ge=1, le=7)]
    weekday: Weekday
    period_id: uuid.UUID
    room_id: uuid.UUID | None = None


class ActivityIn(Schema):
    course_id: uuid.UUID
    activity_type_id: uuid.UUID
    label: Annotated[str, Field(max_length=120)] | None = None
    duration: Annotated[int, Field(ge=1, le=12)] = 1
    sessions_per_week: Annotated[int, Field(ge=1, le=7)] = 1
    different_days: bool = True
    delivery_mode: Literal["in_person", "online"] = "in_person"
    room_type_id: uuid.UUID | None = None
    min_capacity: Annotated[int, Field(ge=1, le=100_000)] | None = None
    campus_id: uuid.UUID | None = None
    building_id: uuid.UUID | None = None
    notes: LongText | None = None
    group_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=100)]
    instructor_ids: Annotated[list[uuid.UUID], Field(max_length=20)] = []
    feature_ids: Annotated[list[uuid.UUID], Field(max_length=50)] = []
    rooms: Annotated[list[ActivityRoomIn], Field(max_length=200)] = []
    fixed: Annotated[list[FixedIn], Field(max_length=7)] = []


class ActivityPatch(Patch):
    required_fields: ClassVar[frozenset[str]] = frozenset(
        {
            "course_id",
            "activity_type_id",
            "duration",
            "sessions_per_week",
            "different_days",
            "delivery_mode",
            "group_ids",
            "instructor_ids",
            "feature_ids",
            "rooms",
            "fixed",
        }
    )
    course_id: uuid.UUID | None = None
    activity_type_id: uuid.UUID | None = None
    label: Annotated[str, Field(max_length=120)] | None = None
    duration: Annotated[int, Field(ge=1, le=12)] | None = None
    sessions_per_week: Annotated[int, Field(ge=1, le=7)] | None = None
    different_days: bool | None = None
    delivery_mode: Literal["in_person", "online"] | None = None
    room_type_id: uuid.UUID | None = None
    min_capacity: Annotated[int, Field(ge=1, le=100_000)] | None = None
    campus_id: uuid.UUID | None = None
    building_id: uuid.UUID | None = None
    notes: LongText | None = None
    group_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=100)] | None = None
    instructor_ids: Annotated[list[uuid.UUID], Field(max_length=20)] | None = None
    feature_ids: Annotated[list[uuid.UUID], Field(max_length=50)] | None = None
    rooms: Annotated[list[ActivityRoomIn], Field(max_length=200)] | None = None
    fixed: Annotated[list[FixedIn], Field(max_length=7)] | None = None


class ActivityRoomOut(Schema):
    room_id: uuid.UUID
    kind: str


class FixedOut(Schema):
    occurrence: int
    weekday: int
    period_id: uuid.UUID
    room_id: uuid.UUID | None


class ActivityOut(Schema):
    id: uuid.UUID
    course_id: uuid.UUID
    activity_type_id: uuid.UUID
    label: str | None
    duration: int
    sessions_per_week: int
    different_days: bool
    delivery_mode: str
    room_type_id: uuid.UUID | None
    min_capacity: int | None
    campus_id: uuid.UUID | None
    building_id: uuid.UUID | None
    notes: str | None
    group_ids: list[uuid.UUID]
    instructor_ids: list[uuid.UUID]
    feature_ids: list[uuid.UUID]
    rooms: list[ActivityRoomOut]
    fixed: list[FixedOut]
    version: int


# ── availability ───────────────────────────────────────────────────────


class CellIn(Schema):
    weekday: Weekday
    period_id: uuid.UUID
    state: Literal["preferred", "undesirable", "unavailable"]


class GridIn(Schema):
    version: int | None = None
    cells: Annotated[list[CellIn], Field(max_length=7 * 24)]


class GridOut(Schema):
    resource_id: uuid.UUID
    cells: list[CellIn]
    source: str | None
    version: int | None
    updated_at: datetime | None


# ── rules and profiles ─────────────────────────────────────────────────


class RuleIn(Schema):
    rule_type: str
    name: Annotated[str, Field(max_length=200)] | None = None
    enforcement: Literal["hard", "soft"] = "hard"
    tier: Annotated[int, Field(ge=1, le=5)] = 2
    weight: Annotated[int, Field(ge=1, le=1000)] = 1
    params: dict[str, Any] = {}
    scope: dict[str, Any] = {}
    is_enabled: bool = True
    notes: LongText | None = None


class RulePatch(Patch):
    required_fields: ClassVar[frozenset[str]] = frozenset(
        {"rule_type", "name", "enforcement", "tier", "weight", "params", "scope", "is_enabled"}
    )
    rule_type: str | None = None
    name: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    enforcement: Literal["hard", "soft"] | None = None
    tier: Annotated[int, Field(ge=1, le=5)] | None = None
    weight: Annotated[int, Field(ge=1, le=1000)] | None = None
    params: dict[str, Any] | None = None
    scope: dict[str, Any] | None = None
    is_enabled: bool | None = None
    notes: LongText | None = None


class RuleOut(Out):
    id: uuid.UUID
    rule_type: str
    name: str
    enforcement: str
    tier: int
    weight: int
    params: dict[str, Any]
    scope: dict[str, Any]
    is_enabled: bool
    notes: str | None
    version: int


class ProfileIn(Schema):
    code: Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_]+$")]
    name: Name
    description: LongText | None = None
    objectives: dict[str, dict[str, Any]]
    position: Annotated[int, Field(ge=0, le=1000)] = 100


class ProfilePatch(Patch):
    required_fields: ClassVar[frozenset[str]] = frozenset({"name", "objectives", "position"})
    name: Name | None = None
    description: LongText | None = None
    objectives: dict[str, dict[str, Any]] | None = None
    position: Annotated[int, Field(ge=0, le=1000)] | None = None


class ProfileOut(Out):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    objectives: dict[str, Any]
    position: int
    version: int


class CatalogRuleOut(Schema):
    code: str
    name: str
    description: str
    scope: str
    unit: str
    params_schema: dict[str, Any]


class CatalogObjectiveOut(Schema):
    code: str
    name: str
    description: str
    unit: str


class CatalogOut(Schema):
    rules: list[CatalogRuleOut]
    objectives: list[CatalogObjectiveOut]


class CopyTermIn(Schema):
    source_term_id: uuid.UUID
    include: Annotated[
        list[Literal["groups", "activities", "availability", "rules", "profiles"]],
        Field(min_length=1),
    ]

    @field_validator("include")
    @classmethod
    def _activities_need_groups(cls, value: list[str]) -> list[str]:
        if "activities" in value and "groups" not in value:
            raise ValueError("copying activities requires copying groups")
        return value


class CopyTermOut(Schema):
    copied: dict[str, int]
    skipped: list[str]
