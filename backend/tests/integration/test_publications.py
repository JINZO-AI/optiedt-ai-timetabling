"""Approval, versioned publication, rebasing, restoring, dated occurrences, exceptions and
disruption planning."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, PermissionDenied
from optiedt.models import (
    Activity,
    CalendarEvent,
    Instructor,
    Publication,
    Solution,
    Term,
)
from optiedt.problem.snapshot import session_id
from optiedt.security.permissions import Principal
from optiedt.services import availability as availability_service
from optiedt.services import calendar, editing, exceptions, publications
from optiedt.services.auth import build_principal
from optiedt.services.editing import Move
from optiedt.services.exceptions import Request
from optiedt.services.reference import get_institution
from optiedt.services.solutions import encoded_placements
from tests import factories

pytestmark = pytest.mark.solver


def _setup(db: Session) -> tuple[factories.Institution, Term, Solution, Principal]:
    inst, term = factories.populated_term(db)
    draft = factories.solved_draft(db, term.id)
    return inst, term, draft, factories.admin_principal(db)


def _publish(db: Session, admin: Principal, solution: Solution) -> Publication:
    publications.submit(db, admin, solution.id, version=solution.version, note=None)
    publications.approve(db, admin, solution.id, version=solution.version, note="Looks good")
    return publications.publish(db, admin, solution.id, version=solution.version, note=None)


def _lectures(db: Session, term: Term) -> tuple[str, str, str]:
    activities = list(db.scalars(select(Activity).where(Activity.term_id == term.id)))
    lecture = next(a for a in activities if a.sessions_per_week == 2)
    tutorial = next(a for a in activities if a.sessions_per_week == 1)
    return (
        str(session_id(lecture.id, 1)),
        str(session_id(lecture.id, 2)),
        str(session_id(tutorial.id, 1)),
    )


def test_submit_approve_publish(db: Session) -> None:
    _, _, draft, admin = _setup(db)
    publication = _publish(db, admin, draft)
    assert publication.version_no == 1
    assert publication.is_current
    assert publication.summary["changes"]["added"] == 3
    assert draft.status == "published"
    assert (
        publications.publication_placements(db, publication.id)
        == encoded_placements(db, draft.id)[0]
    )
    with pytest.raises(Conflict) as again:
        publications.publish(db, admin, draft.id, version=draft.version, note=None)
    assert again.value.code == "wrong_status"


def test_only_valid_drafts_go_forward(db: Session) -> None:
    _, term, draft, admin = _setup(db)
    lecture, _, _ = _lectures(db, term)
    editing.apply_moves(
        db, admin, draft.id, version=draft.version, moves=[Move(lecture, None, None, None)]
    )
    with pytest.raises(Conflict) as refused:
        publications.submit(db, admin, draft.id, version=draft.version, note=None)
    assert refused.value.code == "not_valid"


def test_first_publication_needs_an_institution_wide_approver(db: Session) -> None:
    inst, _, draft, admin = _setup(db)
    head = build_principal(db, factories.user(db, "cs.head", [("department_head", inst.cs.id)]))
    publications.submit(db, admin, draft.id, version=draft.version, note=None)
    with pytest.raises(PermissionDenied):
        publications.approve(db, head, draft.id, version=draft.version, note=None)


def test_department_heads_approve_changes_within_their_department(db: Session) -> None:
    inst, term, draft, admin = _setup(db)
    _publish(db, admin, draft)
    copy = editing.duplicate(db, admin, draft.id)
    lecture, _, _ = _lectures(db, term)
    options = editing.suggestions(db, admin, copy.id, lecture)["valid"]
    target = next(o for o in options if not o["is_current"])
    editing.apply_moves(
        db,
        admin,
        copy.id,
        version=copy.version,
        moves=[Move(lecture, target["day"], target["period"], target["room_id"])],
    )
    publications.submit(db, admin, copy.id, version=copy.version, note=None)
    head = build_principal(db, factories.user(db, "cs.head", [("department_head", inst.cs.id)]))
    approved = publications.approve(db, head, copy.id, version=copy.version, note="Fine")
    assert approved.status == "approved"
    second = publications.publish(db, admin, copy.id, version=copy.version, note="Room change")
    assert second.version_no == 2
    assert second.summary["changes"]["moved"] + second.summary["changes"]["room"] == 1
    db.refresh(draft)
    assert draft.status == "archived"


def test_publishing_without_approval_when_the_institution_allows_it(db: Session) -> None:
    _, _, draft, admin = _setup(db)
    get_institution(db).approval_required = False
    db.flush()
    publication = publications.publish(db, admin, draft.id, version=draft.version, note=None)
    assert publication.version_no == 1


def test_a_stale_base_needs_a_rebase_that_keeps_the_drafts_own_changes(db: Session) -> None:
    _, term, draft, admin = _setup(db)
    first = _publish(db, admin, draft)
    lecture, _, tutorial = _lectures(db, term)
    mine = editing.duplicate(db, admin, draft.id, "Mine")
    theirs = editing.duplicate(db, admin, draft.id, "Theirs")
    assert mine.base_publication_id == first.id

    def move_somewhere(solution: Solution, session: str, avoid_day: int | None) -> list[object]:
        options = editing.suggestions(db, admin, solution.id, session)["valid"]
        target = next(o for o in options if not o["is_current"] and o["day"] != avoid_day)
        editing.apply_moves(
            db,
            admin,
            solution.id,
            version=solution.version,
            moves=[Move(session, target["day"], target["period"], target["room_id"])],
        )
        return [target["day"], target["period"], target["room_id"]]

    their_place = move_somewhere(theirs, tutorial, None)
    _publish(db, admin, theirs)
    # On another day than their tutorial, so the two changes cannot clash.
    my_place = move_somewhere(mine, lecture, int(their_place[0]))  # type: ignore[call-overload]
    publications.submit(db, admin, mine.id, version=mine.version, note=None)
    publications.approve(db, admin, mine.id, version=mine.version, note=None)
    with pytest.raises(Conflict) as stale:
        publications.publish(db, admin, mine.id, version=mine.version, note=None)
    assert stale.value.code == "rebase_needed"

    rebased = publications.rebase(db, admin, mine.id)
    placements, _ = encoded_placements(db, rebased.id)
    assert placements[lecture] == my_place  # my change
    assert placements[tutorial] == their_place  # their published change
    assert rebased.origin == "rebase"
    assert rebased.is_valid
    third = _publish(db, admin, rebased)
    assert third.version_no == 3


def test_data_changes_block_publication_until_rebased(db: Session) -> None:
    _, term, draft, admin = _setup(db)
    lecture, _, _ = _lectures(db, term)
    placements, _ = encoded_placements(db, draft.id)
    day, period, _ = placements[lecture]
    publications.submit(db, admin, draft.id, version=draft.version, note=None)
    publications.approve(db, admin, draft.id, version=draft.version, note=None)
    teacher = db.scalars(select(Instructor).where(Instructor.code == "T100")).one()
    periods = factories.term_periods(db, term.id)
    availability_service.put_grid(
        db,
        admin,
        term.id,
        "instructor",
        teacher.id,
        version=None,
        cells=[
            availability_service.Cell(term.weekdays[day], periods[period].id, "unavailable"),
        ],
        today=term.start_date,
    )
    with pytest.raises(Conflict) as changed:
        publications.publish(db, admin, draft.id, version=draft.version, note=None)
    assert changed.value.code == "data_changed"
    rebased = publications.rebase(db, admin, draft.id)
    codes = {v["code"] for v in rebased.evaluation["violations"]}
    assert "instructor_unavailable" in codes


def test_restoring_an_old_version_publishes_it_again(db: Session) -> None:
    _, term, draft, admin = _setup(db)
    first = _publish(db, admin, draft)
    copy = editing.duplicate(db, admin, draft.id)
    _, _, tutorial = _lectures(db, term)
    options = editing.suggestions(db, admin, copy.id, tutorial)["valid"]
    target = next(o for o in options if not o["is_current"])
    editing.apply_moves(
        db,
        admin,
        copy.id,
        version=copy.version,
        moves=[Move(tutorial, target["day"], target["period"], target["room_id"])],
    )
    second = _publish(db, admin, copy)
    restored = publications.restore(db, admin, first.id, note="Back to the first version")
    assert restored.version_no == 3
    assert restored.restored_from_id == first.id
    assert publications.publication_placements(db, restored.id) == (
        publications.publication_placements(db, first.id)
    )
    diff = publications.diff_publications(db, admin, restored.id, second.id)
    assert diff["counts"]["moved"] + diff["counts"]["room"] == 1
    assert diff["changes"][0]["label"]


# ── dated occurrences and exceptions ────────────────────────────────────


def _first(term: Term, placement: list[object]) -> date:
    """The first date the weekly placement occurs."""
    weekday = term.weekdays[int(placement[0])]  # type: ignore[call-overload]
    offset = (weekday - term.start_date.weekday()) % 7
    return term.start_date + timedelta(days=offset)


def test_occurrences_follow_the_term_calendar(db: Session) -> None:
    _, term, draft, admin = _setup(db)
    publication = _publish(db, admin, draft)
    lecture, _, _ = _lectures(db, term)
    placement = publications.publication_placements(db, publication.id)[lecture]
    first = _first(term, placement)
    db.add(
        CalendarEvent(
            start_date=first + timedelta(days=7),
            end_date=first + timedelta(days=7),
            kind="holiday",
            label="Holiday",
        )
    )
    db.flush()
    found = [
        o.date
        for o in calendar.occurrences(db, publication, first, first + timedelta(days=21))
        if o.session_id == lecture
    ]
    assert found == [first, first + timedelta(days=14), first + timedelta(days=21)]


def test_exceptions_cancel_relocate_and_reschedule(db: Session) -> None:
    _, term, draft, admin = _setup(db)
    publication = _publish(db, admin, draft)
    lecture, _, tutorial = _lectures(db, term)
    placements = publications.publication_placements(db, publication.id)
    lecture_day = _first(term, placements[lecture])
    tutorial_day = _first(term, placements[tutorial])

    exceptions.create(
        db,
        admin,
        publication.id,
        Request(lecture, lecture_day, "cancelled"),
        reason="Conference",
        notice="Lecture cancelled",
    )
    on_day = calendar.occurrences(db, publication, lecture_day, lecture_day)
    assert next(o for o in on_day if o.session_id == lecture).status == "cancelled"

    other_room = next(
        r for r in ("A-101", "A-102") if str(factories.room_id(db, r)) != placements[tutorial][2]
    )
    relocated = exceptions.create(
        db,
        admin,
        publication.id,
        Request(
            tutorial, tutorial_day, "relocated", new_room_id=str(factories.room_id(db, other_room))
        ),
        reason=None,
        notice=None,
    )
    with pytest.raises(Conflict) as twice:
        exceptions.create(
            db,
            admin,
            publication.id,
            Request(tutorial, tutorial_day, "cancelled"),
            reason=None,
            notice=None,
        )
    assert twice.value.code == "exception_exists"
    exceptions.revoke(db, admin, relocated.id, reason=None)

    with pytest.raises(Conflict) as small:
        exceptions.create(
            db,
            admin,
            publication.id,
            Request(
                tutorial,
                tutorial_day,
                "relocated",
                new_room_id=str(factories.room_id(db, "A-LAB1")),
            ),
            reason=None,
            notice=None,
        )
    assert "room type" in str(small.value.details["problems"])

    next_week = tutorial_day + timedelta(days=7)
    with pytest.raises(Conflict) as far:
        exceptions.create(
            db,
            admin,
            publication.id,
            Request(tutorial, tutorial_day, "rescheduled", new_date=next_week, new_period=0),
            reason=None,
            notice=None,
        )
    assert "same week" in str(far.value.details["problems"])


def test_new_versions_carry_exceptions_whose_session_did_not_move(db: Session) -> None:
    _, term, draft, admin = _setup(db)
    publication = _publish(db, admin, draft)
    lecture, _, tutorial = _lectures(db, term)
    placements = publications.publication_placements(db, publication.id)
    for session in (lecture, tutorial):
        exceptions.create(
            db,
            admin,
            publication.id,
            Request(session, _first(term, placements[session]), "cancelled"),
            reason=None,
            notice=None,
        )
    copy = editing.duplicate(db, admin, draft.id)
    options = editing.suggestions(db, admin, copy.id, tutorial)["valid"]
    target = next(o for o in options if not o["is_current"] and o["day"] != placements[tutorial][0])
    editing.apply_moves(
        db,
        admin,
        copy.id,
        version=copy.version,
        moves=[Move(tutorial, target["day"], target["period"], target["room_id"])],
    )
    second = _publish(db, admin, copy)
    carried = exceptions.list_exceptions(db, admin, second.id)
    assert [str(e.session_id) for e in carried] == [lecture]
    assert [d["session_id"] for d in second.summary["exceptions_dropped"]] == [tutorial]


def test_a_closed_room_gets_relocations_proposed_and_applied(db: Session) -> None:
    _, term, draft, admin = _setup(db)
    publication = _publish(db, admin, draft)
    _, _, tutorial = _lectures(db, term)
    placements = publications.publication_placements(db, publication.id)
    day = _first(term, placements[tutorial])
    room = placements[tutorial][2]
    assert room is not None
    plan = exceptions.plan_disruption(
        db,
        admin,
        publication.id,
        resource_kind="room",
        resource_id=uuid.UUID(room),
        start=day,
        end=day,
    )
    assert [entry["action"] for entry in plan] == ["relocated"]
    entry = plan[0]
    created = exceptions.apply_disruption(
        db,
        admin,
        publication.id,
        [Request(entry["session_id"], day, "relocated", new_room_id=entry["new_room_id"])],
        reason="Water leak",
        notice="Room change today",
    )
    assert len(created) == 1
    moved = next(
        o for o in calendar.occurrences(db, publication, day, day) if o.session_id == tutorial
    )
    assert moved.status == "relocated"
    assert moved.room_id == entry["new_room_id"]
    assert moved.original_room_id == room
