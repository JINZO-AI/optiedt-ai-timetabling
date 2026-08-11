"""The tables FR-19 records: every run with its data, seed, weights and results.

**What is normalised and what is not, and why.** `docs/domain-model.md` lists
Run, WeightProfile, Candidate, Placement and SubScore as entities, and each gets
a table — they are the things a later question will be asked about ("which runs
placed this session here?", "how did S3 move across runs?"). Two things stay as
JSON columns instead: `duplicates_removed` and a diagnosis's
`conflicting_codes`. Both are short ordered lists of scalars with no identity of
their own, nothing joins to them, and a table per list would add two joins to
every read for no question anyone asks.

⚠️ **Candidate order is data, not presentation.** `frontend/src/types/domain.ts`
says "in rank order, best first — display this order, do not sort", so the order
the ranker produced has to survive a restart. `Candidate.rank_order` carries it;
reading candidates without `ORDER BY rank_order` would silently return whatever
PostgreSQL found convenient, and the screen would show a ranking nobody chose.

⚠️ **Invariant 6: a candidate is immutable once recorded.** There is no update
path to `candidates`, `placements` or `sub_scores` anywhere in
`db/repositories.py` — a run's candidates are inserted once, when it first
carries them. A regenerated timetable is a NEW candidate under a NEW run.

`ondelete="CASCADE"` throughout: a run is the aggregate root, and a candidate
without its run is not a thing this domain has a use for.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from optiedt.db.base import Base


class RunRow(Base):
    """One execution of the generation. The aggregate root."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    seed: Mapped[int] = mapped_column(Integer)
    deterministic_budget: Mapped[float] = mapped_column(Float)
    """Deterministic time, NOT wall-clock seconds (ADR-011)."""

    state: Mapped[str] = mapped_column(String(16))
    model_version: Mapped[str] = mapped_column(String(64))
    """What produced the candidates. A score is only comparable across runs
    computed the same way, so this is recorded rather than inferred."""

    duplicates_removed: Mapped[list[str]] = mapped_column(JSON, default=list)
    deterministic_time_used: Mapped[float] = mapped_column(Float, default=0.0)
    wall_clock_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    origin_run_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    origin_candidate_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    origin_action_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    origin_action_detail: Mapped[str | None] = mapped_column(String(512), nullable=True)
    """Provenance of a run regenerated from an accepted recommendation (FR-23).

    All four are NULL for a run launched from the generation screen.
    ``origin_run_id`` is deliberately NOT a foreign key: it is provenance, and
    a run must not become undeletable because a later one cites it. A dangling
    origin reads as "the run it came from is gone", which is honest; a
    cascade would silently delete the regenerated run along with its origin,
    destroying a record invariant 6 exists to keep.
    """

    overrides: Mapped[dict[str, list[list[str | int]]]] = mapped_column(JSON, default=dict)
    """The locks and exclusions this run solved under, composed along the
    regeneration chain (C-20).

    JSON rather than three tables, following ``duplicates_removed``: this is
    one short list per run, read whole and never queried into. Normalising it
    would add three join tables to answer a question nobody asks."""

    weights: Mapped[list[RunWeightRow]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    checks: Mapped[list[PreAnalysisCheckRow]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="PreAnalysisCheckRow.ordinal"
    )
    diagnosis: Mapped[DiagnosisRow | None] = relationship(
        cascade="all, delete-orphan", lazy="selectin", uselist=False
    )
    candidates: Mapped[list[CandidateRow]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="CandidateRow.rank_order"
    )


class RunWeightRow(Base):
    """The weight vector in force for a run.

    ONE vector prices every candidate of the run: the exact-decomposition
    identity only holds when the same w_i prices both sides
    (docs/scoring-and-explanation.md). Recorded per run, never per candidate,
    so that reading it back cannot reintroduce the ambiguity.
    """

    __tablename__ = "run_weights"
    __table_args__ = (UniqueConstraint("run_id", "criterion"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    criterion: Mapped[str] = mapped_column(String(8))
    weight: Mapped[float] = mapped_column(Float)


class PreAnalysisCheckRow(Base):
    """One of the five verifications, as the run recorded it (FR-12).

    `ordinal` preserves the reported order rather than relying on insertion
    order. ⚠️ NO rows at all means the stage did not run — never "verified,
    nothing wrong".
    """

    __tablename__ = "run_checks"
    __table_args__ = (UniqueConstraint("run_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(32))
    passed: Mapped[bool] = mapped_column(Boolean)
    resource: Mapped[str | None] = mapped_column(String(128), nullable=True)
    missing_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str] = mapped_column(String(4096), default="")


class DiagnosisRow(Base):
    """Stage 3's report (FR-8). At most one per run.

    ⚠️ `is_conclusive` is not decoration: an empty `conflicting_codes` means
    either "no withdrawable rule explains it" or "no proof was found", and only
    this column separates them.
    """

    __tablename__ = "run_diagnoses"

    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True)
    conflicting_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_minimal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_conclusive: Mapped[bool] = mapped_column(Boolean, default=True)
    detail: Mapped[str] = mapped_column(String(4096), default="")


class CandidateRow(Base):
    """A valid timetable. Immutable once recorded (invariant 6)."""

    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    rank_order: Mapped[int] = mapped_column(Integer)
    """Position in the ranking the run produced. Read back with ORDER BY."""

    profile_name: Mapped[str] = mapped_column(String(32))
    """Provenance only. The comparison decomposes under the RUN's weights, not
    under the producing profile's."""

    cost: Mapped[int] = mapped_column(Integer)
    """The solver's objective value, provenance ONLY. Nothing ranks on it -
    under `interleave_search` it can disagree with the solution returned
    (ADR-011). `score` is recomputed by the analysis layer."""

    score: Mapped[float] = mapped_column(Float)

    placements: Mapped[list[PlacementRow]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="PlacementRow.session"
    )
    sub_scores: Mapped[list[SubScoreRow]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="SubScoreRow.criterion"
    )


class PlacementRow(Base):
    """One assignment inside one candidate. Written only by the solver."""

    __tablename__ = "placements"
    __table_args__ = (UniqueConstraint("candidate_id", "session"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    session: Mapped[str] = mapped_column(String(64))
    slot: Mapped[int] = mapped_column(Integer)
    room: Mapped[str] = mapped_column(String(64))


class SubScoreRow(Base):
    """One criterion's value for one candidate, raw and normalised."""

    __tablename__ = "sub_scores"
    __table_args__ = (UniqueConstraint("candidate_id", "criterion"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    criterion: Mapped[str] = mapped_column(String(8))
    raw_value: Mapped[float] = mapped_column(Float)
    normalised: Mapped[float] = mapped_column(Float)
    """In [0, 1], 1 = best, against instance-derived bounds (ADR-009)."""


class PublicationRow(Base):
    """A timetable made visible — the acceptance criterion's other half.

    ⚠️ **No placements are copied here.** It points at the candidate, which is
    immutable (invariant 6), so the published timetable cannot drift from the
    record of it. Copying would let two rows disagree about one timetable, and
    then nothing says which was published.

    `run_id` is stored even though it is reachable through the candidate: the
    trace must survive being read on its own, and a publication that needs a
    join to name its run is one query away from being reported without it.

    ⚠️ No `ondelete` cascade to `candidates`, deliberately. A published
    timetable is a record of something the department did, and it must not
    vanish because a run was tidied away. Deleting a run that has a publication
    now fails on the foreign key, which is the correct answer.
    """

    __tablename__ = "publications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    published_by: Mapped[str] = mapped_column(String(64))
    """The username, recorded because publication is an act with an author."""


class UserRow(Base):
    """An account and its role — FR-11.

    ⚠️ `password_hash` is read by `SqlUserStore.authenticate` and by nothing
    else, ever. It is not on `domain.User`, so it cannot reach a router, a
    response schema or a log line by accident.

    `teacher` is set only for a TEACHER and links the account to a row of
    `teachers.csv`. It is what makes "a teacher account obtains only its own
    availability and timetable" enforceable from the token rather than from the
    request path.

    `group` is the same for a STUDENT, added in Phase 11: SRS Table 2 gives the
    student "read the timetable of their group", and the account is the only
    place that can say which group that is.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(24))
    teacher: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    group: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class CalendarOverrideRow(Base):
    """The calendar an administrator stated — FR-9.

    ⚠️ **One row, and the row is the whole calendar.** `id` is a fixed key
    because an installation has one calendar; a table that admitted several
    would leave "which one is in force?" for a later reader to guess.

    ⚠️ **The loaded `slots.csv`, `holidays.csv` and `calendar_config.csv` are
    NOT copied in here.** This row carries only what was stated through the
    application and is layered over the pristine instance at run assembly
    (`services/calendar.apply_calendar`), exactly as FR-2's declarations are.
    Copying the loaded calendar in would make the edit impossible to withdraw
    and would give the same fact two homes free to disagree.

    JSON columns for the same reason `RunRow.overrides` uses one: each is a
    short list read whole at run assembly and never queried into, and three
    tables would add three joins to answer a question nobody asks.

    `slot_open` is `{"index": bool}` for the slots actually stated — a slot
    absent from it keeps whatever `slots.csv` says. `holidays` is NULL when no
    holiday list was ever stated, which is deliberately different from an empty
    list meaning "there are none".
    """

    __tablename__ = "calendar_overrides"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    slot_open: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict)
    holidays: Mapped[list[dict[str, object]] | None] = mapped_column(JSON, nullable=True)
    shortened_day: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[str] = mapped_column(String(64))
    """The username. Closing a half-day changes what every future run can
    produce, so it is recorded with an author, like a publication."""


class AvailabilityRow(Base):
    """A declaration made through the application (FR-2).

    ⚠️ Only rows a teacher actually declared live here. The instance's own 157
    generated rows stay in `teacher_availability.csv` and are NOT copied in:
    `services/availability.py` substitutes a declaring teacher's rows wholesale
    over the generated ones, and a teacher absent from this table has not been
    asked - which is deliberately different from one who answered "I am free all
    week". Copying the generated rows in would erase that distinction and let a
    generated declaration pass for a real one.

    `source` is stored even though every row written here is `TEACHER`, because
    the distinction is a requirement rather than a convenience
    (docs/domain-model.md) and a column that has to be added later is a column
    that was inferred in the meantime.
    """

    __tablename__ = "availability_declarations"
    __table_args__ = (UniqueConstraint("teacher", "slot", "semester"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher: Mapped[str] = mapped_column(String(64), index=True)
    slot: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16))
    semester: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))


class DepartmentDatasetRow(Base):
    """The department dataset that was imported — FR-1.

    ⚠️ **One row, and the row is the whole dataset.** `id` is a fixed key
    because an installation has one department; CdC §3.2 puts *"simultaneous
    treatment of several faculties of the same university"* outside the scope,
    so a table admitting several would model something the specification
    excludes.

    ⚠️ **`files` holds the supplied TEXTS, not a serialisation of the entities**,
    and not one table per entity. Three reasons, in order of weight. The
    instance is read *whole* at run assembly and never queried into, which is
    the same test `RunRow.overrides` and `calendar_overrides` already passed —
    eleven tables would add eleven joins to answer a question nobody asks.
    Storing the text keeps **one** parse path, `instance/validation.py`, so a
    stored dataset cannot drift from what was verified. And the file schema is
    already what `docs/data-and-instance.md` calls the contract between the
    generator and the application; a second shape for the same entities would
    be a second thing to keep in step with the domain.

    ⚠️ **`constraint_catalogue.csv` is not among the files and cannot be.**
    `instance/validation.DEPARTMENT_FILES` names eleven, and the catalogue is
    the software's own — see ADR-003 and invariant 7.

    `revision` changes on every save. `api/deps.py` reads it on every request
    and re-parses only when it has moved, which is what makes serving a dataset
    the database no longer holds impossible rather than unlikely.
    """

    __tablename__ = "department_dataset"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    files: Mapped[dict[str, str]] = mapped_column(JSON)
    revision: Mapped[str] = mapped_column(String(36))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    imported_by: Mapped[str] = mapped_column(String(64))
