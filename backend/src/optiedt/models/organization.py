"""Institution settings, departments, campuses, buildings and rooms."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from optiedt.db.base import Base, Timestamps, UuidPk, Versioned


class Institution(Versioned, Base):
    """The single institution this deployment serves (ADR 0004)."""

    __tablename__ = "institution"
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton"),
        CheckConstraint("week_start BETWEEN 0 AND 6", name="week_start_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str] = mapped_column(String(40))
    country_code: Mapped[str | None] = mapped_column(String(2))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    default_locale: Mapped[str] = mapped_column(String(8), default="en")
    enabled_locales: Mapped[list[str]] = mapped_column(
        ARRAY(String(8)), default=lambda: ["en", "fr", "ar"]
    )
    week_start: Mapped[int] = mapped_column(SmallInteger, default=0)
    date_format: Mapped[str] = mapped_column(String(16), default="dd/MM/yyyy")
    time_format: Mapped[str] = mapped_column(String(8), default="HH:mm")
    public_timetable_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    assistant_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Department(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "departments"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Campus(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "campuses"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CampusTravelTime(Base):
    """Travel time between two campuses; stored once per unordered pair (lower id first)."""

    __tablename__ = "campus_travel_times"
    __table_args__ = (
        CheckConstraint("campus_a_id < campus_b_id", name="ordered_pair"),
        CheckConstraint("minutes >= 0", name="non_negative"),
    )

    campus_a_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campuses.id", ondelete="CASCADE"), primary_key=True
    )
    campus_b_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campuses.id", ondelete="CASCADE"), primary_key=True
    )
    minutes: Mapped[int] = mapped_column(Integer)


class Building(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "buildings"
    __table_args__ = (UniqueConstraint("campus_id", "code"),)

    campus_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campuses.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RoomType(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "room_types"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RoomFeature(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "room_features"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120))


room_feature_links = Table(
    "room_feature_links",
    Base.metadata,
    Column("room_id", ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "feature_id",
        ForeignKey("room_features.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    ),
)


class Room(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("building_id", "code"),
        CheckConstraint("capacity > 0", name="positive_capacity"),
    )

    building_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str | None] = mapped_column(String(200))
    room_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("room_types.id", ondelete="RESTRICT"), index=True
    )
    capacity: Mapped[int] = mapped_column(Integer)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    features: Mapped[list[RoomFeature]] = relationship(
        secondary=room_feature_links, lazy="selectin", order_by=RoomFeature.code
    )
