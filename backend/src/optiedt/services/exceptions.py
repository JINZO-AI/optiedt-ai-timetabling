"""Date-level exceptions on the current publication and the disruption planner (ADR 0013).

An exception cancels one occurrence, relocates it (another room, same time) or reschedules
it (another period in the same teaching week). Relocations and reschedulings are checked
like any placement (room suitability, weekly availability, closed slots, hard slot rules) and
against what actually happens on that date, other exceptions included.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, FieldError, InvalidInput, NotFound, PermissionDenied
from optiedt.evaluation.evaluator import Evaluator
from optiedt.evaluation.suggest import candidate_rooms
from optiedt.evaluation.types import ObjectiveConfig, Placement
from optiedt.models import OccurrenceException, Publication, Term
from optiedt.problem.model import Problem
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.calendar import (
    Occurrence,
    day_of_date,
    occurrences,
    session_ids_for,
    teaching_dates,
)
from optiedt.services.problems import problem_for
from optiedt.services.publications import get_publication
from optiedt.services.terms import get_term

KINDS = ("cancelled", "relocated", "rescheduled")
IGNORED_CODES = frozenset({"fixed_moved"})
"""Fixed placements constrain the weekly timetable, not single dated changes."""


@dataclass(frozen=True, slots=True)
class Request:
    session_id: str
    occurrence_date: date
    kind: str
    new_room_id: str | None = None
    new_date: date | None = None
    new_period: int | None = None


class Checker:
    """Checks dated placements against the weekly rules and the occurrences of a date."""

    def __init__(self, db: Session, publication: Publication) -> None:
        self.db = db
        self.publication = publication
        self.term: Term = get_term(db, publication.term_id)
        self.problem: Problem = problem_for(db, publication.snapshot_id)
        self.evaluator = Evaluator(self.problem, ObjectiveConfig({}))
        self.index = {s.id: s.index for s in self.problem.sessions}
        self._days: dict[date, list[Occurrence]] = {}

    def day(self, value: date) -> list[Occurrence]:
        if value not in self._days:
            self._days[value] = occurrences(self.db, self.publication, value, value)
        return self._days[value]

    def forget(self, *values: date) -> None:
        for value in values:
            self._days.pop(value, None)

    def label(self, session_id: str) -> str:
        return self.problem.describe_session(self.problem.sessions[self.index[session_id]])

    def static_problems(
        self, session_id: str, day: int, period: int, room_id: str | None
    ) -> list[str]:
        p = self.problem
        if period + p.sessions[self.index[session_id]].duration > p.n_periods:
            return ["it does not fit before the end of the day"]
        room = p.room_index.get(room_id) if room_id is not None else None
        found = self.evaluator.placement_violations(
            self.index[session_id], Placement(p.slot(day, period), room)
        )
        return [v.message for v in found if v.code not in IGNORED_CODES]

    def clashes(
        self,
        session_id: str,
        when: date,
        period: int,
        room_id: str | None,
        ignore: Occurrence | None,
    ) -> list[str]:
        p = self.problem
        s = p.sessions[self.index[session_id]]
        periods = set(range(period, period + s.duration))
        found = []
        for other in self.day(when):
            if not other.takes_place or other == ignore or other.session_id == session_id:
                continue
            if not periods & set(other.periods()):
                continue
            o = p.sessions[self.index[other.session_id]]
            label = p.describe_session(o)
            if room_id is not None and other.room_id == room_id:
                found.append(f"{p.rooms[p.room_index[room_id]].code} is used by {label}")
            shared = set(s.instructors) & set(o.instructors)
            if shared:
                names = ", ".join(p.instructors[i].name for i in sorted(shared))
                found.append(f"{names} teaches {label}")
            if self.evaluator.overlap.sessions_share_students(s.groups, o.groups):
                found.append(f"its students attend {label}")
        return found


def _require_manage(principal: Principal, checker: Checker, session_ids: Sequence[str]) -> None:
    scope = principal.scope(Permission.EXCEPTIONS_MANAGE)
    if scope.is_empty:
        raise PermissionDenied()
    if scope.everywhere:
        return
    p = checker.problem
    departments = {
        uuid.UUID(p.activities[p.sessions[checker.index[s]].activity].department_id)
        for s in session_ids
        if s in checker.index
    }
    if not scope.covers_all(departments):
        raise PermissionDenied("You may only change sessions of your departments.")


def _current(db: Session, publication_id: uuid.UUID) -> Publication:
    publication = get_publication(db, publication_id)
    if not publication.is_current:
        raise Conflict("Only the current timetable can take date changes.", code="not_current")
    return publication


def _validate(checker: Checker, request: Request) -> tuple[Occurrence, list[str]]:
    """The occurrence the request changes, and every reason it cannot be applied."""
    if request.session_id not in checker.index:
        raise InvalidInput("Unknown session.", [FieldError("session_id", request.session_id)])
    if request.kind not in KINDS:
        raise InvalidInput("Unknown kind of change.", [FieldError("kind", request.kind)])
    target = next(
        (
            o
            for o in checker.day(request.occurrence_date)
            if o.session_id == request.session_id and o.date == request.occurrence_date
        ),
        None,
    )
    if target is None:
        raise NotFound("Occurrence of this session on that date")
    if target.exception_id is not None:
        raise Conflict(
            "This occurrence already has a change; undo it first.", code="exception_exists"
        )
    problems: list[str] = []
    day = day_of_date(checker.term, request.occurrence_date)
    if request.kind == "relocated":
        if request.new_room_id is None or request.new_room_id == target.room_id:
            raise InvalidInput("Choose another room.", [FieldError("new_room_id", "required")])
        if day is not None:
            problems += checker.static_problems(
                request.session_id, day, target.period, request.new_room_id
            )
        problems += checker.clashes(
            request.session_id, target.date, target.period, request.new_room_id, target
        )
    elif request.kind == "rescheduled":
        if request.new_date is None or request.new_period is None:
            raise InvalidInput(
                "Choose the new date and period.",
                [FieldError("new_date", "required"), FieldError("new_period", "required")],
            )
        if request.new_date.isocalendar()[:2] != request.occurrence_date.isocalendar()[:2]:
            problems.append("the new date is not in the same week")
        new_day = teaching_dates(checker.db, checker.term, request.new_date, request.new_date).get(
            request.new_date
        )
        if new_day is None:
            problems.append("the new date is not a teaching day")
        elif (request.new_date, request.new_period) == (target.date, target.period):
            problems.append("the new time is the current time")
        else:
            room = request.new_room_id or target.room_id
            problems += checker.static_problems(
                request.session_id, new_day, request.new_period, room
            )
            problems += checker.clashes(
                request.session_id, request.new_date, request.new_period, room, target
            )
    return target, problems


def create(
    db: Session,
    principal: Principal,
    publication_id: uuid.UUID,
    request: Request,
    *,
    reason: str | None,
    notice: str | None,
    checker: Checker | None = None,
) -> OccurrenceException:
    publication = _current(db, publication_id)
    checker = checker or Checker(db, publication)
    _require_manage(principal, checker, [request.session_id])
    target, problems = _validate(checker, request)
    if problems:
        raise Conflict(
            "This change is not possible: " + "; ".join(problems) + ".",
            code="exception_invalid",
            problems=problems,
        )
    exception = OccurrenceException(
        publication_id=publication.id,
        session_id=uuid.UUID(request.session_id),
        occurrence_date=request.occurrence_date,
        kind=request.kind,
        new_room_id=uuid.UUID(request.new_room_id) if request.new_room_id else None,
        new_date=request.new_date if request.kind == "rescheduled" else None,
        new_period=request.new_period if request.kind == "rescheduled" else None,
        reason=reason,
        notice=notice,
        created_by_id=principal.user_id,
    )
    if request.kind == "rescheduled" and request.new_room_id is None:
        exception.new_room_id = uuid.UUID(target.room_id) if target.room_id else None
    db.add(exception)
    db.flush()
    checker.forget(request.occurrence_date, *(d for d in (request.new_date,) if d))
    audit.record(
        db,
        principal,
        action=f"exception.{request.kind}",
        entity_type="occurrence_exception",
        entity_id=exception.id,
        summary=f"{checker.label(request.session_id)} on {request.occurrence_date}: {request.kind}",
        reason=reason,
        term_id=publication.term_id,
    )
    return exception


def revoke(
    db: Session, principal: Principal, exception_id: uuid.UUID, *, reason: str | None
) -> OccurrenceException:
    """Undoes a change, if the occurrence can take its weekly place again on that date."""
    exception = db.get(OccurrenceException, exception_id)
    if exception is None or exception.revoked_at is not None:
        raise NotFound("Date change")
    publication = _current(db, exception.publication_id)
    checker = Checker(db, publication)
    session_id = str(exception.session_id)
    _require_manage(principal, checker, [session_id])
    weekly = next(
        (o for o in checker.day(exception.occurrence_date) if o.session_id == session_id), None
    )
    exception.revoked_at = datetime.now(UTC)
    exception.revoked_by_id = principal.user_id
    db.flush()
    checker.forget(exception.occurrence_date)
    if weekly is not None:
        clashes = checker.clashes(
            session_id, exception.occurrence_date, weekly.period, weekly.room_id, None
        )
        if clashes:
            raise Conflict(
                "Undoing this change would clash on that date: " + "; ".join(clashes) + ".",
                code="revoke_clash",
            )
    audit.record(
        db,
        principal,
        action="exception.revoke",
        entity_type="occurrence_exception",
        entity_id=exception.id,
        summary=f"Undid the {exception.kind} change of {checker.label(session_id)} on "
        f"{exception.occurrence_date}",
        reason=reason,
        term_id=publication.term_id,
    )
    return exception


def list_exceptions(
    db: Session,
    principal: Principal,
    publication_id: uuid.UUID,
    *,
    start: date | None = None,
    end: date | None = None,
    include_revoked: bool = False,
) -> list[OccurrenceException]:
    if not (
        principal.can(Permission.PUBLICATIONS_READ) or principal.can(Permission.SOLUTIONS_READ)
    ):
        raise PermissionDenied()
    get_publication(db, publication_id)
    statement = select(OccurrenceException).where(
        OccurrenceException.publication_id == publication_id
    )
    if not include_revoked:
        statement = statement.where(OccurrenceException.revoked_at.is_(None))
    if start is not None:
        statement = statement.where(OccurrenceException.occurrence_date >= start)
    if end is not None:
        statement = statement.where(OccurrenceException.occurrence_date <= end)
    return list(
        db.scalars(
            statement.order_by(OccurrenceException.occurrence_date, OccurrenceException.created_at)
        )
    )


# ── disruptions ────────────────────────────────────────────────────────


def plan_disruption(
    db: Session,
    principal: Principal,
    publication_id: uuid.UUID,
    *,
    resource_kind: str,
    resource_id: uuid.UUID,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    """Occurrences that use a room, instructor or group between two dates, each with the
    least disruptive valid change: another room at the same time, else another time in the
    same week outside the disruption, else cancellation."""
    if resource_kind not in ("room", "instructor", "group"):
        raise InvalidInput("Unknown resource kind.", [FieldError("resource_kind", resource_kind)])
    if end < start:
        raise InvalidInput("The end date is before the start date.", [FieldError("end", "order")])
    publication = _current(db, publication_id)
    checker = Checker(db, publication)
    problem = checker.problem
    if not principal.can(Permission.EXCEPTIONS_MANAGE):
        raise PermissionDenied()
    sessions = session_ids_for(
        problem,
        instructor_id=resource_id if resource_kind == "instructor" else None,
        group_id=resource_id if resource_kind == "group" else None,
    )
    affected = [
        o
        for o in occurrences(db, publication, start, end)
        if o.takes_place
        and (
            (resource_kind == "room" and o.room_id == str(resource_id))
            or (sessions is not None and o.session_id in sessions)
        )
    ]
    plan = []
    for occurrence in affected:
        proposal = None
        if resource_kind == "room" or occurrence.room_id is None:
            proposal = _relocation(checker, occurrence, avoid=str(resource_id))
        if proposal is None and occurrence.status == "scheduled":
            proposal = _rescheduling(checker, occurrence, start, end)
        if proposal is None:
            proposal = Request(occurrence.session_id, occurrence.date, "cancelled")
        _occupy(checker, occurrence, proposal)
        plan.append(
            {
                "session_id": occurrence.session_id,
                "label": checker.label(occurrence.session_id),
                "date": occurrence.date.isoformat(),
                "period": occurrence.period,
                "room_id": occurrence.room_id,
                "status": occurrence.status,
                "action": proposal.kind,
                "new_room_id": proposal.new_room_id,
                "new_date": proposal.new_date.isoformat() if proposal.new_date else None,
                "new_period": proposal.new_period,
                "applicable": occurrence.status == "scheduled",
            }
        )
    return plan


def _relocation(checker: Checker, occurrence: Occurrence, avoid: str) -> Request | None:
    p = checker.problem
    s = checker.index[occurrence.session_id]
    need = p.activities[p.sessions[s].activity].min_capacity
    day = day_of_date(checker.term, occurrence.date)
    if day is None:
        return None
    rooms = [r for r in candidate_rooms(checker.evaluator, s) if r is not None]
    for r in sorted(rooms, key=lambda r: (p.rooms[r].capacity - need, p.rooms[r].code)):
        room_id = p.rooms[r].id
        if room_id in (avoid, occurrence.room_id):
            continue
        if checker.static_problems(occurrence.session_id, day, occurrence.period, room_id):
            continue
        if checker.clashes(
            occurrence.session_id, occurrence.date, occurrence.period, room_id, occurrence
        ):
            continue
        return Request(occurrence.session_id, occurrence.date, "relocated", new_room_id=room_id)
    return None


def _rescheduling(
    checker: Checker, occurrence: Occurrence, start: date, end: date
) -> Request | None:
    year, week, _ = occurrence.date.isocalendar()
    week_dates = {
        d: day
        for d, day in teaching_dates(
            checker.db,
            checker.term,
            date.fromisocalendar(year, week, 1),
            date.fromisocalendar(year, week, 7),
        ).items()
        if not start <= d <= end
    }
    for when, day in sorted(week_dates.items()):
        for period in range(checker.problem.n_periods):
            room = occurrence.room_id
            if checker.static_problems(occurrence.session_id, day, period, room):
                continue
            if checker.clashes(occurrence.session_id, when, period, room, occurrence):
                continue
            return Request(
                occurrence.session_id,
                occurrence.date,
                "rescheduled",
                new_date=when,
                new_period=period,
            )
    return None


def _occupy(checker: Checker, occurrence: Occurrence, proposal: Request) -> None:
    """Records a proposal in the planner's view of each date, so later proposals avoid it."""
    day = checker.day(occurrence.date)
    day[:] = [o for o in day if o != occurrence]
    if proposal.kind == "relocated":
        day.append(
            Occurrence(
                occurrence.session_id,
                occurrence.date,
                occurrence.period,
                occurrence.duration,
                proposal.new_room_id,
                "relocated",
            )
        )
    elif proposal.kind == "rescheduled" and proposal.new_date is not None:
        checker.day(proposal.new_date).append(
            Occurrence(
                occurrence.session_id,
                proposal.new_date,
                int(proposal.new_period or 0),
                occurrence.duration,
                occurrence.room_id,
                "rescheduled",
            )
        )


def apply_disruption(
    db: Session,
    principal: Principal,
    publication_id: uuid.UUID,
    requests: Sequence[Request],
    *,
    reason: str | None,
    notice: str | None,
) -> list[OccurrenceException]:
    """Creates the chosen changes in order; each is checked against the ones before it."""
    publication = _current(db, publication_id)
    checker = Checker(db, publication)
    return [
        create(
            db, principal, publication.id, request, reason=reason, notice=notice, checker=checker
        )
        for request in requests
    ]
