"""Accounts, role assignments, sessions, login throttling and calendar feed tokens."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from optiedt.db.base import Base, Timestamps, UuidPk, Versioned

ROLES = (
    "system_admin",
    "institution_admin",
    "scheduling_officer",
    "department_head",
    "instructor",
    "student",
    "viewer",
)


class User(UuidPk, Timestamps, Versioned, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str | None] = mapped_column(String(254))
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    locale: Mapped[str | None] = mapped_column(String(8))
    instructor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("instructors.id", ondelete="SET NULL"), unique=True
    )
    last_login_at: Mapped[datetime | None]
    password_changed_at: Mapped[datetime | None]

    roles: Mapped[list[RoleAssignment]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="RoleAssignment.user_id",
    )


class RoleAssignment(UuidPk, Base):
    __tablename__ = "role_assignments"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "role", "department_id", postgresql_nulls_not_distinct=True
        ),
        CheckConstraint(
            "role IN (" + ", ".join(f"'{r}'" for r in ROLES) + ")", name="known_role"
        ),
        CheckConstraint(
            "department_id IS NULL OR role NOT IN ('system_admin', 'institution_admin')",
            name="admin_roles_unscoped",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    user: Mapped[User] = relationship(back_populates="roles", foreign_keys=[user_id])


class StudentMembership(Base):
    """Links a student account to the student groups whose timetable it may read."""

    __tablename__ = "student_memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_groups.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class UserSession(UuidPk, Base):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(256))
    revoked_at: Mapped[datetime | None]


class LoginThrottle(Base):
    """Failed sign-in counters keyed by account name or client address."""

    __tablename__ = "login_throttles"

    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_started_at: Mapped[datetime]
    locked_until: Mapped[datetime | None]


class CalendarFeedToken(UuidPk, Base):
    __tablename__ = "calendar_feed_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_used_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]
