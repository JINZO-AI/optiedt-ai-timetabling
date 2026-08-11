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

from datetime import UTC, date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from optiedt.core.security import hash_password, verify_password
from optiedt.db.models import (
    AvailabilityRow,
    CalendarOverrideRow,
    CandidateRow,
    DiagnosisRow,
    PlacementRow,
    PreAnalysisCheckRow,
    PublicationRow,
    RunRow,
    RunWeightRow,
    SubScoreRow,
    UserRow,
)
from optiedt.domain.entities import (
    Availability,
    Candidate,
    CandidateId,
    DiagnosisResult,
    Holiday,
    Placement,
    Publication,
    Run,
    RunId,
    RunOrigin,
    RunOverrides,
    SubScore,
    TeacherId,
    User,
)
from optiedt.domain.enums import AvailabilityState, DeclarationSource, RunState, UserRole
from optiedt.preanalysis.checks import CheckResult
from optiedt.services.calendar import EMPTY, CalendarEdit, CalendarOverrides, ShortenedDay
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
        origin=(
            RunOrigin(
                run=row.origin_run_id,
                candidate=row.origin_candidate_id or "",
                action_kind=row.origin_action_kind or "",
                action_detail=row.origin_action_detail or "",
            )
            if row.origin_run_id is not None
            else None
        ),
        overrides=_to_overrides(row.overrides or {}),
    )


def _to_overrides(stored: dict[str, list[list[str | int]]]) -> RunOverrides:
    """JSON back into the domain type.

    Tuples come back from JSON as lists, so every element is rebuilt rather
    than cast. A frozenset of lists would not even be constructible, which is
    the kind of error worth having the type system catch here rather than at
    the next solve.
    """
    return RunOverrides(
        locked_placements=frozenset(
            Placement(session=str(p[0]), slot=int(p[1]), room=str(p[2]))
            for p in stored.get("locked_placements", [])
        ),
        excluded_slots=frozenset((str(p[0]), int(p[1])) for p in stored.get("excluded_slots", [])),
        excluded_rooms=frozenset((str(p[0]), str(p[1])) for p in stored.get("excluded_rooms", [])),
    )


def _from_overrides(overrides: RunOverrides) -> dict[str, list[list[str | int]]]:
    """The domain type into JSON, sorted.

    Sorted because a frozenset has no order and PostgreSQL stores what it is
    given: an unsorted dump would make two identical override sets serialise
    differently, so a stored run would not compare equal to itself across a
    rewrite. That is exactly the kind of drift
    `tests/integration/test_store_contract.py` exists to catch.
    """
    return {
        "locked_placements": [
            [p.session, p.slot, p.room]
            for p in sorted(overrides.locked_placements, key=lambda p: (p.session, p.slot, p.room))
        ],
        "excluded_slots": [[s, t] for s, t in sorted(overrides.excluded_slots)],
        "excluded_rooms": [[s, r] for s, r in sorted(overrides.excluded_rooms)],
    }


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
                origin_run_id=record.origin.run if record.origin else None,
                origin_candidate_id=record.origin.candidate if record.origin else None,
                origin_action_kind=record.origin.action_kind if record.origin else None,
                origin_action_detail=record.origin.action_detail if record.origin else None,
                overrides=_from_overrides(record.overrides),
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


class SqlPublicationStore:
    """Publications in PostgreSQL — the trace half of FR-19.

    ⚠️ Publishing the same candidate twice REPLACES the record rather than
    adding a second. Publishing is idempotent by intention: the department
    publishes *a* timetable, and a history of "published, published again" is
    not something any requirement asks for or any screen shows. If a change
    ever needs that history, it needs a new table, not a relaxed primary key.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def publish(self, publication: Publication) -> None:
        with self._sessions() as session, session.begin():
            existing = session.scalar(
                select(PublicationRow).where(PublicationRow.candidate_id == publication.candidate)
            )
            if existing is not None:
                existing.published_at = publication.published_at
                existing.published_by = publication.user
                return
            session.add(
                PublicationRow(
                    id=f"{publication.run}:{publication.candidate}",
                    candidate_id=publication.candidate,
                    run_id=publication.run,
                    published_at=publication.published_at,
                    published_by=publication.user,
                )
            )

    def all(self) -> tuple[Publication, ...]:
        with self._sessions() as session:
            rows = session.scalars(
                select(PublicationRow).order_by(PublicationRow.published_at.desc())
            ).all()
            return tuple(_to_publication(row) for row in rows)

    def for_candidate(self, candidate: CandidateId) -> Publication | None:
        with self._sessions() as session:
            row = session.scalar(
                select(PublicationRow).where(PublicationRow.candidate_id == candidate)
            )
            return _to_publication(row) if row is not None else None


def _to_publication(row: PublicationRow) -> Publication:
    return Publication(
        candidate=row.candidate_id,
        run=row.run_id,
        published_at=row.published_at,
        user=row.published_by,
    )


class SqlUserStore:
    """Accounts in PostgreSQL — FR-11.

    ⚠️ The hash is read inside `authenticate` and returned by nothing. See
    `services/users.py` for why that seam matters.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def by_username(self, username: str) -> User | None:
        with self._sessions() as session:
            row = session.scalar(select(UserRow).where(UserRow.username == username))
            return _to_user(row) if row is not None else None

    def authenticate(self, username: str, password: str) -> User | None:
        with self._sessions() as session:
            row = session.scalar(select(UserRow).where(UserRow.username == username))
        if row is None:
            # Hash anyway, so that an unknown username and a wrong password
            # take comparable time. Without it, the response time alone tells
            # an attacker which usernames exist.
            verify_password(password, _TIMING_DECOY)
            return None
        return _to_user(row) if verify_password(password, row.password_hash) else None

    def create(self, user: User, password: str) -> None:
        with self._sessions() as session, session.begin():
            if session.scalar(select(UserRow).where(UserRow.username == user.username)):
                raise KeyError(f"user {user.username} already exists")
            session.add(
                UserRow(
                    id=user.id,
                    username=user.username,
                    password_hash=hash_password(password),
                    role=user.role.value,
                    teacher=user.teacher,
                    group=user.group,
                )
            )

    def delete(self, username: str) -> bool:
        """Remove an account. No cascade reaches anything else, by design.

        A publication records `published_by` as a **username string**, never a
        foreign key, so removing the account that published a timetable leaves
        the record of who published it intact. That is the honest outcome: the
        act happened, and the department's evidence of it must not depend on
        the author still having access.
        """
        with self._sessions() as session, session.begin():
            row = session.scalar(select(UserRow).where(UserRow.username == username))
            if row is None:
                return False
            session.delete(row)
            return True

    def all(self) -> tuple[User, ...]:
        with self._sessions() as session:
            rows = session.scalars(select(UserRow).order_by(UserRow.username)).all()
            return tuple(_to_user(row) for row in rows)


def _to_user(row: UserRow) -> User:
    return User(
        id=row.id,
        username=row.username,
        role=UserRole(row.role),
        teacher=row.teacher,
        group=row.group,
    )


# ── The calendar an administrator stated — FR-9 ────────────────────────

_CALENDAR_KEY = "current"
"""One installation, one calendar. See `CalendarOverrideRow`."""


class SqlCalendarStore:
    """The calendar overrides in PostgreSQL — FR-9.

    ⚠️ **It stores the administrator's statement, never the loaded calendar.**
    `services/calendar.apply_calendar` layers what is here over the pristine
    instance at run assembly, so `reset()` genuinely restores `slots.csv` —
    which it could not do if this table had ever been seeded from it.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def overrides(self) -> CalendarOverrides:
        with self._sessions() as session:
            row = session.get(CalendarOverrideRow, _CALENDAR_KEY)
            return EMPTY if row is None else _to_overrides_calendar(row)

    def save(self, overrides: CalendarOverrides, author: str) -> None:
        with self._sessions() as session, session.begin():
            row = session.get(CalendarOverrideRow, _CALENDAR_KEY)
            if row is None:
                row = CalendarOverrideRow(id=_CALENDAR_KEY)
                session.add(row)
            row.slot_open = {str(index): value for index, value in overrides.slot_open}
            row.holidays = (
                None
                if overrides.holidays is None
                else [_holiday_json(h) for h in overrides.holidays]
            )
            row.shortened_day = (
                None
                if overrides.shortened_day is None
                else _shortened_json(overrides.shortened_day)
            )
            row.updated_at = datetime.now(UTC)
            row.updated_by = author

    def last_edit(self) -> CalendarEdit | None:
        with self._sessions() as session:
            row = session.get(CalendarOverrideRow, _CALENDAR_KEY)
            return None if row is None else CalendarEdit(at=row.updated_at, by=row.updated_by)

    def reset(self) -> None:
        """Delete the row rather than blanking its columns.

        A row of nulls and an absent row would both mean "no edit", and two
        representations of one state is how a later reader ends up asking which
        of them is the real one.
        """
        with self._sessions() as session, session.begin():
            session.execute(
                delete(CalendarOverrideRow).where(CalendarOverrideRow.id == _CALENDAR_KEY)
            )


def _to_overrides_calendar(row: CalendarOverrideRow) -> CalendarOverrides:
    return CalendarOverrides(
        slot_open=tuple(
            sorted((int(index), bool(value)) for index, value in row.slot_open.items())
        ),
        holidays=(
            None if row.holidays is None else tuple(_to_holiday(entry) for entry in row.holidays)
        ),
        shortened_day=(None if row.shortened_day is None else _to_shortened(row.shortened_day)),
    )


def _holiday_json(holiday: Holiday) -> dict[str, object]:
    return {
        "date": holiday.date.isoformat(),
        "label": holiday.label,
        "lunar": holiday.lunar,
        "approximate": holiday.approximate,
        "blocking": holiday.blocking,
    }


def _to_holiday(entry: dict[str, object]) -> Holiday:
    return Holiday(
        date=date.fromisoformat(str(entry["date"])),
        label=str(entry["label"]),
        lunar=bool(entry["lunar"]),
        approximate=bool(entry["approximate"]),
        blocking=bool(entry["blocking"]),
    )


def _shortened_json(shortened: ShortenedDay) -> dict[str, object]:
    return {
        "start": shortened.start.isoformat(),
        "end": shortened.end.isoformat(),
        "shift_minutes": shortened.shift_minutes,
    }


def _to_shortened(entry: dict[str, object]) -> ShortenedDay:
    return ShortenedDay(
        start=date.fromisoformat(str(entry["start"])),
        end=date.fromisoformat(str(entry["end"])),
        shift_minutes=int(str(entry["shift_minutes"])),
    )


_TIMING_DECOY = hash_password("timing-decoy-never-a-real-password")
"""A real bcrypt hash, verified against when the username is unknown.

Computed once at import: bcrypt is deliberately slow, and doing this per
request would cost every failed sign-in a second hash for no extra protection.
"""


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
