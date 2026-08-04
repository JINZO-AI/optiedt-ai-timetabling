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
