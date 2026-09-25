"""Term-scoped data: time grid, student groups, activities, availability, rules, profiles.

Links between term-scoped records carry ``term_id`` in composite foreign keys, so the database
itself refuses an activity of one term pointing at a student group of another.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from optiedt.db.base import Base, Timestamps, UuidPk, Versioned

AVAILABILITY_STATES = ("preferred", "undesirable", "unavailable")


class Term(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "terms"
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="ordered_dates"),
        CheckConstraint("status IN ('planning', 'active', 'closed')", name="known_status"),
        CheckConstraint("cardinality(weekdays) BETWEEN 1 AND 7", name="weekday_count"),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    academic_year: Mapped[str] = mapped_column(String(16))
    start_date: Mapped[date]
    end_date: Mapped[date]
    status: Mapped[str] = mapped_column(String(16), default="planning")
    weekdays: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger))
    """Teaching weekdays in display order, 0 = Monday … 6 = Sunday."""
    availability_open_until: Mapped[date | None]
    """Last day instructors may edit their own availability; ``None`` closes declarations."""
    room_capacity_ratio: Mapped[float] = mapped_column(default=4.0)
    """The solver does not consider rooms more than this many times the required seats."""

    periods: Mapped[list[Period]] = relationship(
        back_populates="term", order_by="Period.position", cascade="all, delete-orphan"
    )


class Period(UuidPk, Base):
    __tablename__ = "periods"
    __table_args__ = (
        UniqueConstraint("term_id", "position"),
        CheckConstraint("end_time > start_time", name="ordered_times"),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(SmallInteger)
    label: Mapped[str] = mapped_column(String(32))
    start_time: Mapped[time]
    end_time: Mapped[time]
    joins_next: Mapped[bool] = mapped_column(Boolean, default=True)
    """A session may continue from this period into the next one (false across a break)."""

    term: Mapped[Term] = relationship(back_populates="periods")


class SlotSetting(UuidPk, Base):
    """Non-default properties of one (weekday, period) slot."""

    __tablename__ = "slot_settings"
    __table_args__ = (
        UniqueConstraint("term_id", "weekday", "period_id"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("penalty BETWEEN 0 AND 3", name="penalty_range"),
        CheckConstraint(
            "(start_time IS NULL) = (end_time IS NULL) AND "
            "(start_time IS NULL OR end_time > start_time)",
            name="time_override_pair",
        ),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(SmallInteger)
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("periods.id", ondelete="CASCADE"))
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_reason: Mapped[str | None] = mapped_column(String(200))
    start_time: Mapped[time | None]
    end_time: Mapped[time | None]
    penalty: Mapped[int] = mapped_column(SmallInteger, default=0)


class TimingVariant(UuidPk, Timestamps, Versioned, Base):
    """Alternative period times for a date range (e.g. Ramadan hours)."""

    __tablename__ = "timing_variants"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ordered_dates"),)

    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date]
    end_date: Mapped[date]

    periods: Mapped[list[TimingVariantPeriod]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class TimingVariantPeriod(Base):
    __tablename__ = "timing_variant_periods"
    __table_args__ = (CheckConstraint("end_time > start_time", name="ordered_times"),)

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("timing_variants.id", ondelete="CASCADE"), primary_key=True
    )
    period_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("periods.id", ondelete="CASCADE"), primary_key=True
    )
    start_time: Mapped[time]
    end_time: Mapped[time]


class StudentGroup(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "student_groups"
    __table_args__ = (
        UniqueConstraint("term_id", "code"),
        UniqueConstraint("term_id", "id"),
        ForeignKeyConstraint(
            ["term_id", "parent_id"],
            ["student_groups.term_id", "student_groups.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("size >= 0", name="non_negative_size"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_own_parent"),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(48))
    name: Mapped[str] = mapped_column(String(200))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    partition_key: Mapped[str] = mapped_column(String(32), default="default")
    """Children of one parent sharing a key are disjoint; different keys overlap (ADR 0011)."""
    size: Mapped[int] = mapped_column(Integer)
    programme_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("programmes.id", ondelete="SET NULL"), index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)


activity_groups = Table(
    "activity_groups",
    Base.metadata,
    Column("term_id", UUID(as_uuid=True), nullable=False),
    Column("activity_id", UUID(as_uuid=True), primary_key=True),
    Column("group_id", UUID(as_uuid=True), primary_key=True, index=True),
    ForeignKeyConstraint(
        ["term_id", "activity_id"], ["activities.term_id", "activities.id"], ondelete="CASCADE"
    ),
    ForeignKeyConstraint(
        ["term_id", "group_id"],
        ["student_groups.term_id", "student_groups.id"],
        ondelete="RESTRICT",
    ),
)

activity_instructors = Table(
    "activity_instructors",
    Base.metadata,
    Column("activity_id", ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "instructor_id",
        ForeignKey("instructors.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    ),
)

activity_features = Table(
    "activity_features",
    Base.metadata,
    Column("activity_id", ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
    Column("feature_id", ForeignKey("room_features.id", ondelete="RESTRICT"), primary_key=True),
)


class Activity(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("term_id", "id"),
        CheckConstraint("duration BETWEEN 1 AND 12", name="duration_range"),
        CheckConstraint("sessions_per_week BETWEEN 1 AND 7", name="sessions_range"),
        CheckConstraint("delivery_mode IN ('in_person', 'online')", name="known_delivery"),
        CheckConstraint("min_capacity IS NULL OR min_capacity > 0", name="positive_capacity"),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="RESTRICT"), index=True
    )
    activity_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("activity_types.id", ondelete="RESTRICT")
    )
    label: Mapped[str | None] = mapped_column(String(120))
    duration: Mapped[int] = mapped_column(SmallInteger, default=1)
    sessions_per_week: Mapped[int] = mapped_column(SmallInteger, default=1)
    different_days: Mapped[bool] = mapped_column(Boolean, default=True)
    delivery_mode: Mapped[str] = mapped_column(String(16), default="in_person")
    room_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("room_types.id", ondelete="RESTRICT")
    )
    """Overrides the activity type's default room type."""
    min_capacity: Mapped[int | None] = mapped_column(Integer)
    """Seats required; defaults to the total size of the student groups."""
    campus_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campuses.id", ondelete="RESTRICT")
    )
    building_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT")
    )
    notes: Mapped[str | None] = mapped_column(Text)


class ActivityRoom(Base):
    """Room restriction or preference of an activity."""

    __tablename__ = "activity_rooms"
    __table_args__ = (
        CheckConstraint("kind IN ('allowed', 'preferred', 'avoided')", name="known_kind"),
    )

    activity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(16))


class FixedPlacement(Base):
    """A pre-decided slot (and optionally room) for one occurrence of an activity."""

    __tablename__ = "fixed_placements"
    __table_args__ = (
        CheckConstraint("occurrence >= 1", name="positive_occurrence"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
    )

    activity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True
    )
    occurrence: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    weekday: Mapped[int] = mapped_column(SmallInteger)
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("periods.id", ondelete="CASCADE"))
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))


class AvailabilityGrid(UuidPk, Versioned, Base):
    """Slot states of one resource in one term.

    ``cells`` holds only non-default slots: ``[{"weekday": 0, "period_id": "…", "state": …}]``.
    Exactly one resource column is set.
    """

    __tablename__ = "availability_grids"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(instructor_id, group_id, room_id, activity_id) = 1",
            name="one_resource",
        ),
        CheckConstraint("source IN ('self', 'staff', 'import')", name="known_source"),
        Index(
            "uq_availability_instructor",
            "term_id",
            "instructor_id",
            unique=True,
            postgresql_where=text("instructor_id IS NOT NULL"),
        ),
        Index(
            "uq_availability_group",
            "term_id",
            "group_id",
            unique=True,
            postgresql_where=text("group_id IS NOT NULL"),
        ),
        Index(
            "uq_availability_room",
            "term_id",
            "room_id",
            unique=True,
            postgresql_where=text("room_id IS NOT NULL"),
        ),
        Index(
            "uq_availability_activity",
            "term_id",
            "activity_id",
            unique=True,
            postgresql_where=text("activity_id IS NOT NULL"),
        ),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    instructor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("instructors.id", ondelete="CASCADE")
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("student_groups.id", ondelete="CASCADE")
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE")
    )
    cells: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    source: Mapped[str] = mapped_column(String(8), default="staff")
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class ConstraintRule(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "constraint_rules"
    __table_args__ = (
        CheckConstraint("enforcement IN ('hard', 'soft')", name="known_enforcement"),
        CheckConstraint("tier BETWEEN 1 AND 5", name="tier_range"),
        CheckConstraint("weight >= 1", name="positive_weight"),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    rule_type: Mapped[str] = mapped_column(String(48))
    name: Mapped[str] = mapped_column(String(200))
    enforcement: Mapped[str] = mapped_column(String(8))
    tier: Mapped[int] = mapped_column(SmallInteger, default=2)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)


class ObjectiveProfile(UuidPk, Timestamps, Versioned, Base):
    """Tier and weight of every built-in objective (ADR 0006)."""

    __tablename__ = "objective_profiles"
    __table_args__ = (UniqueConstraint("term_id", "code"),)

    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    objectives: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    """``{objective_code: {"tier": int, "weight": int, "enabled": bool}}``."""
    position: Mapped[int] = mapped_column(SmallInteger, default=0)
