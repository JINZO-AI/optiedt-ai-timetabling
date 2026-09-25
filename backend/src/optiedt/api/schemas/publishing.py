"""Request and response bodies for publications, dated occurrences and exceptions."""

from __future__ import annotations

import datetime as dt
import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from optiedt.api.schemas.common import LongText, Out, Schema


class PublicationOut(Out):
    id: uuid.UUID
    term_id: uuid.UUID
    version_no: int
    solution_id: uuid.UUID
    snapshot_id: uuid.UUID
    content_hash: str
    is_current: bool
    restored_from_id: uuid.UUID | None
    published_by_id: uuid.UUID | None
    published_at: datetime
    note: str | None
    summary: dict[str, Any]


class PublishIn(Schema):
    version: int
    note: LongText | None = None


class RestoreIn(Schema):
    note: LongText | None = None


class DiffChangeOut(Out):
    session_id: str
    kind: str
    before: list[Any] | None
    after: list[Any] | None
    label: str | None


class DiffOut(Out):
    from_version: int | None
    to_version: int
    counts: dict[str, int]
    changes: list[DiffChangeOut]


class OccurrenceOut(Out):
    session_id: str
    date: dt.date
    period: int
    duration: int
    room_id: str | None
    status: str
    exception_id: str | None
    original_date: dt.date | None
    original_period: int | None
    original_room_id: str | None
    moved_to_date: dt.date | None
    moved_to_period: int | None
    notice: str | None


ExceptionKind = Literal["cancelled", "relocated", "rescheduled"]


class ExceptionIn(Schema):
    session_id: uuid.UUID
    occurrence_date: date
    kind: ExceptionKind
    new_room_id: uuid.UUID | None = None
    new_date: date | None = None
    new_period: Annotated[int, Field(ge=0, le=47)] | None = None
    reason: LongText | None = None
    notice: LongText | None = None
    """Shown to the people concerned in their timetable and calendar feed."""


class ExceptionOut(Out):
    id: uuid.UUID
    publication_id: uuid.UUID
    session_id: uuid.UUID
    occurrence_date: date
    kind: str
    new_date: date | None
    new_period: int | None
    new_room_id: uuid.UUID | None
    reason: str | None
    notice: str | None
    created_by_id: uuid.UUID | None
    created_at: datetime
    revoked_at: datetime | None


class DisruptionIn(Schema):
    resource_kind: Literal["room", "instructor", "group"]
    resource_id: uuid.UUID
    start: date
    end: date


class DisruptionEntryOut(Out):
    session_id: str
    label: str
    date: dt.date
    period: int
    room_id: str | None
    status: str
    action: str
    new_room_id: str | None
    new_date: dt.date | None
    new_period: int | None
    applicable: bool


class DisruptionChangeIn(Schema):
    session_id: uuid.UUID
    occurrence_date: date
    kind: ExceptionKind
    new_room_id: uuid.UUID | None = None
    new_date: date | None = None
    new_period: Annotated[int, Field(ge=0, le=47)] | None = None


class DisruptionApplyIn(Schema):
    changes: Annotated[list[DisruptionChangeIn], Field(min_length=1, max_length=500)]
    reason: LongText | None = None
    notice: LongText | None = None
