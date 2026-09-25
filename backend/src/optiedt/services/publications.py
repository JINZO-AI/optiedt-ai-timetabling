"""The approval workflow and versioned publications (ADR 0012).

A valid draft is submitted, approved (or returned) and published as a numbered, immutable
publication that becomes the term's current timetable. A draft records the publication it
was derived from; publishing is refused when that is no longer current, and ``rebase`` brings
the draft's own changes onto the current publication and the current data.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from optiedt.errors import Conflict, NotFound, PermissionDenied
from optiedt.evaluation.evaluator import Evaluator
from optiedt.models import (
    OccurrenceException,
    Publication,
    PublicationAssignment,
    Solution,
    SolutionChange,
)
from optiedt.problem.encoding import Codec, EncodedPlacements
from optiedt.problem.model import Problem, build_problem
from optiedt.security.permissions import Permission, Principal
from optiedt.services import audit
from optiedt.services.crud import check_version
from optiedt.services.problems import problem_for
from optiedt.services.reference import get_institution
from optiedt.services.snapshots import compile_snapshot, store_snapshot
from optiedt.services.solutions import (
    create_solution,
    encoded_placements,
    get_solution,
    objective_config,
)


def require_read(principal: Principal) -> None:
    if not (
        principal.can(Permission.PUBLICATIONS_READ) or principal.can(Permission.SOLUTIONS_READ)
    ):
        raise PermissionDenied()


def current_publication(db: Session, term_id: uuid.UUID) -> Publication | None:
    return db.scalar(
        select(Publication).where(Publication.term_id == term_id, Publication.is_current)
    )


def get_publication(db: Session, publication_id: uuid.UUID) -> Publication:
    publication = db.get(Publication, publication_id)
    if publication is None:
        raise NotFound("Publication")
    return publication


def publication_placements(db: Session, publication_id: uuid.UUID) -> EncodedPlacements:
    return {
        str(row.session_id): [row.day, row.period, str(row.room_id) if row.room_id else None]
        for row in db.scalars(
            select(PublicationAssignment).where(
                PublicationAssignment.publication_id == publication_id
            )
        )
    }


def _log(
    db: Session, principal: Principal, solution: Solution, kind: str, summary: str, note: str | None
) -> None:
    seq = db.scalar(
        select(func.max(SolutionChange.seq)).where(SolutionChange.solution_id == solution.id)
    )
    db.add(
        SolutionChange(
            solution_id=solution.id,
            seq=int(seq or 0) + 1,
            actor_id=principal.user_id,
            actor_label=principal.label,
            kind=kind,
            summary=summary,
            reason=note,
        )
    )


def _changed_departments(
    problem: Problem, before: EncodedPlacements, after: EncodedPlacements
) -> set[uuid.UUID]:
    """Departments of the sessions placed differently in ``after`` than in ``before``."""
    codec = Codec(problem)
    departments: set[uuid.UUID] = set()
    for session_id in set(before) | set(after):
        if before.get(session_id) == after.get(session_id):
            continue
        s = codec.session_index.get(session_id)
        if s is not None:
            activity = problem.activities[problem.sessions[s].activity]
            departments.add(uuid.UUID(activity.department_id))
    return departments


def _require_over_changes(
    db: Session, principal: Principal, permission: Permission, solution: Solution, action: str
) -> None:
    """Institution-wide rights, or rights over every department whose sessions differ from
    the current publication; the first publication of a term needs institution-wide rights."""
    scope = principal.scope(permission)
    if scope.is_empty:
        raise PermissionDenied()
    if scope.everywhere:
        return
    current = current_publication(db, solution.term_id)
    if current is None:
        raise PermissionDenied(
            f"The first timetable of a term needs institution-wide rights to {action}."
        )
    placements, _ = encoded_placements(db, solution.id)
    changed = _changed_departments(
        problem_for(db, solution.snapshot_id), publication_placements(db, current.id), placements
    )
    if not scope.covers_all(changed):
        raise PermissionDenied(
            f"This timetable changes departments outside your scope to {action}."
        )


def _require_valid(solution: Solution) -> None:
    if not solution.is_valid:
        raise Conflict(
            "Only complete timetables without hard violations can go forward. "
            f"This one has {len(solution.evaluation.get('unscheduled', []))} unscheduled "
            f"session(s) and {solution.hard_violation_count} hard violation(s).",
            code="not_valid",
        )


# ── workflow ───────────────────────────────────────────────────────────


def submit(
    db: Session, principal: Principal, solution_id: uuid.UUID, *, version: int, note: str | None
) -> Solution:
    principal.require(Permission.SOLUTIONS_EDIT)
    solution = get_solution(db, solution_id)
    check_version(solution, version, "timetable")
    if solution.status != "draft":
        raise Conflict("Only drafts can be submitted.", code="wrong_status")
    _require_valid(solution)
    solution.status = "pending_approval"
    solution.submitted_by_id = principal.user_id
    solution.submitted_at = datetime.now(UTC)
    solution.review_note = note
    _log(db, principal, solution, "submit", "Submitted for approval", note)
    db.flush()
    audit.record(
        db,
        principal,
        action="solution.submit",
        entity_type="solution",
        entity_id=solution.id,
        summary=f"Submitted {solution.name} for approval",
        reason=note,
        term_id=solution.term_id,
    )
    return solution


def approve(
    db: Session, principal: Principal, solution_id: uuid.UUID, *, version: int, note: str | None
) -> Solution:
    solution = get_solution(db, solution_id)
    _require_over_changes(db, principal, Permission.SOLUTIONS_APPROVE, solution, "approve")
    check_version(solution, version, "timetable")
    if solution.status != "pending_approval":
        raise Conflict("Only submitted timetables can be approved.", code="wrong_status")
    _require_valid(solution)
    solution.status = "approved"
    solution.approved_by_id = principal.user_id
    solution.approved_at = datetime.now(UTC)
    solution.review_note = note
    _log(db, principal, solution, "approve", "Approved", note)
    db.flush()
    audit.record(
        db,
        principal,
        action="solution.approve",
        entity_type="solution",
        entity_id=solution.id,
        summary=f"Approved {solution.name}",
        reason=note,
        term_id=solution.term_id,
    )
    return solution


def return_to_draft(
    db: Session, principal: Principal, solution_id: uuid.UUID, *, version: int, note: str
) -> Solution:
    """An approver sends a submitted timetable back with a note; its submitter may withdraw it."""
    solution = get_solution(db, solution_id)
    is_submitter = solution.submitted_by_id == principal.user_id
    if not (principal.can(Permission.SOLUTIONS_APPROVE) or is_submitter):
        raise PermissionDenied()
    check_version(solution, version, "timetable")
    if solution.status not in ("pending_approval", "approved"):
        raise Conflict(
            "Only submitted or approved timetables can be returned.", code="wrong_status"
        )
    solution.status = "draft"
    solution.review_note = note
    solution.approved_by_id = None
    solution.approved_at = None
    _log(db, principal, solution, "return", "Returned to draft", note)
    db.flush()
    audit.record(
        db,
        principal,
        action="solution.return",
        entity_type="solution",
        entity_id=solution.id,
        summary=f"Returned {solution.name} to draft",
        reason=note,
        term_id=solution.term_id,
    )
    return solution


# ── publishing ─────────────────────────────────────────────────────────


def _assignments_hash(placements: EncodedPlacements) -> str:
    text = json.dumps(sorted(placements.items()), separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def _current_snapshot(db: Session, solution: Solution) -> tuple[uuid.UUID, Problem]:
    """The snapshot of the term's current data; checks that the timetable is still valid on
    it when the data changed since the timetable was made."""
    snapshot = compile_snapshot(db, solution.term_id)
    problem = build_problem(snapshot)
    stored = store_snapshot(db, solution.term_id, snapshot)
    if stored.id == solution.snapshot_id:
        return stored.id, problem
    placements, _ = encoded_placements(db, solution.id)
    codec = Codec(problem)
    config = objective_config(solution, codec)
    evaluation = Evaluator(problem, config).evaluate(codec.placements(placements))
    lost = [s for s in placements if s not in codec.session_index]
    if evaluation.violations or not evaluation.complete or lost:
        problems = [v.message for v in evaluation.violations[:5]]
        raise Conflict(
            "The data changed since this timetable was made and it no longer fits: "
            f"{len(evaluation.violations)} hard violation(s), "
            f"{len(evaluation.unscheduled)} session(s) without a place. Rebase it.",
            code="data_changed",
            violations=problems,
        )
    return stored.id, problem


def _carry_exceptions(
    db: Session,
    previous: Publication | None,
    new: Publication,
    placements: EncodedPlacements,
) -> list[dict[str, Any]]:
    """Copies active exceptions whose session keeps its weekly placement; returns the others."""
    if previous is None:
        return []
    old = publication_placements(db, previous.id)
    dropped = []
    for exception in db.scalars(
        select(OccurrenceException).where(
            OccurrenceException.publication_id == previous.id,
            OccurrenceException.revoked_at.is_(None),
        )
    ):
        key = str(exception.session_id)
        if key in placements and placements[key] == old.get(key):
            db.add(
                OccurrenceException(
                    publication_id=new.id,
                    session_id=exception.session_id,
                    occurrence_date=exception.occurrence_date,
                    kind=exception.kind,
                    new_date=exception.new_date,
                    new_period=exception.new_period,
                    new_room_id=exception.new_room_id,
                    reason=exception.reason,
                    notice=exception.notice,
                    created_by_id=exception.created_by_id,
                )
            )
        else:
            dropped.append(
                {
                    "session_id": key,
                    "date": exception.occurrence_date.isoformat(),
                    "kind": exception.kind,
                }
            )
    return dropped


def _new_publication(
    db: Session,
    principal: Principal,
    *,
    term_id: uuid.UUID,
    solution_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    placements: EncodedPlacements,
    note: str | None,
    restored_from: Publication | None = None,
) -> Publication:
    previous = current_publication(db, term_id)
    number = db.scalar(
        select(func.coalesce(func.max(Publication.version_no), 0)).where(
            Publication.term_id == term_id
        )
    )
    if previous is not None:
        db.execute(
            update(Publication).where(Publication.id == previous.id).values(is_current=False)
        )
        db.flush()
    diff = difference(publication_placements(db, previous.id) if previous else {}, placements)
    publication = Publication(
        term_id=term_id,
        version_no=int(number or 0) + 1,
        solution_id=solution_id,
        snapshot_id=snapshot_id,
        content_hash=_assignments_hash(placements),
        is_current=True,
        restored_from_id=restored_from.id if restored_from else None,
        published_by_id=principal.user_id,
        note=note,
        summary={},
    )
    db.add(publication)
    db.flush()
    db.add_all(
        PublicationAssignment(
            publication_id=publication.id,
            session_id=uuid.UUID(session_id),
            day=day,
            period=period,
            room_id=uuid.UUID(room_id) if room_id else None,
        )
        for session_id, (day, period, room_id) in placements.items()
    )
    dropped = _carry_exceptions(db, previous, publication, placements)
    publication.summary = {
        "sessions": len(placements),
        "previous_version": previous.version_no if previous else None,
        "changes": diff["counts"],
        "exceptions_dropped": dropped,
    }
    db.flush()
    return publication


def publish(
    db: Session, principal: Principal, solution_id: uuid.UUID, *, version: int, note: str | None
) -> Publication:
    solution = get_solution(db, solution_id)
    _require_over_changes(db, principal, Permission.PUBLICATIONS_PUBLISH, solution, "publish")
    check_version(solution, version, "timetable")
    institution = get_institution(db)
    allowed = (
        ("approved",)
        if institution.approval_required
        else ("draft", "pending_approval", "approved")
    )
    if solution.status not in allowed:
        raise Conflict(
            "This timetable must be approved before it is published."
            if institution.approval_required
            else "This timetable cannot be published in its current state.",
            code="wrong_status",
        )
    _require_valid(solution)
    current = current_publication(db, solution.term_id)
    if solution.base_publication_id != (current.id if current else None):
        raise Conflict(
            "Another version of the timetable was published since this one was made. "
            "Rebase it onto the current version.",
            code="rebase_needed",
            current_publication_id=str(current.id) if current else None,
        )
    snapshot_id, _ = _current_snapshot(db, solution)
    placements, _ = encoded_placements(db, solution.id)
    publication = _new_publication(
        db,
        principal,
        term_id=solution.term_id,
        solution_id=solution.id,
        snapshot_id=snapshot_id,
        placements=placements,
        note=note,
    )
    db.execute(
        update(Solution)
        .where(Solution.term_id == solution.term_id, Solution.status == "published")
        .values(status="archived")
    )
    solution.status = "published"
    _log(db, principal, solution, "publish", f"Published as version {publication.version_no}", note)
    db.flush()
    audit.record(
        db,
        principal,
        action="publication.publish",
        entity_type="publication",
        entity_id=publication.id,
        summary=f"Published {solution.name} as version {publication.version_no}",
        reason=note,
        term_id=solution.term_id,
        changes=publication.summary["changes"],
    )
    return publication


def restore(
    db: Session, principal: Principal, publication_id: uuid.UUID, *, note: str | None
) -> Publication:
    """Publishes an earlier version's content again, as a new version."""
    source = get_publication(db, publication_id)
    if source.is_current:
        raise Conflict("This version is already the current one.", code="already_current")
    principal.require_everywhere(Permission.PUBLICATIONS_PUBLISH)
    placements = publication_placements(db, source.id)
    publication = _new_publication(
        db,
        principal,
        term_id=source.term_id,
        solution_id=source.solution_id,
        snapshot_id=source.snapshot_id,
        placements=placements,
        note=note,
        restored_from=source,
    )
    audit.record(
        db,
        principal,
        action="publication.restore",
        entity_type="publication",
        entity_id=publication.id,
        summary=f"Restored version {source.version_no} as version {publication.version_no}",
        reason=note,
        term_id=source.term_id,
    )
    return publication


def difference(before: EncodedPlacements, after: EncodedPlacements) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    counts = dict.fromkeys(("moved", "room", "added", "removed"), 0)
    for session_id in sorted(set(before) | set(after)):
        old, new = before.get(session_id), after.get(session_id)
        if old == new:
            continue
        if old is None:
            kind = "added"
        elif new is None:
            kind = "removed"
        elif old[:2] == new[:2]:
            kind = "room"
        else:
            kind = "moved"
        counts[kind] += 1
        changes.append({"session_id": session_id, "kind": kind, "before": old, "after": new})
    return {"counts": counts, "changes": changes}


def diff_publications(
    db: Session, principal: Principal, publication_id: uuid.UUID, against_id: uuid.UUID | None
) -> dict[str, Any]:
    """Differences from ``against`` (by default the previous version) to this publication."""
    require_read(principal)
    publication = get_publication(db, publication_id)
    if against_id is None:
        previous = db.scalar(
            select(Publication).where(
                Publication.term_id == publication.term_id,
                Publication.version_no == publication.version_no - 1,
            )
        )
    else:
        previous = get_publication(db, against_id)
        if previous.term_id != publication.term_id:
            raise Conflict("Both versions must belong to the same term.", code="different_terms")
    before = publication_placements(db, previous.id) if previous else {}
    result = difference(before, publication_placements(db, publication.id))
    problem = problem_for(db, publication.snapshot_id)
    codec = Codec(problem)
    for change in result["changes"]:
        s = codec.session_index.get(change["session_id"])
        change["label"] = problem.describe_session(problem.sessions[s]) if s is not None else None
    result["from_version"] = previous.version_no if previous else None
    result["to_version"] = publication.version_no
    return result


# ── rebasing ───────────────────────────────────────────────────────────


def rebase(db: Session, principal: Principal, solution_id: uuid.UUID) -> Solution:
    """A new draft on the current data and the current publication, carrying the source's own
    changes (relative to the publication it was derived from). Its evaluation shows what no
    longer fits; repair or edit from there."""
    principal.require(Permission.SOLUTIONS_EDIT)
    source = get_solution(db, solution_id)
    snapshot = compile_snapshot(db, source.term_id)
    problem = build_problem(snapshot)
    stored = store_snapshot(db, source.term_id, snapshot)
    known_sessions = {s.id for s in problem.sessions}
    known_rooms = set(problem.room_index)
    own, locked = encoded_placements(db, source.id)
    current = current_publication(db, source.term_id)
    placements = dict(own)
    if current is not None and source.base_publication_id != current.id:
        base = (
            publication_placements(db, source.base_publication_id)
            if source.base_publication_id
            else {}
        )
        placements = publication_placements(db, current.id)
        for session_id in set(own) | set(base):
            if own.get(session_id) != base.get(session_id):
                if session_id in own:
                    placements[session_id] = own[session_id]
                else:
                    placements.pop(session_id, None)
    kept = {
        session_id: [day, period, room_id if room_id in known_rooms else None]
        for session_id, (day, period, room_id) in placements.items()
        if session_id in known_sessions
    }
    config = {k: v for k, v in source.objective_config.items() if k != "reference"}
    draft = create_solution(
        db,
        term_id=source.term_id,
        snapshot_id=stored.id,
        name=f"{source.name} (rebased)",
        origin="rebase",
        objective_config=config,
        placements=kept,
        locked={s for s in locked if s in kept},
        profile_code=source.profile_code,
        parent_id=source.id,
        created_by_id=principal.user_id,
    )
    draft.base_publication_id = current.id if current else None
    db.flush()
    audit.record(
        db,
        principal,
        action="solution.rebase",
        entity_type="solution",
        entity_id=draft.id,
        summary=(
            f"Rebased {source.name}: {len(kept)} of {len(known_sessions)} sessions placed, "
            f"{draft.hard_violation_count} hard violation(s)"
        ),
        term_id=source.term_id,
    )
    return draft
