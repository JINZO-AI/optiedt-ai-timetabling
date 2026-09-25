"""Editing drafts: validated moves, forced placements, locks, suggestions, copies and the
change log."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, PermissionDenied, StaleVersion
from optiedt.models import Activity, Solution, SolutionAssignment, SolutionChange
from optiedt.problem.snapshot import session_id
from optiedt.services import editing
from optiedt.services.auth import build_principal
from optiedt.services.editing import Move
from optiedt.services.solutions import encoded_placements
from tests import factories

pytestmark = pytest.mark.solver


def _draft(db: Session) -> tuple[Solution, dict[str, str]]:
    """A solved draft and the session ids of its lectures and tutorial."""
    _, term = factories.populated_term(db)
    draft = factories.solved_draft(db, term.id)
    ids: dict[str, str] = {}
    for activity in db.scalars(select(Activity).where(Activity.term_id == term.id)):
        if activity.sessions_per_week == 2:
            ids["lecture1"] = str(session_id(activity.id, 1))
            ids["lecture2"] = str(session_id(activity.id, 2))
        else:
            ids["tutorial"] = str(session_id(activity.id, 1))
    return draft, ids


def _free_slot(db: Session, draft: Solution, avoid_days: set[int]) -> tuple[int, int]:
    placements, _ = encoded_placements(db, draft.id)
    taken = {(d, p) for d, p, _ in placements.values()}
    return next(
        (d, p)
        for d in range(5)
        for p in (1, 2)
        if d not in avoid_days and (d, p) not in taken and (d, p - 1) not in taken
    )


def test_a_valid_move_is_applied_logged_and_re_evaluated(db: Session) -> None:
    draft, ids = _draft(db)
    admin = factories.admin_principal(db)
    placements, _ = encoded_placements(db, draft.id)
    lecture = placements[ids["lecture1"]]
    other_day = placements[ids["lecture2"]][0]
    day, period = _free_slot(db, draft, {other_day, lecture[0], 0})
    version = draft.version

    preview = editing.preview_moves(
        db, admin, draft.id, [Move(ids["lecture1"], day, period, lecture[2])]
    )
    assert preview["valid"]
    assert encoded_placements(db, draft.id)[0][ids["lecture1"]] == lecture  # nothing changed

    solution, result = editing.apply_moves(
        db,
        admin,
        draft.id,
        version=version,
        moves=[Move(ids["lecture1"], day, period, lecture[2])],
        reason="Room booked for an exam",
    )
    assert result["valid"]
    assert solution.version > version
    assert encoded_placements(db, draft.id)[0][ids["lecture1"]] == [day, period, lecture[2]]
    change = db.scalars(select(SolutionChange).where(SolutionChange.solution_id == draft.id)).one()
    assert change.kind == "move"
    assert change.reason == "Room booked for an exam"
    assert change.before == {"day": lecture[0], "period": lecture[1], "room_id": lecture[2]}
    assert "→" in change.summary
    assert solution.evaluation["edited"] is True
    assert solution.is_valid

    with pytest.raises(StaleVersion):
        editing.apply_moves(db, admin, draft.id, version=version, moves=[])


def test_a_conflicting_move_is_refused_unless_forced(db: Session) -> None:
    draft, ids = _draft(db)
    admin = factories.admin_principal(db)
    placements, _ = encoded_placements(db, draft.id)
    tutorial = placements[ids["tutorial"]]
    lecture = placements[ids["lecture1"]]
    # Same students (the cohort and its group G1) at the same time.
    clash = Move(ids["lecture1"], tutorial[0], tutorial[1], lecture[2])
    with pytest.raises(Conflict) as refused:
        editing.apply_moves(db, admin, draft.id, version=draft.version, moves=[clash])
    assert refused.value.code == "move_invalid"
    introduced = refused.value.details["preview"]["introduced"]  # type: ignore[index]
    assert {v["code"] for v in introduced} >= {"student_conflict"}

    solution, _ = editing.apply_moves(
        db, admin, draft.id, version=draft.version, moves=[clash], force=True
    )
    assert solution.hard_violation_count > 0
    assert not solution.is_valid


def test_unscheduling_and_locks(db: Session) -> None:
    draft, ids = _draft(db)
    admin = factories.admin_principal(db)
    solution = editing.set_locks(
        db, admin, draft.id, version=draft.version, session_ids=[ids["tutorial"]], locked=True
    )
    with pytest.raises(Conflict) as locked:
        editing.apply_moves(
            db,
            admin,
            draft.id,
            version=solution.version,
            moves=[Move(ids["tutorial"], None, None, None)],
        )
    assert locked.value.code == "locked"
    solution = editing.set_locks(
        db, admin, draft.id, version=solution.version, session_ids=[ids["tutorial"]], locked=False
    )
    solution, _ = editing.apply_moves(
        db,
        admin,
        draft.id,
        version=solution.version,
        moves=[Move(ids["tutorial"], None, None, None)],
    )
    assert not solution.is_complete
    assert ids["tutorial"] in solution.evaluation["unscheduled"]
    kinds = list(
        db.scalars(
            select(SolutionChange.kind)
            .where(SolutionChange.solution_id == draft.id)
            .order_by(SolutionChange.seq)
        )
    )
    assert kinds == ["lock", "unlock", "unschedule"]


def test_suggestions_rank_valid_places_and_explain_blocked_ones(db: Session) -> None:
    draft, ids = _draft(db)
    admin = factories.admin_principal(db)
    result = editing.suggestions(db, admin, draft.id, ids["lecture1"])
    assert result["valid_count"] > 0
    assert any(option["is_current"] for option in result["valid"])
    tiers = [option["tier_deltas"] for option in result["valid"]]
    assert tiers == sorted(tiers)
    assert result["blocked"]
    assert all(option["violations"] for option in result["blocked"])


def test_department_editors_only_move_their_departments_sessions(db: Session) -> None:
    draft, ids = _draft(db)
    physics_department = factories.department(db, "PHYS", "Physics")
    account = factories.user(db, "physics.officer", [("scheduling_officer", physics_department.id)])
    physics = build_principal(db, account)
    placements, _ = encoded_placements(db, draft.id)
    lecture = placements[ids["lecture1"]]
    with pytest.raises(PermissionDenied):
        editing.apply_moves(
            db,
            physics,
            draft.id,
            version=draft.version,
            moves=[Move(ids["lecture1"], lecture[0], lecture[1], lecture[2])],
        )


def test_approved_timetables_are_read_only_but_can_be_copied(db: Session) -> None:
    draft, ids = _draft(db)
    admin = factories.admin_principal(db)
    editing.set_locks(
        db, admin, draft.id, version=draft.version, session_ids=[ids["tutorial"]], locked=True
    )
    draft.status = "approved"
    db.flush()
    with pytest.raises(Conflict) as refused:
        editing.apply_moves(db, admin, draft.id, version=draft.version, moves=[])
    assert refused.value.code == "not_editable"
    copy = editing.duplicate(db, admin, draft.id)
    assert copy.status == "draft"
    assert copy.parent_id == draft.id
    assert copy.origin == "copy"
    assert encoded_placements(db, copy.id) == encoded_placements(db, draft.id)
    locked = db.scalars(
        select(SolutionAssignment.session_id).where(
            SolutionAssignment.solution_id == copy.id, SolutionAssignment.locked
        )
    ).all()
    assert [str(s) for s in locked] == [ids["tutorial"]]
