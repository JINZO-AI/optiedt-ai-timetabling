"""Request and response bodies for reference data."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import EmailStr, Field, model_validator

from optiedt.api.schemas.common import Code, LongText, Name, Out, Patch, Schema

Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Locale = Literal["en", "fr", "ar"]


# ── institution ────────────────────────────────────────────────────────


class InstitutionOut(Out):
    name: str
    short_name: str
    country_code: str | None
    timezone: str
    default_locale: str
    enabled_locales: list[str]
    week_start: int
    date_format: str
    time_format: str
    public_timetable_enabled: bool
    approval_required: bool
    assistant_enabled: bool
    version: int


class InstitutionPatch(Patch):
    required_fields = frozenset(
        {"name", "short_name", "timezone", "default_locale", "enabled_locales", "week_start"}
    )
    name: Name | None = None
    short_name: Annotated[str, Field(min_length=1, max_length=40)] | None = None
    country_code: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None
    timezone: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    default_locale: Locale | None = None
    enabled_locales: Annotated[list[Locale], Field(min_length=1, max_length=3)] | None = None
    week_start: Annotated[int, Field(ge=0, le=6)] | None = None
    date_format: Literal["dd/MM/yyyy", "MM/dd/yyyy", "yyyy-MM-dd", "dd.MM.yyyy"] | None = None
    time_format: Literal["HH:mm", "h:mm a"] | None = None
    public_timetable_enabled: bool | None = None
    approval_required: bool | None = None
    assistant_enabled: bool | None = None

    @model_validator(mode="after")
    def _valid_timezone(self) -> InstitutionPatch:
        if self.timezone is not None:
            from zoneinfo import available_timezones

            if self.timezone not in available_timezones():
                raise ValueError(f"unknown time zone {self.timezone!r}")
        return self


# ── departments ────────────────────────────────────────────────────────


class DepartmentIn(Schema):
    code: Code
    name: Name
    parent_id: uuid.UUID | None = None
    is_active: bool = True


class DepartmentPatch(Patch):
    required_fields = frozenset({"code", "name", "is_active"})
    code: Code | None = None
    name: Name | None = None
    parent_id: uuid.UUID | None = None
    is_active: bool | None = None


class DepartmentOut(Out):
    id: uuid.UUID
    code: str
    name: str
    parent_id: uuid.UUID | None
    is_active: bool
    version: int


# ── campuses and buildings ─────────────────────────────────────────────


class CampusIn(Schema):
    code: Code
    name: Name
    address: LongText | None = None
    is_active: bool = True


class CampusPatch(Patch):
    required_fields = frozenset({"code", "name", "is_active"})
    code: Code | None = None
    name: Name | None = None
    address: LongText | None = None
    is_active: bool | None = None


class CampusOut(Out):
    id: uuid.UUID
    code: str
    name: str
    address: str | None
    is_active: bool
    version: int


class TravelTimeIn(Schema):
    campus_a_id: uuid.UUID
    campus_b_id: uuid.UUID
    minutes: int = Field(ge=0, le=1440)


class TravelTimeOut(Out):
    campus_a_id: uuid.UUID
    campus_b_id: uuid.UUID
    minutes: int


class BuildingIn(Schema):
    campus_id: uuid.UUID
    code: Code
    name: Name
    is_active: bool = True


class BuildingPatch(Patch):
    required_fields = frozenset({"campus_id", "code", "name", "is_active"})
    campus_id: uuid.UUID | None = None
    code: Code | None = None
    name: Name | None = None
    is_active: bool | None = None


class BuildingOut(Out):
    id: uuid.UUID
    campus_id: uuid.UUID
    code: str
    name: str
    is_active: bool
    version: int


# ── rooms ──────────────────────────────────────────────────────────────


class RoomTypeIn(Schema):
    code: Code
    name: Name
    description: LongText | None = None
    is_active: bool = True


class RoomTypePatch(Patch):
    required_fields = frozenset({"code", "name", "is_active"})
    code: Code | None = None
    name: Name | None = None
    description: LongText | None = None
    is_active: bool | None = None


class RoomTypeOut(Out):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    version: int


class RoomFeatureIn(Schema):
    code: Code
    name: Name


class RoomFeaturePatch(Patch):
    required_fields = frozenset({"code", "name"})
    code: Code | None = None
    name: Name | None = None


class RoomFeatureOut(Out):
    id: uuid.UUID
    code: str
    name: str
    version: int


class RoomIn(Schema):
    building_id: uuid.UUID
    code: Code
    name: Name | None = None
    room_type_id: uuid.UUID
    capacity: int = Field(ge=1, le=10_000)
    department_id: uuid.UUID | None = None
    is_active: bool = True
    notes: LongText | None = None
    feature_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)


class RoomPatch(Patch):
    required_fields = frozenset(
        {"building_id", "code", "room_type_id", "capacity", "is_active", "feature_ids"}
    )
    building_id: uuid.UUID | None = None
    code: Code | None = None
    name: Name | None = None
    room_type_id: uuid.UUID | None = None
    capacity: Annotated[int, Field(ge=1, le=10_000)] | None = None
    department_id: uuid.UUID | None = None
    is_active: bool | None = None
    notes: LongText | None = None
    feature_ids: Annotated[list[uuid.UUID], Field(max_length=50)] | None = None


class FeatureRef(Out):
    id: uuid.UUID
    code: str
    name: str


class RoomOut(Out):
    id: uuid.UUID
    building_id: uuid.UUID
    code: str
    name: str | None
    room_type_id: uuid.UUID
    capacity: int
    department_id: uuid.UUID | None
    is_active: bool
    notes: str | None
    features: list[FeatureRef]
    version: int


# ── academic catalogue ─────────────────────────────────────────────────


class ProgrammeIn(Schema):
    code: Code
    name: Name
    department_id: uuid.UUID
    level: Annotated[str, Field(max_length=40)] | None = None
    is_active: bool = True


class ProgrammePatch(Patch):
    required_fields = frozenset({"code", "name", "department_id", "is_active"})
    code: Code | None = None
    name: Name | None = None
    department_id: uuid.UUID | None = None
    level: Annotated[str, Field(max_length=40)] | None = None
    is_active: bool | None = None


class ProgrammeOut(Out):
    id: uuid.UUID
    code: str
    name: str
    department_id: uuid.UUID
    level: str | None
    is_active: bool
    version: int


class CourseIn(Schema):
    code: Code
    title: Name
    department_id: uuid.UUID
    credits: Annotated[Decimal, Field(ge=0, le=100, decimal_places=1)] | None = None
    description: LongText | None = None
    is_active: bool = True


class CoursePatch(Patch):
    required_fields = frozenset({"code", "title", "department_id", "is_active"})
    code: Code | None = None
    title: Name | None = None
    department_id: uuid.UUID | None = None
    credits: Annotated[Decimal, Field(ge=0, le=100, decimal_places=1)] | None = None
    description: LongText | None = None
    is_active: bool | None = None


class CourseOut(Out):
    id: uuid.UUID
    code: str
    title: str
    department_id: uuid.UUID
    credits: Decimal | None
    description: str | None
    is_active: bool
    version: int


class ActivityTypeIn(Schema):
    code: Annotated[str, Field(min_length=1, max_length=16, pattern=r"^\S+$")]
    name: Name
    default_room_type_id: uuid.UUID | None = None
    color: Color = "#5b6b7f"
    position: int = Field(default=0, ge=0, le=1000)
    is_active: bool = True


class ActivityTypePatch(Patch):
    required_fields = frozenset({"code", "name", "color", "position", "is_active"})
    code: Annotated[str, Field(min_length=1, max_length=16, pattern=r"^\S+$")] | None = None
    name: Name | None = None
    default_room_type_id: uuid.UUID | None = None
    color: Color | None = None
    position: Annotated[int, Field(ge=0, le=1000)] | None = None
    is_active: bool | None = None


class ActivityTypeOut(Out):
    id: uuid.UUID
    code: str
    name: str
    default_room_type_id: uuid.UUID | None
    color: str
    position: int
    is_active: bool
    version: int


class InstructorIn(Schema):
    code: Code
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]
    email: EmailStr | None = None
    department_id: uuid.UUID
    title: Annotated[str, Field(max_length=80)] | None = None
    max_weekly_periods: Annotated[int, Field(ge=1, le=100)] | None = None
    is_active: bool = True
    notes: LongText | None = None


class InstructorPatch(Patch):
    required_fields = frozenset({"code", "first_name", "last_name", "department_id", "is_active"})
    code: Code | None = None
    first_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    last_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    email: EmailStr | None = None
    department_id: uuid.UUID | None = None
    title: Annotated[str, Field(max_length=80)] | None = None
    max_weekly_periods: Annotated[int, Field(ge=1, le=100)] | None = None
    is_active: bool | None = None
    notes: LongText | None = None


class InstructorOut(Out):
    id: uuid.UUID
    code: str
    first_name: str
    last_name: str
    email: str | None
    department_id: uuid.UUID
    title: str | None
    max_weekly_periods: int | None
    is_active: bool
    notes: str | None
    version: int


class CalendarEventIn(Schema):
    start_date: date
    end_date: date
    kind: Literal["holiday", "closure"] = "holiday"
    label: Name
    is_tentative: bool = False


class CalendarEventPatch(Patch):
    required_fields = frozenset({"start_date", "end_date", "kind", "label", "is_tentative"})
    start_date: date | None = None
    end_date: date | None = None
    kind: Literal["holiday", "closure"] | None = None
    label: Name | None = None
    is_tentative: bool | None = None


class CalendarEventOut(Out):
    id: uuid.UUID
    start_date: date
    end_date: date
    kind: str
    label: str
    is_tentative: bool
    version: int
    updated_at: datetime
