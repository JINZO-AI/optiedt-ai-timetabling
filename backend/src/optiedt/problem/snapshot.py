"""The problem snapshot: a self-contained, canonical description of one term's scheduling
problem (ADR 0008).

Slots are addressed by ``[day, period]`` where ``day`` indexes the term's teaching weekdays
in display order and ``period`` indexes the period list. Everything a run, a solution or a
publication needs to be interpreted later is in here.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1
SESSION_NAMESPACE = uuid.UUID("7b1b4c1e-3c2a-5d6f-9a0b-4f2e8d1c6a57")

Slot = tuple[int, int]
"""(day index, period index)."""


def session_id(activity_id: uuid.UUID | str, occurrence: int) -> uuid.UUID:
    """Stable identity of an activity's weekly occurrence across snapshots."""
    return uuid.uuid5(SESSION_NAMESPACE, f"{activity_id}:{occurrence}")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class STerm(_Model):
    id: str
    code: str
    name: str
    start_date: str
    end_date: str
    timezone: str
    room_capacity_ratio: float


class SDay(_Model):
    index: int
    weekday: int


class SPeriod(_Model):
    id: str
    index: int
    label: str
    start: str
    end: str
    joins_next: bool


class SSlot(_Model):
    day: int
    period: int
    closed: bool = False
    penalty: int = 0
    start: str | None = None
    end: str | None = None
    reason: str | None = None


class SCampus(_Model):
    id: str
    code: str
    name: str


class SBuilding(_Model):
    id: str
    code: str
    name: str
    campus_id: str


class SNamed(_Model):
    id: str
    code: str
    name: str


class SRoom(_Model):
    id: str
    code: str
    name: str | None
    building_id: str
    campus_id: str
    type_id: str
    capacity: int
    features: list[str]
    department_id: str | None
    unavailable: list[Slot] = Field(default_factory=list)


class SDepartment(_Model):
    id: str
    code: str
    name: str
    parent_id: str | None


class SInstructor(_Model):
    id: str
    code: str
    name: str
    email: str | None
    department_id: str
    max_weekly_periods: int | None
    active: bool
    unavailable: list[Slot] = Field(default_factory=list)
    undesirable: list[Slot] = Field(default_factory=list)
    preferred: list[Slot] = Field(default_factory=list)


class SGroup(_Model):
    id: str
    code: str
    name: str
    parent_id: str | None
    partition: str
    size: int
    department_id: str | None
    unavailable: list[Slot] = Field(default_factory=list)


class SCourse(_Model):
    id: str
    code: str
    title: str
    department_id: str


class SActivityType(_Model):
    id: str
    code: str
    name: str
    color: str


class SFixed(_Model):
    occurrence: int
    day: int
    period: int
    room_id: str | None


class SActivity(_Model):
    id: str
    course_id: str
    type_id: str
    label: str | None
    duration: int
    sessions_per_week: int
    different_days: bool
    online: bool
    room_type_id: str | None
    """Effective room type: the activity's own, else the activity type's default."""
    features: list[str]
    min_capacity: int
    """Effective seats: the activity's own figure, else the total size of its groups."""
    campus_id: str | None
    building_id: str | None
    allowed_rooms: list[str]
    preferred_rooms: list[str]
    avoided_rooms: list[str]
    group_ids: list[str]
    instructor_ids: list[str]
    unavailable: list[Slot] = Field(default_factory=list)
    fixed: list[SFixed] = Field(default_factory=list)


class SSession(_Model):
    id: str
    activity_id: str
    occurrence: int


class SRule(_Model):
    id: str
    type: str
    name: str
    enforcement: str
    tier: int
    weight: int
    params: dict[str, Any]
    """Parameters with period and slot references resolved to indices."""
    instructor_ids: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)
    activity_ids: list[str] = Field(default_factory=list)
    """Targets resolved from the rule's scope (departments expanded, 'all' made explicit)."""
    ordered: bool = False
    """True for pair rules: ``activity_ids`` is [first, second]."""


class SObjectiveSetting(_Model):
    tier: int
    weight: int
    enabled: bool = True


class SProfile(_Model):
    code: str
    name: str
    objectives: dict[str, SObjectiveSetting]


class Snapshot(_Model):
    schema_version: int = SCHEMA_VERSION
    term: STerm
    days: list[SDay]
    periods: list[SPeriod]
    slots: list[SSlot]
    campuses: list[SCampus]
    travel_minutes: list[tuple[str, str, int]]
    buildings: list[SBuilding]
    room_types: list[SNamed]
    features: list[SNamed]
    rooms: list[SRoom]
    departments: list[SDepartment]
    instructors: list[SInstructor]
    groups: list[SGroup]
    courses: list[SCourse]
    activity_types: list[SActivityType]
    activities: list[SActivity]
    sessions: list[SSession]
    rules: list[SRule]
    profiles: list[SProfile]


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
