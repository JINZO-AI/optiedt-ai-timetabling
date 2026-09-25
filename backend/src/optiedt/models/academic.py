"""Programmes, courses, activity types, instructors and the date calendar."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from optiedt.db.base import Base, Timestamps, UuidPk, Versioned


class Programme(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "programmes"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    level: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Course(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ActivityType(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "activity_types"
    __table_args__ = (CheckConstraint("color ~ '^#[0-9a-fA-F]{6}$'", name="hex_color"),)

    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    default_room_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("room_types.id", ondelete="SET NULL")
    )
    color: Mapped[str] = mapped_column(String(7), default="#5b6b7f")
    position: Mapped[int] = mapped_column(SmallInteger, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Instructor(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "instructors"
    __table_args__ = (
        CheckConstraint(
            "max_weekly_periods IS NULL OR max_weekly_periods > 0", name="positive_max_load"
        ),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(254))
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(80))
    max_weekly_periods: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class CalendarEvent(UuidPk, Timestamps, Versioned, Base):
    """A dated holiday or closure; no teaching occurs on these dates."""

    __tablename__ = "calendar_events"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ordered_dates"),
        CheckConstraint("kind IN ('holiday', 'closure')", name="known_kind"),
    )

    start_date: Mapped[date]
    end_date: Mapped[date]
    kind: Mapped[str] = mapped_column(String(16), default="holiday")
    label: Mapped[str] = mapped_column(String(200))
    is_tentative: Mapped[bool] = mapped_column(Boolean, default=False)
