"""Dated occurrences of a published weekly timetable (ADR 0013).

A session placed on a teaching day occurs on every date of the term with that weekday,
except holidays and closures. Exceptions then cancel, relocate or reschedule single
occurrences. Portals, calendar feeds, exceptions and disruption planning all read dated
occurrences from here.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from optiedt.models import CalendarEvent, OccurrenceException, Publication, Term
from optiedt.problem.model import Problem
from optiedt.services.problems import problem_for
from optiedt.services.publications import publication_placements
from optiedt.services.terms import get_term

MAX_RANGE_DAYS = 400


@dataclass(frozen=True, slots=True)
class Occurrence:
    session_id: str
    date: dt.date
    period: int
    duration: int
    room_id: str | None
    status: str
    """``scheduled``, ``cancelled``, ``relocated``, ``rescheduled`` (at its new place) or
    ``moved`` (the original place of a rescheduled occurrence)."""
    exception_id: str | None = None
    original_date: dt.date | None = None
    """For a rescheduled occurrence, the date it was moved from."""
    original_period: int | None = None
    original_room_id: str | None = None
    """For a relocated or rescheduled occurrence, the room of the weekly timetable."""
    moved_to_date: dt.date | None = None
    """For the original place of a rescheduled occurrence, where it went."""
    moved_to_period: int | None = None
    notice: str | None = None

    @property
    def takes_place(self) -> bool:
        return self.status in ("scheduled", "relocated", "rescheduled")

    def periods(self) -> range:
        return range(self.period, self.period + self.duration)


def dates(start: date, end: date) -> Iterator[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def closed_dates(db: Session, start: date, end: date) -> set[date]:
    """Dates of holidays and closures between ``start`` and ``end``."""
    closed: set[date] = set()
    for event in db.scalars(
        select(CalendarEvent).where(
            CalendarEvent.start_date <= end, CalendarEvent.end_date >= start
        )
    ):
        closed.update(d for d in dates(event.start_date, event.end_date) if start <= d <= end)
    return closed


def teaching_dates(db: Session, term: Term, start: date, end: date) -> dict[date, int]:
    """Teaching dates in the range with the index of their day in the term's week."""
    day_index = {weekday: i for i, weekday in enumerate(term.weekdays)}
    start, end = max(start, term.start_date), min(end, term.end_date)
    if start > end:
        return {}
    closed = closed_dates(db, start, end)
    return {
        d: day_index[d.weekday()]
        for d in dates(start, end)
        if d.weekday() in day_index and d not in closed
    }


def day_of_date(term: Term, value: date) -> int | None:
    return next((i for i, weekday in enumerate(term.weekdays) if weekday == value.weekday()), None)


def occurrences(db: Session, publication: Publication, start: date, end: date) -> list[Occurrence]:
    """Every dated occurrence of the publication between ``start`` and ``end``, exceptions
    applied, sorted by date and period."""
    if (end - start).days > MAX_RANGE_DAYS:
        end = start + timedelta(days=MAX_RANGE_DAYS)
    term = get_term(db, publication.term_id)
    problem = problem_for(db, publication.snapshot_id)
    duration = _durations(problem)
    by_day: dict[int, list[tuple[str, int, str | None]]] = defaultdict(list)
    for session_id, (day, period, room_id) in publication_placements(db, publication.id).items():
        by_day[day].append((session_id, period, room_id))
    exceptions = list(
        db.scalars(
            select(OccurrenceException).where(
                OccurrenceException.publication_id == publication.id,
                OccurrenceException.revoked_at.is_(None),
                or_(
                    OccurrenceException.occurrence_date.between(start, end),
                    OccurrenceException.new_date.between(start, end),
                ),
            )
        )
    )
    by_occurrence = {(str(e.session_id), e.occurrence_date): e for e in exceptions}
    result: list[Occurrence] = []
    for day_date, day in sorted(teaching_dates(db, term, start, end).items()):
        for session_id, period, room_id in by_day.get(day, ()):
            base = Occurrence(
                session_id, day_date, period, duration[session_id], room_id, "scheduled"
            )
            exception = by_occurrence.get((session_id, day_date))
            result.append(base if exception is None else _apply(base, exception))
    for exception in exceptions:
        if exception.kind != "rescheduled" or exception.new_date is None:
            continue
        if not start <= exception.new_date <= end:
            continue
        session_id = str(exception.session_id)
        if session_id not in duration:
            continue
        original_room = _weekly_room(by_day, session_id)
        new_room = str(exception.new_room_id) if exception.new_room_id else original_room
        result.append(
            Occurrence(
                session_id,
                exception.new_date,
                int(exception.new_period or 0),
                duration[session_id],
                new_room,
                "rescheduled",
                exception_id=str(exception.id),
                original_date=exception.occurrence_date,
                original_period=_weekly_period(by_day, session_id),
                original_room_id=original_room,
                notice=exception.notice,
            )
        )
    result.sort(key=lambda o: (o.date, o.period, o.session_id))
    return result


def _durations(problem: Problem) -> dict[str, int]:
    return {s.id: s.duration for s in problem.sessions}


Weekly = dict[int, list[tuple[str, int, str | None]]]


def _weekly_room(by_day: Weekly, session_id: str) -> str | None:
    return next(
        (room for entries in by_day.values() for sid, _, room in entries if sid == session_id), None
    )


def _weekly_period(by_day: Weekly, session_id: str) -> int | None:
    return next(
        (period for entries in by_day.values() for sid, period, _ in entries if sid == session_id),
        None,
    )


def _apply(base: Occurrence, exception: OccurrenceException) -> Occurrence:
    identifier = str(exception.id)
    if exception.kind == "cancelled":
        return replace(base, status="cancelled", exception_id=identifier, notice=exception.notice)
    if exception.kind == "relocated":
        return replace(
            base,
            status="relocated",
            room_id=str(exception.new_room_id),
            original_room_id=base.room_id,
            exception_id=identifier,
            notice=exception.notice,
        )
    return replace(
        base,
        status="moved",
        exception_id=identifier,
        moved_to_date=exception.new_date,
        moved_to_period=exception.new_period,
        notice=exception.notice,
    )


def session_ids_for(problem: Problem, **resource: uuid.UUID | None) -> set[str] | None:
    """Sessions of one instructor, one group (including the groups sharing its students) or
    none; ``None`` means no filter. Room filtering is done on dated occurrences."""
    from optiedt.evaluation.groups import GroupOverlap

    instructor_id = resource.get("instructor_id")
    group_id = resource.get("group_id")
    if instructor_id is None and group_id is None:
        return None
    result: set[str] = set()
    if instructor_id is not None:
        index = problem.instructor_index.get(str(instructor_id))
        result |= {s.id for s in problem.sessions if index is not None and index in s.instructors}
    if group_id is not None:
        index = problem.group_index.get(str(group_id))
        if index is not None:
            overlap = GroupOverlap(problem)
            result |= {
                s.id
                for s in problem.sessions
                if any(overlap.share_students(index, g) for g in s.groups)
            }
    return result
