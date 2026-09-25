"""Snapshots, scenarios, solver runs, solutions and publications."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from optiedt.db.base import Base, Timestamps, UuidPk, Versioned

RUN_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")
RUN_KINDS = ("optimize", "repair", "relaxation")
SOLUTION_STATUSES = ("draft", "pending_approval", "approved", "published", "archived")
SOLUTION_ORIGINS = ("solver", "copy", "rebase", "repair", "restore")
EXCEPTION_KINDS = ("cancelled", "relocated", "rescheduled")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


class ProblemSnapshot(UuidPk, Base):
    """Immutable, content-addressed copy of everything a run needs (ADR 0008)."""

    __tablename__ = "problem_snapshots"
    __table_args__ = (UniqueConstraint("term_id", "content_hash"),)

    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    content_hash: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[int] = mapped_column(SmallInteger)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Scenario(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "scenarios"

    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    profile_codes: Mapped[list[str]] = mapped_column(ARRAY(String(32)))
    scope_department_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list
    )
    """When non-empty, only activities of these departments may move; the rest stay as in the
    base solution."""
    base_solution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("solutions.id", ondelete="SET NULL", use_alter=True)
    )
    minimize_changes: Mapped[bool] = mapped_column(Boolean, default=False)
    """Add the stability objective relative to the base solution in tier 1."""
    solver_mode: Mapped[str] = mapped_column(String(16), default="fastest")
    time_limit_seconds: Mapped[int] = mapped_column(Integer, default=120)
    seed: Mapped[int] = mapped_column(Integer, default=1)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    archived_at: Mapped[datetime | None]

    __table_args__ = (
        CheckConstraint("solver_mode IN ('reproducible', 'fastest')", name="known_mode"),
        CheckConstraint("time_limit_seconds BETWEEN 5 AND 86400", name="time_limit_range"),
    )


class SolverRun(UuidPk, Base):
    """One execution; also the job record claimed by workers (ADR 0003)."""

    __tablename__ = "solver_runs"
    __table_args__ = (
        CheckConstraint(_in("status", RUN_STATUSES), name="known_status"),
        CheckConstraint(_in("kind", RUN_KINDS), name="known_kind"),
        Index("ix_solver_runs_queue", "status", "requested_at"),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), index=True
    )
    source_solution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("solutions.id", ondelete="SET NULL", use_alter=True)
    )
    kind: Mapped[str] = mapped_column(String(16), default="optimize")
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_snapshots.id", ondelete="RESTRICT")
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    phase: Mapped[str | None] = mapped_column(String(32))
    progress: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    worker_id: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None]
    heartbeat_at: Mapped[datetime | None]
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    log: Mapped[str | None] = mapped_column(Text)
    app_version: Mapped[str] = mapped_column(String(32))
    solver_version: Mapped[str] = mapped_column(String(32))


class SolverRunEvent(Base):
    __tablename__ = "solver_run_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solver_runs.id", ondelete="CASCADE"), index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Solution(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "solutions"
    __table_args__ = (
        CheckConstraint(_in("status", SOLUTION_STATUSES), name="known_status"),
        CheckConstraint(_in("origin", SOLUTION_ORIGINS), name="known_origin"),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_snapshots.id", ondelete="RESTRICT"), index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("solver_runs.id", ondelete="SET NULL"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("solutions.id", ondelete="SET NULL")
    )
    base_publication_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("publications.id", ondelete="SET NULL", use_alter=True)
    )
    name: Mapped[str] = mapped_column(String(200))
    origin: Mapped[str] = mapped_column(String(16))
    profile_code: Mapped[str | None] = mapped_column(String(32))
    objective_config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    """Tiers and weights used to evaluate and compare this solution."""
    status: Mapped[str] = mapped_column(String(24), default="draft")
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    hard_violation_count: Mapped[int] = mapped_column(Integer, default=0)
    evaluation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    evaluated_at: Mapped[datetime | None]
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    submitted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    submitted_at: Mapped[datetime | None]
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None]
    review_note: Mapped[str | None] = mapped_column(Text)

    @property
    def is_valid(self) -> bool:
        return self.is_complete and self.hard_violation_count == 0


class SolutionAssignment(Base):
    """Placement of one snapshot session. Unplaced sessions have no row."""

    __tablename__ = "solution_assignments"

    solution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solutions.id", ondelete="CASCADE"), primary_key=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    day: Mapped[int] = mapped_column(SmallInteger)
    period: Mapped[int] = mapped_column(SmallInteger)
    room_id: Mapped[uuid.UUID | None]
    locked: Mapped[bool] = mapped_column(Boolean, default=False)


class SolutionChange(Base):
    __tablename__ = "solution_changes"
    __table_args__ = (
        UniqueConstraint("solution_id", "seq"),
        Index("ix_solution_changes_instructors", "affected_instructor_ids", postgresql_using="gin"),
        Index("ix_solution_changes_groups", "affected_group_ids", postgresql_using="gin"),
        Index("ix_solution_changes_rooms", "affected_room_ids", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    solution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("solutions.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_label: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(24))
    session_id: Mapped[uuid.UUID | None]
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    summary: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    affected_instructor_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list
    )
    affected_group_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list
    )
    affected_room_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list
    )


class Publication(UuidPk, Base):
    __tablename__ = "publications"
    __table_args__ = (
        UniqueConstraint("term_id", "version_no"),
        Index(
            "uq_publications_current",
            "term_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    version_no: Mapped[int] = mapped_column(Integer)
    solution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("solutions.id", ondelete="RESTRICT"))
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problem_snapshots.id", ondelete="RESTRICT")
    )
    content_hash: Mapped[str] = mapped_column(String(64))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    restored_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("publications.id", ondelete="SET NULL")
    )
    published_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    published_at: Mapped[datetime] = mapped_column(server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class PublicationAssignment(Base):
    __tablename__ = "publication_assignments"

    publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), primary_key=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    day: Mapped[int] = mapped_column(SmallInteger)
    period: Mapped[int] = mapped_column(SmallInteger)
    room_id: Mapped[uuid.UUID | None]


class OccurrenceException(UuidPk, Base):
    """Change to one dated occurrence of a published session (ADR 0013)."""

    __tablename__ = "occurrence_exceptions"
    __table_args__ = (
        CheckConstraint(_in("kind", EXCEPTION_KINDS), name="known_kind"),
        CheckConstraint(
            "(kind = 'cancelled') OR (kind = 'relocated' AND new_room_id IS NOT NULL) OR "
            "(kind = 'rescheduled' AND new_date IS NOT NULL AND new_period IS NOT NULL)",
            name="kind_fields",
        ),
        Index(
            "uq_occurrence_exceptions_active",
            "publication_id",
            "session_id",
            "occurrence_date",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID]
    occurrence_date: Mapped[date]
    kind: Mapped[str] = mapped_column(String(16))
    new_date: Mapped[date | None]
    new_period: Mapped[int | None] = mapped_column(SmallInteger)
    new_room_id: Mapped[uuid.UUID | None]
    reason: Mapped[str | None] = mapped_column(Text)
    notice: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    revoked_at: Mapped[datetime | None]
    revoked_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class WorkerHeartbeat(Base):
    """Liveness of solver worker processes, shown in system status and readiness."""

    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    current_run_id: Mapped[uuid.UUID | None]
    version: Mapped[str] = mapped_column(String(32))
