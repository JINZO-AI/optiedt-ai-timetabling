"""Publications: versions, weekly and dated views, differences, restoring, date-level
exceptions and disruption planning."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select

from optiedt.api.deps import DbSession, PrincipalDep
from optiedt.api.idempotency import IdempotencyKey, perform
from optiedt.api.schemas import publishing as p
from optiedt.api.schemas import scheduling as s
from optiedt.errors import FieldError, InvalidInput
from optiedt.models import Publication
from optiedt.services import calendar, exceptions, publications
from optiedt.services.exceptions import Request
from optiedt.services.problems import problem_for
from optiedt.services.solutions import timetable_payload
from optiedt.services.terms import get_term

router = APIRouter(tags=["publications"])

MAX_DAYS = 400


@router.get("/terms/{term_id}/publications", response_model=list[p.PublicationOut])
def list_publications(
    term_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> list[p.PublicationOut]:
    publications.require_read(principal)
    get_term(db, term_id)
    rows = db.scalars(
        select(Publication)
        .where(Publication.term_id == term_id)
        .order_by(Publication.version_no.desc())
    )
    return [p.PublicationOut.model_validate(row) for row in rows]


@router.get("/publications/{publication_id}", response_model=p.PublicationOut)
def get_publication(
    publication_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> p.PublicationOut:
    publications.require_read(principal)
    return p.PublicationOut.model_validate(publications.get_publication(db, publication_id))


@router.get("/publications/{publication_id}/timetable", response_model=s.TimetableOut)
def get_timetable(
    publication_id: uuid.UUID, db: DbSession, principal: PrincipalDep
) -> s.TimetableOut:
    """The weekly pattern; dated views and exceptions are under ``/occurrences``."""
    publications.require_read(principal)
    publication = publications.get_publication(db, publication_id)
    payload = timetable_payload(
        problem_for(db, publication.snapshot_id),
        publications.publication_placements(db, publication.id),
        set(),
        [],
    )
    return s.TimetableOut.model_validate(payload)


@router.get("/publications/{publication_id}/diff", response_model=p.DiffOut)
def diff(
    publication_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    against: uuid.UUID | None = None,
) -> p.DiffOut:
    """Changes from ``against`` (by default the previous version) to this version."""
    return p.DiffOut.model_validate(
        publications.diff_publications(db, principal, publication_id, against)
    )


@router.post(
    "/publications/{publication_id}/restore", response_model=p.PublicationOut, status_code=201
)
def restore(
    publication_id: uuid.UUID,
    body: p.RestoreIn,
    db: DbSession,
    principal: PrincipalDep,
    idempotency_key: IdempotencyKey = None,
) -> JSONResponse:
    def action() -> tuple[int, object]:
        publication = publications.restore(db, principal, publication_id, note=body.note)
        db.flush()
        db.refresh(publication)
        return 201, p.PublicationOut.model_validate(publication).model_dump(mode="json")

    return perform(
        db,
        principal,
        idempotency_key,
        f"publication-restore:{publication_id}",
        body.model_dump(mode="json"),
        action,
    )


def _range(start: date, end: date) -> None:
    if end < start:
        raise InvalidInput("The end date is before the start date.", [FieldError("to", "order")])
    if end - start > timedelta(days=MAX_DAYS):
        raise InvalidInput(
            f"Ask for at most {MAX_DAYS} days at a time.", [FieldError("to", "range")]
        )


@router.get("/publications/{publication_id}/occurrences", response_model=list[p.OccurrenceOut])
def list_occurrences(
    publication_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
    group_id: uuid.UUID | None = None,
    instructor_id: uuid.UUID | None = None,
    room_id: uuid.UUID | None = None,
) -> list[p.OccurrenceOut]:
    """Dated occurrences with exceptions applied, optionally for one group (with the groups
    sharing its students), instructor or room."""
    publications.require_read(principal)
    _range(start, end)
    publication = publications.get_publication(db, publication_id)
    found = calendar.occurrences(db, publication, start, end)
    sessions = calendar.session_ids_for(
        problem_for(db, publication.snapshot_id), group_id=group_id, instructor_id=instructor_id
    )
    if sessions is not None:
        found = [o for o in found if o.session_id in sessions]
    if room_id is not None:
        found = [o for o in found if o.room_id == str(room_id)]
    return [p.OccurrenceOut.model_validate(o) for o in found]


@router.get("/publications/{publication_id}/exceptions", response_model=list[p.ExceptionOut])
def list_exceptions(
    publication_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
    include_revoked: bool = False,
) -> list[p.ExceptionOut]:
    rows = exceptions.list_exceptions(
        db, principal, publication_id, start=start, end=end, include_revoked=include_revoked
    )
    return [p.ExceptionOut.model_validate(row) for row in rows]


def _request(body: p.ExceptionIn | p.DisruptionChangeIn) -> Request:
    return Request(
        session_id=str(body.session_id),
        occurrence_date=body.occurrence_date,
        kind=body.kind,
        new_room_id=str(body.new_room_id) if body.new_room_id else None,
        new_date=body.new_date,
        new_period=body.new_period,
    )


@router.post(
    "/publications/{publication_id}/exceptions", response_model=p.ExceptionOut, status_code=201
)
def create_exception(
    publication_id: uuid.UUID,
    body: p.ExceptionIn,
    db: DbSession,
    principal: PrincipalDep,
    idempotency_key: IdempotencyKey = None,
) -> JSONResponse:
    def action() -> tuple[int, object]:
        exception = exceptions.create(
            db, principal, publication_id, _request(body), reason=body.reason, notice=body.notice
        )
        db.flush()
        db.refresh(exception)
        return 201, p.ExceptionOut.model_validate(exception).model_dump(mode="json")

    return perform(
        db,
        principal,
        idempotency_key,
        f"publication-exception:{publication_id}",
        body.model_dump(mode="json"),
        action,
    )


@router.delete("/exceptions/{exception_id}", response_model=p.ExceptionOut)
def revoke_exception(
    exception_id: uuid.UUID,
    db: DbSession,
    principal: PrincipalDep,
    reason: Annotated[str | None, Query(max_length=4000)] = None,
) -> p.ExceptionOut:
    """Undoes a date change; the record stays, marked revoked."""
    exception = exceptions.revoke(db, principal, exception_id, reason=reason)
    db.commit()
    db.refresh(exception)
    return p.ExceptionOut.model_validate(exception)


@router.post(
    "/publications/{publication_id}/disruptions", response_model=list[p.DisruptionEntryOut]
)
def plan_disruption(
    publication_id: uuid.UUID, body: p.DisruptionIn, db: DbSession, principal: PrincipalDep
) -> list[p.DisruptionEntryOut]:
    """What a room, instructor or group being unavailable between two dates affects, with the
    least disruptive valid change for each occurrence. Nothing is changed."""
    _range(body.start, body.end)
    plan = exceptions.plan_disruption(
        db,
        principal,
        publication_id,
        resource_kind=body.resource_kind,
        resource_id=body.resource_id,
        start=body.start,
        end=body.end,
    )
    return [p.DisruptionEntryOut.model_validate(entry) for entry in plan]


@router.post(
    "/publications/{publication_id}/disruptions/apply",
    response_model=list[p.ExceptionOut],
    status_code=201,
)
def apply_disruption(
    publication_id: uuid.UUID,
    body: p.DisruptionApplyIn,
    db: DbSession,
    principal: PrincipalDep,
    idempotency_key: IdempotencyKey = None,
) -> JSONResponse:
    def action() -> tuple[int, object]:
        created = exceptions.apply_disruption(
            db,
            principal,
            publication_id,
            [_request(change) for change in body.changes],
            reason=body.reason,
            notice=body.notice,
        )
        db.flush()
        for row in created:
            db.refresh(row)
        return 201, [p.ExceptionOut.model_validate(row).model_dump(mode="json") for row in created]

    return perform(
        db,
        principal,
        idempotency_key,
        f"publication-disruption:{publication_id}",
        body.model_dump(mode="json"),
        action,
    )
