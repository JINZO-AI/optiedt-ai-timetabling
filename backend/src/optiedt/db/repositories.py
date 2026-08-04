"""Database-backed `RunStore` and `AvailabilityStore` — FR-19.

These substitute the in-memory implementations Phase 4 left behind their
Protocols, and **no router changes**: that seam was the point of declaring them
as Protocols rather than as classes (`docs/dashboard.md`, Phase 4's dependency
note).

⚠️ **Invariant 6 is enforced by omission, and that is deliberate.** There is no
code path here that updates a candidate, a placement or a sub-score. A run's
candidates are written once — when a revision first carries them — and never
touched again, because a candidate's sub-scores describe its content and
editing it would leave them describing something that no longer exists. A
regenerated timetable is a NEW candidate under a NEW run. If a future change
needs `UPDATE candidates`, the change is wrong.

`save()` is called on every state transition, so it must be idempotent for the
parts that are already stored and additive for the parts that are not. It
updates the run's own mutable columns — state, timings, error — and inserts
checks, diagnosis and candidates only the first time they appear.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from optiedt.db.models import (
    AvailabilityRow,
    CandidateRow,
    DiagnosisRow,
    PlacementRow,
    PreAnalysisCheckRow,
    RunRow,
    RunWeightRow,
    SubScoreRow,
)
from optiedt.domain.entities import (
    Availability,
    Candidate,
    DiagnosisResult,
    Placement,
    Run,
    RunId,
    SubScore,
    TeacherId,
)
from optiedt.domain.enums import AvailabilityState, DeclarationSource, RunState
from optiedt.preanalysis.checks import CheckResult
from optiedt.services.runs import RunRecord

# ── domain <- rows ─────────────────────────────────────────────────────


def _to_record(row: RunRow) -> RunRecord:
    return RunRecord(
        run=Run(
            id=row.id,
            created_at=row.created_at,
            seed=row.seed,
            deterministic_budget=row.deterministic_budget,
            state=RunState(row.state),
            model_version=row.model_version,
        ),
        weights={w.criterion: w.weight for w in row.weights},
        candidates=tuple(_to_candidate(c) for c in row.candidates),
        pre_analysis=tuple(
            CheckResult(
                name=c.name,
                passed=c.passed,
                resource=c.resource,
                missing_quantity=c.missing_quantity,
                detail=c.detail,
            )
            for c in row.checks
        ),
        diagnosis=(
            DiagnosisResult(
                conflicting_codes=tuple(row.diagnosis.conflicting_codes),
                is_minimal=row.diagnosis.is_minimal,
                is_conclusive=row.diagnosis.is_conclusive,
                detail=row.diagnosis.detail,
            )
            if row.diagnosis is not None
            else None
        ),
        duplicates_removed=tuple(row.duplicates_removed),
        deterministic_time_used=row.deterministic_time_used,
        wall_clock_seconds=row.wall_clock_seconds,
        error=row.error,
    )


def _to_candidate(row: CandidateRow) -> Candidate:
    return Candidate(
        id=row.id,
        run=row.run_id,
        profile_name=row.profile_name,
        cost=row.cost,
        score=row.score,
        placements=tuple(
            Placement(session=p.session, slot=p.slot, room=p.room) for p in row.placements
        ),
        sub_scores=tuple(
            SubScore(criterion=s.criterion, raw_value=s.raw_value, normalised=s.normalised)
            for s in row.sub_scores
        ),
    )


# ── the run record ─────────────────────────────────────────────────────


class SqlRunStore:
    """Runs by id, in PostgreSQL. Substitutes `InMemoryRunStore`."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def create(self, record: RunRecord) -> None:
        with self._sessions() as session, session.begin():
            if session.get(RunRow, record.run.id) is not None:
                raise KeyError(f"run {record.run.id} already exists")
            row = RunRow(
                id=record.run.id,
                created_at=record.run.created_at,
                seed=record.run.seed,
                deterministic_budget=record.run.deterministic_budget,
                state=record.run.state.value,
                model_version=record.run.model_version,
                duplicates_removed=list(record.duplicates_removed),
                deterministic_time_used=record.deterministic_time_used,
                wall_clock_seconds=record.wall_clock_seconds,
                error=record.error,
            )
            row.weights = [
                RunWeightRow(run_id=record.run.id, criterion=code, weight=weight)
                for code, weight in sorted(record.weights.items())
            ]
            session.add(row)

    def get(self, run_id: RunId) -> RunRecord | None:
        with self._sessions() as session:
            row = session.get(RunRow, run_id)
            return _to_record(row) if row is not None else None

    def save(self, record: RunRecord) -> None:
        with self._sessions() as session, session.begin():
            row = session.get(RunRow, record.run.id)
            if row is None:
                raise KeyError(f"run {record.run.id} does not exist")

            row.state = record.run.state.value
            row.duplicates_removed = list(record.duplicates_removed)
            row.deterministic_time_used = record.deterministic_time_used
            row.wall_clock_seconds = record.wall_clock_seconds
            row.error = record.error

            if record.pre_analysis and not row.checks:
                row.checks = [
                    PreAnalysisCheckRow(
                        run_id=row.id,
                        ordinal=ordinal,
                        name=check.name,
                        passed=check.passed,
                        resource=check.resource,
                        missing_quantity=check.missing_quantity,
                        detail=check.detail,
                    )
                    for ordinal, check in enumerate(record.pre_analysis)
                ]

            if record.diagnosis is not None and row.diagnosis is None:
                row.diagnosis = DiagnosisRow(
                    run_id=row.id,
                    conflicting_codes=list(record.diagnosis.conflicting_codes),
                    is_minimal=record.diagnosis.is_minimal,
                    is_conclusive=record.diagnosis.is_conclusive,
                    detail=record.diagnosis.detail,
                )

            # Invariant 6: written once, never updated. `not row.candidates` is
            # the whole guard - a run that already carries candidates keeps the
            # ones it has, whatever a later revision claims.
            if record.candidates and not row.candidates:
                row.candidates = [
                    CandidateRow(
                        id=candidate.id,
                        run_id=row.id,
                        rank_order=rank,
                        profile_name=candidate.profile_name,
                        cost=candidate.cost,
                        score=candidate.score,
                        placements=[
                            PlacementRow(
                                candidate_id=candidate.id,
                                session=p.session,
                                slot=p.slot,
                                room=p.room,
                            )
                            for p in candidate.placements
                        ],
                        sub_scores=[
                            SubScoreRow(
                                candidate_id=candidate.id,
                                criterion=s.criterion,
                                raw_value=s.raw_value,
                                normalised=s.normalised,
                            )
                            for s in candidate.sub_scores
                        ],
                    )
                    for rank, candidate in enumerate(record.candidates)
                ]

    def all(self) -> tuple[RunRecord, ...]:
        with self._sessions() as session:
            rows = session.scalars(select(RunRow).order_by(RunRow.created_at.desc())).all()
            return tuple(_to_record(row) for row in rows)


# ── availability declarations ──────────────────────────────────────────


class SqlAvailabilityStore:
    """Teachers' declarations, in PostgreSQL. Substitutes the in-memory store.

    ⚠️ A teacher with no rows here has NOT declared anything, and the
    instance's generated rows stand for them. A teacher who declared "free all
    week" also has no rows — `build_declaration` stores only non-AVAILABLE
    cells, matching the instance's own convention. `declared_teachers()`
    therefore cannot be derived from the rows alone, so a declaration is
    recorded even when it is empty: `_DeclaredMarker` below is what keeps
    "asked and answered nothing" distinct from "never asked".
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def declarations(self, teacher: TeacherId) -> tuple[Availability, ...] | None:
        with self._sessions() as session:
            rows = session.scalars(
                select(AvailabilityRow)
                .where(AvailabilityRow.teacher == teacher)
                .order_by(AvailabilityRow.slot)
            ).all()
            if not rows:
                return None
            # An empty tuple is a real answer - "nothing unavailable" - and is
            # returned whenever the marker is present. Only NO rows at all
            # means the teacher was never asked.
            real = [r for r in rows if r.slot != _DECLARED_MARKER_SLOT]
            return tuple(
                Availability(
                    teacher=r.teacher,
                    slot=r.slot,
                    state=AvailabilityState(r.state),
                    semester=r.semester,
                    source=DeclarationSource(r.source),
                )
                for r in real
            )

    def declare(self, teacher: TeacherId, rows: tuple[Availability, ...]) -> None:
        with self._sessions() as session, session.begin():
            # Replace wholesale: a teacher's grid is the complete statement of
            # their week, so a slot they left free must clear a row that said
            # otherwise. Merging would make a declaration impossible to
            # withdraw (services/availability.py).
            session.execute(delete(AvailabilityRow).where(AvailabilityRow.teacher == teacher))
            semester = rows[0].semester if rows else _DEFAULT_SEMESTER
            session.add(
                AvailabilityRow(
                    teacher=teacher,
                    slot=_DECLARED_MARKER_SLOT,
                    state=AvailabilityState.AVAILABLE.value,
                    semester=semester,
                    source=DeclarationSource.TEACHER.value,
                )
            )
            session.add_all(
                AvailabilityRow(
                    teacher=row.teacher,
                    slot=row.slot,
                    state=row.state.value,
                    semester=row.semester,
                    source=row.source.value,
                )
                for row in rows
            )

    def declared_teachers(self) -> frozenset[TeacherId]:
        with self._sessions() as session:
            return frozenset(session.scalars(select(AvailabilityRow.teacher).distinct()).all())


_DECLARED_MARKER_SLOT = -1
"""Records that a teacher answered, even when they marked nothing unavailable.

⚠️ Not a placeholder for tidiness. `effective_availability` substitutes a
declaring teacher's rows for the generated ones, so "declared nothing
unavailable" must WITHDRAW the generated rows rather than leave them standing.
Without a marker, an empty declaration is indistinguishable from never having
been asked, and a teacher who said "I am free all week" would keep the
generated unavailability the instance invented for them.

Slot -1 cannot collide with a real slot index (they are 0..29) and is filtered
out of every read.
"""

_DEFAULT_SEMESTER = 2
"""Only reached for an empty declaration, which carries no semester of its own.
The reference instance is second semester (`calendar_config`)."""
