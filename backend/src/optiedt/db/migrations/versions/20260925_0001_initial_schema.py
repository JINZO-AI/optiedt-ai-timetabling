"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-25 00:33:57.769358
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_label", sa.String(length=160), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=48), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("term_id", sa.UUID(), nullable=True),
        sa.Column("department_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False)
    op.create_index(op.f("ix_audit_events_actor_id"), "audit_events", ["actor_id"], unique=False)
    op.create_index(
        "ix_audit_events_departments",
        "audit_events",
        ["department_ids"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_occurred_at"), "audit_events", ["occurred_at"], unique=False
    )
    op.create_index(op.f("ix_audit_events_term_id"), "audit_events", ["term_id"], unique=False)
    op.create_table(
        "calendar_events",
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("is_tentative", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('holiday', 'closure')", name=op.f("ck_calendar_events_known_kind")
        ),
        sa.CheckConstraint("end_date >= start_date", name=op.f("ck_calendar_events_ordered_dates")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendar_events")),
    )
    op.create_table(
        "campuses",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campuses")),
        sa.UniqueConstraint("code", name=op.f("uq_campuses_code")),
    )
    op.create_table(
        "departments",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["departments.id"],
            name=op.f("fk_departments_parent_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("code", name=op.f("uq_departments_code")),
    )
    op.create_index(op.f("ix_departments_parent_id"), "departments", ["parent_id"], unique=False)
    op.create_table(
        "idempotency_records",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("endpoint", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "key", name=op.f("pk_idempotency_records")),
    )
    op.create_index(
        op.f("ix_idempotency_records_created_at"),
        "idempotency_records",
        ["created_at"],
        unique=False,
    )
    op.create_table(
        "institution",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("short_name", sa.String(length=40), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("default_locale", sa.String(length=8), nullable=False),
        sa.Column("enabled_locales", postgresql.ARRAY(sa.String(length=8)), nullable=False),
        sa.Column("week_start", sa.SmallInteger(), nullable=False),
        sa.Column("date_format", sa.String(length=16), nullable=False),
        sa.Column("time_format", sa.String(length=8), nullable=False),
        sa.Column("public_timetable_enabled", sa.Boolean(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("assistant_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("id = 1", name=op.f("ck_institution_singleton")),
        sa.CheckConstraint(
            "week_start BETWEEN 0 AND 6", name=op.f("ck_institution_week_start_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institution")),
    )
    op.create_table(
        "login_throttles",
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_login_throttles")),
    )
    op.create_table(
        "room_features",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_room_features")),
        sa.UniqueConstraint("code", name=op.f("uq_room_features_code")),
    )
    op.create_table(
        "room_types",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_room_types")),
        sa.UniqueConstraint("code", name=op.f("uq_room_types_code")),
    )
    op.create_table(
        "terms",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("academic_year", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("weekdays", postgresql.ARRAY(sa.SmallInteger()), nullable=False),
        sa.Column("availability_open_until", sa.Date(), nullable=True),
        sa.Column("room_capacity_ratio", sa.Double(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status IN ('planning', 'active', 'closed')", name=op.f("ck_terms_known_status")
        ),
        sa.CheckConstraint(
            "cardinality(weekdays) BETWEEN 1 AND 7", name=op.f("ck_terms_weekday_count")
        ),
        sa.CheckConstraint("end_date > start_date", name=op.f("ck_terms_ordered_dates")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_terms")),
        sa.UniqueConstraint("code", name=op.f("uq_terms_code")),
    )
    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_id", sa.String(length=128), nullable=False),
        sa.Column("hostname", sa.String(length=128), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("current_run_id", sa.UUID(), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("worker_id", name=op.f("pk_worker_heartbeats")),
    )
    op.create_index(
        op.f("ix_worker_heartbeats_last_seen_at"),
        "worker_heartbeats",
        ["last_seen_at"],
        unique=False,
    )
    op.create_table(
        "activity_types",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("default_room_type_id", sa.UUID(), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("color ~ '^#[0-9a-fA-F]{6}$'", name=op.f("ck_activity_types_hex_color")),
        sa.ForeignKeyConstraint(
            ["default_room_type_id"],
            ["room_types.id"],
            name=op.f("fk_activity_types_default_room_type_id_room_types"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_types")),
        sa.UniqueConstraint("code", name=op.f("uq_activity_types_code")),
    )
    op.create_table(
        "buildings",
        sa.Column("campus_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campus_id"],
            ["campuses.id"],
            name=op.f("fk_buildings_campus_id_campuses"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_buildings")),
        sa.UniqueConstraint("campus_id", "code", name=op.f("uq_buildings_campus_id_code")),
    )
    op.create_index(op.f("ix_buildings_campus_id"), "buildings", ["campus_id"], unique=False)
    op.create_table(
        "campus_travel_times",
        sa.Column("campus_a_id", sa.UUID(), nullable=False),
        sa.Column("campus_b_id", sa.UUID(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "campus_a_id < campus_b_id", name=op.f("ck_campus_travel_times_ordered_pair")
        ),
        sa.CheckConstraint("minutes >= 0", name=op.f("ck_campus_travel_times_non_negative")),
        sa.ForeignKeyConstraint(
            ["campus_a_id"],
            ["campuses.id"],
            name=op.f("fk_campus_travel_times_campus_a_id_campuses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["campus_b_id"],
            ["campuses.id"],
            name=op.f("fk_campus_travel_times_campus_b_id_campuses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("campus_a_id", "campus_b_id", name=op.f("pk_campus_travel_times")),
    )
    op.create_table(
        "constraint_rules",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("rule_type", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("enforcement", sa.String(length=8), nullable=False),
        sa.Column("tier", sa.SmallInteger(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "enforcement IN ('hard', 'soft')", name=op.f("ck_constraint_rules_known_enforcement")
        ),
        sa.CheckConstraint("tier BETWEEN 1 AND 5", name=op.f("ck_constraint_rules_tier_range")),
        sa.CheckConstraint("weight >= 1", name=op.f("ck_constraint_rules_positive_weight")),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_constraint_rules_term_id_terms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_constraint_rules")),
    )
    op.create_index(
        op.f("ix_constraint_rules_term_id"), "constraint_rules", ["term_id"], unique=False
    )
    op.create_table(
        "courses",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("credits", sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_courses_department_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("code", name=op.f("uq_courses_code")),
    )
    op.create_index(op.f("ix_courses_department_id"), "courses", ["department_id"], unique=False)
    op.create_table(
        "instructors",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=True),
        sa.Column("max_weekly_periods", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "max_weekly_periods IS NULL OR max_weekly_periods > 0",
            name=op.f("ck_instructors_positive_max_load"),
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_instructors_department_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_instructors")),
        sa.UniqueConstraint("code", name=op.f("uq_instructors_code")),
    )
    op.create_index(
        op.f("ix_instructors_department_id"), "instructors", ["department_id"], unique=False
    )
    op.create_table(
        "objective_profiles",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objectives", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_objective_profiles_term_id_terms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_objective_profiles")),
        sa.UniqueConstraint("term_id", "code", name=op.f("uq_objective_profiles_term_id_code")),
    )
    op.create_index(
        op.f("ix_objective_profiles_term_id"), "objective_profiles", ["term_id"], unique=False
    )
    op.create_table(
        "periods",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("joins_next", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint("end_time > start_time", name=op.f("ck_periods_ordered_times")),
        sa.ForeignKeyConstraint(
            ["term_id"], ["terms.id"], name=op.f("fk_periods_term_id_terms"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_periods")),
        sa.UniqueConstraint("term_id", "position", name=op.f("uq_periods_term_id_position")),
    )
    op.create_table(
        "problem_snapshots",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_problem_snapshots_term_id_terms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_problem_snapshots")),
        sa.UniqueConstraint(
            "term_id", "content_hash", name=op.f("uq_problem_snapshots_term_id_content_hash")
        ),
    )
    op.create_table(
        "programmes",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("level", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_programmes_department_id_departments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_programmes")),
        sa.UniqueConstraint("code", name=op.f("uq_programmes_code")),
    )
    op.create_index(
        op.f("ix_programmes_department_id"), "programmes", ["department_id"], unique=False
    )
    op.create_table(
        "timing_variants",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("end_date >= start_date", name=op.f("ck_timing_variants_ordered_dates")),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_timing_variants_term_id_terms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_timing_variants")),
    )
    op.create_index(
        op.f("ix_timing_variants_term_id"), "timing_variants", ["term_id"], unique=False
    )
    op.create_table(
        "activities",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("activity_type_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("duration", sa.SmallInteger(), nullable=False),
        sa.Column("sessions_per_week", sa.SmallInteger(), nullable=False),
        sa.Column("different_days", sa.Boolean(), nullable=False),
        sa.Column("delivery_mode", sa.String(length=16), nullable=False),
        sa.Column("room_type_id", sa.UUID(), nullable=True),
        sa.Column("min_capacity", sa.Integer(), nullable=True),
        sa.Column("campus_id", sa.UUID(), nullable=True),
        sa.Column("building_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "delivery_mode IN ('in_person', 'online')", name=op.f("ck_activities_known_delivery")
        ),
        sa.CheckConstraint("duration BETWEEN 1 AND 12", name=op.f("ck_activities_duration_range")),
        sa.CheckConstraint(
            "min_capacity IS NULL OR min_capacity > 0", name=op.f("ck_activities_positive_capacity")
        ),
        sa.CheckConstraint(
            "sessions_per_week BETWEEN 1 AND 7", name=op.f("ck_activities_sessions_range")
        ),
        sa.ForeignKeyConstraint(
            ["activity_type_id"],
            ["activity_types.id"],
            name=op.f("fk_activities_activity_type_id_activity_types"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["building_id"],
            ["buildings.id"],
            name=op.f("fk_activities_building_id_buildings"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["campus_id"],
            ["campuses.id"],
            name=op.f("fk_activities_campus_id_campuses"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_activities_course_id_courses"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_type_id"],
            ["room_types.id"],
            name=op.f("fk_activities_room_type_id_room_types"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"], ["terms.id"], name=op.f("fk_activities_term_id_terms"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activities")),
        sa.UniqueConstraint("term_id", "id", name=op.f("uq_activities_term_id_id")),
    )
    op.create_index(op.f("ix_activities_course_id"), "activities", ["course_id"], unique=False)
    op.create_index(op.f("ix_activities_term_id"), "activities", ["term_id"], unique=False)
    op.create_table(
        "rooms",
        sa.Column("building_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("room_type_id", sa.UUID(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("capacity > 0", name=op.f("ck_rooms_positive_capacity")),
        sa.ForeignKeyConstraint(
            ["building_id"],
            ["buildings.id"],
            name=op.f("fk_rooms_building_id_buildings"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_rooms_department_id_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["room_type_id"],
            ["room_types.id"],
            name=op.f("fk_rooms_room_type_id_room_types"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rooms")),
        sa.UniqueConstraint("building_id", "code", name=op.f("uq_rooms_building_id_code")),
    )
    op.create_index(op.f("ix_rooms_building_id"), "rooms", ["building_id"], unique=False)
    op.create_index(op.f("ix_rooms_department_id"), "rooms", ["department_id"], unique=False)
    op.create_index(op.f("ix_rooms_room_type_id"), "rooms", ["room_type_id"], unique=False)
    op.create_table(
        "slot_settings",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("period_id", sa.UUID(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("closed_reason", sa.String(length=200), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("penalty", sa.SmallInteger(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "(start_time IS NULL) = (end_time IS NULL) AND (start_time IS NULL OR end_time > start_time)",
            name=op.f("ck_slot_settings_time_override_pair"),
        ),
        sa.CheckConstraint("penalty BETWEEN 0 AND 3", name=op.f("ck_slot_settings_penalty_range")),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name=op.f("ck_slot_settings_weekday_range")),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["periods.id"],
            name=op.f("fk_slot_settings_period_id_periods"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_slot_settings_term_id_terms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_slot_settings")),
        sa.UniqueConstraint(
            "term_id",
            "weekday",
            "period_id",
            name=op.f("uq_slot_settings_term_id_weekday_period_id"),
        ),
    )
    op.create_index(op.f("ix_slot_settings_term_id"), "slot_settings", ["term_id"], unique=False)
    op.create_table(
        "student_groups",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("partition_key", sa.String(length=32), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("programme_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id", name=op.f("ck_student_groups_not_own_parent")
        ),
        sa.CheckConstraint("size >= 0", name=op.f("ck_student_groups_non_negative_size")),
        sa.ForeignKeyConstraint(
            ["programme_id"],
            ["programmes.id"],
            name=op.f("fk_student_groups_programme_id_programmes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["term_id", "parent_id"],
            ["student_groups.term_id", "student_groups.id"],
            name=op.f("fk_student_groups_term_id_student_groups"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_student_groups_term_id_terms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_groups")),
        sa.UniqueConstraint("term_id", "code", name=op.f("uq_student_groups_term_id_code")),
        sa.UniqueConstraint("term_id", "id", name=op.f("uq_student_groups_term_id_id")),
    )
    op.create_index(
        op.f("ix_student_groups_parent_id"), "student_groups", ["parent_id"], unique=False
    )
    op.create_index(
        op.f("ix_student_groups_programme_id"), "student_groups", ["programme_id"], unique=False
    )
    op.create_index(op.f("ix_student_groups_term_id"), "student_groups", ["term_id"], unique=False)
    op.create_table(
        "timing_variant_periods",
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("period_id", sa.UUID(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.CheckConstraint(
            "end_time > start_time", name=op.f("ck_timing_variant_periods_ordered_times")
        ),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["periods.id"],
            name=op.f("fk_timing_variant_periods_period_id_periods"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["timing_variants.id"],
            name=op.f("fk_timing_variant_periods_variant_id_timing_variants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("variant_id", "period_id", name=op.f("pk_timing_variant_periods")),
    )
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=True),
        sa.Column("instructor_id", sa.UUID(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["instructor_id"],
            ["instructors.id"],
            name=op.f("fk_users_instructor_id_instructors"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("instructor_id", name=op.f("uq_users_instructor_id")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_table(
        "activity_features",
        sa.Column("activity_id", sa.UUID(), nullable=False),
        sa.Column("feature_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activities.id"],
            name=op.f("fk_activity_features_activity_id_activities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["feature_id"],
            ["room_features.id"],
            name=op.f("fk_activity_features_feature_id_room_features"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("activity_id", "feature_id", name=op.f("pk_activity_features")),
    )
    op.create_table(
        "activity_groups",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("activity_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["term_id", "activity_id"],
            ["activities.term_id", "activities.id"],
            name=op.f("fk_activity_groups_term_id_activities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["term_id", "group_id"],
            ["student_groups.term_id", "student_groups.id"],
            name=op.f("fk_activity_groups_term_id_student_groups"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("activity_id", "group_id", name=op.f("pk_activity_groups")),
    )
    op.create_index(
        op.f("ix_activity_groups_group_id"), "activity_groups", ["group_id"], unique=False
    )
    op.create_table(
        "activity_instructors",
        sa.Column("activity_id", sa.UUID(), nullable=False),
        sa.Column("instructor_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activities.id"],
            name=op.f("fk_activity_instructors_activity_id_activities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["instructor_id"],
            ["instructors.id"],
            name=op.f("fk_activity_instructors_instructor_id_instructors"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "activity_id", "instructor_id", name=op.f("pk_activity_instructors")
        ),
    )
    op.create_index(
        op.f("ix_activity_instructors_instructor_id"),
        "activity_instructors",
        ["instructor_id"],
        unique=False,
    )
    op.create_table(
        "activity_rooms",
        sa.Column("activity_id", sa.UUID(), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "kind IN ('allowed', 'preferred', 'avoided')", name=op.f("ck_activity_rooms_known_kind")
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activities.id"],
            name=op.f("fk_activity_rooms_activity_id_activities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name=op.f("fk_activity_rooms_room_id_rooms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("activity_id", "room_id", name=op.f("pk_activity_rooms")),
    )
    op.create_index(op.f("ix_activity_rooms_room_id"), "activity_rooms", ["room_id"], unique=False)
    op.create_table(
        "availability_grids",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("instructor_id", sa.UUID(), nullable=True),
        sa.Column("group_id", sa.UUID(), nullable=True),
        sa.Column("room_id", sa.UUID(), nullable=True),
        sa.Column("activity_id", sa.UUID(), nullable=True),
        sa.Column("cells", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "source IN ('self', 'staff', 'import')", name=op.f("ck_availability_grids_known_source")
        ),
        sa.CheckConstraint(
            "num_nonnulls(instructor_id, group_id, room_id, activity_id) = 1",
            name=op.f("ck_availability_grids_one_resource"),
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activities.id"],
            name=op.f("fk_availability_grids_activity_id_activities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["student_groups.id"],
            name=op.f("fk_availability_grids_group_id_student_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["instructor_id"],
            ["instructors.id"],
            name=op.f("fk_availability_grids_instructor_id_instructors"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name=op.f("fk_availability_grids_room_id_rooms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_availability_grids_term_id_terms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_availability_grids_updated_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_availability_grids")),
    )
    op.create_index(
        "uq_availability_activity",
        "availability_grids",
        ["term_id", "activity_id"],
        unique=True,
        postgresql_where=sa.text("activity_id IS NOT NULL"),
    )
    op.create_index(
        "uq_availability_group",
        "availability_grids",
        ["term_id", "group_id"],
        unique=True,
        postgresql_where=sa.text("group_id IS NOT NULL"),
    )
    op.create_index(
        "uq_availability_instructor",
        "availability_grids",
        ["term_id", "instructor_id"],
        unique=True,
        postgresql_where=sa.text("instructor_id IS NOT NULL"),
    )
    op.create_index(
        "uq_availability_room",
        "availability_grids",
        ["term_id", "room_id"],
        unique=True,
        postgresql_where=sa.text("room_id IS NOT NULL"),
    )
    op.create_table(
        "calendar_feed_tokens",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_calendar_feed_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendar_feed_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_calendar_feed_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_calendar_feed_tokens_user_id"), "calendar_feed_tokens", ["user_id"], unique=False
    )
    op.create_table(
        "fixed_placements",
        sa.Column("activity_id", sa.UUID(), nullable=False),
        sa.Column("occurrence", sa.SmallInteger(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("period_id", sa.UUID(), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=True),
        sa.CheckConstraint("occurrence >= 1", name=op.f("ck_fixed_placements_positive_occurrence")),
        sa.CheckConstraint(
            "weekday BETWEEN 0 AND 6", name=op.f("ck_fixed_placements_weekday_range")
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activities.id"],
            name=op.f("fk_fixed_placements_activity_id_activities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["periods.id"],
            name=op.f("fk_fixed_placements_period_id_periods"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name=op.f("fk_fixed_placements_room_id_rooms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("activity_id", "occurrence", name=op.f("pk_fixed_placements")),
    )
    op.create_table(
        "import_batches",
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("term_id", sa.UUID(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rows", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "status IN ('uploaded', 'committed', 'discarded')",
            name=op.f("ck_import_batches_known_status"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_import_batches_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_import_batches_term_id_terms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
    )
    op.create_table(
        "role_assignments",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "department_id IS NULL OR role NOT IN ('system_admin', 'institution_admin')",
            name=op.f("ck_role_assignments_admin_roles_unscoped"),
        ),
        sa.CheckConstraint(
            "role IN ('system_admin', 'institution_admin', 'scheduling_officer', 'department_head', 'instructor', 'student', 'viewer')",
            name=op.f("ck_role_assignments_known_role"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_role_assignments_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_role_assignments_department_id_departments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_role_assignments_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_assignments")),
        sa.UniqueConstraint(
            "user_id",
            "role",
            "department_id",
            name=op.f("uq_role_assignments_user_id_role_department_id"),
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        op.f("ix_role_assignments_user_id"), "role_assignments", ["user_id"], unique=False
    )
    op.create_table(
        "room_feature_links",
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("feature_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["feature_id"],
            ["room_features.id"],
            name=op.f("fk_room_feature_links_feature_id_room_features"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name=op.f("fk_room_feature_links_room_id_rooms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("room_id", "feature_id", name=op.f("pk_room_feature_links")),
    )
    op.create_index(
        op.f("ix_room_feature_links_feature_id"), "room_feature_links", ["feature_id"], unique=False
    )
    op.create_table(
        "scenarios",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("profile_codes", postgresql.ARRAY(sa.String(length=32)), nullable=False),
        sa.Column("scope_department_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("base_solution_id", sa.UUID(), nullable=True),
        sa.Column("minimize_changes", sa.Boolean(), nullable=False),
        sa.Column("solver_mode", sa.String(length=16), nullable=False),
        sa.Column("time_limit_seconds", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "solver_mode IN ('reproducible', 'fastest')", name=op.f("ck_scenarios_known_mode")
        ),
        sa.CheckConstraint(
            "time_limit_seconds BETWEEN 5 AND 86400", name=op.f("ck_scenarios_time_limit_range")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_scenarios_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"], ["terms.id"], name=op.f("fk_scenarios_term_id_terms"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenarios")),
    )
    op.create_index(op.f("ix_scenarios_term_id"), "scenarios", ["term_id"], unique=False)
    op.create_table(
        "student_memberships",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["student_groups.id"],
            name=op.f("fk_student_memberships_group_id_student_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_student_memberships_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "group_id", name=op.f("pk_student_memberships")),
    )
    op.create_index(
        op.f("ix_student_memberships_group_id"), "student_memberships", ["group_id"], unique=False
    )
    op.create_table(
        "user_sessions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=256), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_sessions_token_hash")),
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)
    op.create_table(
        "solver_runs",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("scenario_id", sa.UUID(), nullable=True),
        sa.Column("source_solution_id", sa.UUID(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=True),
        sa.Column("progress", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_by_id", sa.UUID(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("log", sa.Text(), nullable=True),
        sa.Column("app_version", sa.String(length=32), nullable=False),
        sa.Column("solver_version", sa.String(length=32), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('optimize', 'repair', 'relaxation')", name=op.f("ck_solver_runs_known_kind")
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name=op.f("ck_solver_runs_known_status"),
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_id"],
            ["users.id"],
            name=op.f("fk_solver_runs_requested_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            name=op.f("fk_solver_runs_scenario_id_scenarios"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["problem_snapshots.id"],
            name=op.f("fk_solver_runs_snapshot_id_problem_snapshots"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"], ["terms.id"], name=op.f("fk_solver_runs_term_id_terms"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_solver_runs")),
    )
    op.create_index("ix_solver_runs_queue", "solver_runs", ["status", "requested_at"], unique=False)
    op.create_index(
        op.f("ix_solver_runs_scenario_id"), "solver_runs", ["scenario_id"], unique=False
    )
    op.create_index(op.f("ix_solver_runs_term_id"), "solver_runs", ["term_id"], unique=False)
    op.create_table(
        "solutions",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("base_publication_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("profile_code", sa.String(length=32), nullable=True),
        sa.Column("objective_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("is_complete", sa.Boolean(), nullable=False),
        sa.Column("hard_violation_count", sa.Integer(), nullable=False),
        sa.Column("evaluation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("submitted_by_id", sa.UUID(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "origin IN ('solver', 'copy', 'rebase', 'repair', 'restore')",
            name=op.f("ck_solutions_known_origin"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'published', 'archived')",
            name=op.f("ck_solutions_known_status"),
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["users.id"],
            name=op.f("fk_solutions_approved_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_solutions_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["solutions.id"],
            name=op.f("fk_solutions_parent_id_solutions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["solver_runs.id"],
            name=op.f("fk_solutions_run_id_solver_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["problem_snapshots.id"],
            name=op.f("fk_solutions_snapshot_id_problem_snapshots"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_id"],
            ["users.id"],
            name=op.f("fk_solutions_submitted_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"], ["terms.id"], name=op.f("fk_solutions_term_id_terms"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_solutions")),
    )
    op.create_index(op.f("ix_solutions_run_id"), "solutions", ["run_id"], unique=False)
    op.create_index(op.f("ix_solutions_snapshot_id"), "solutions", ["snapshot_id"], unique=False)
    op.create_index(op.f("ix_solutions_term_id"), "solutions", ["term_id"], unique=False)
    op.create_table(
        "solver_run_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["solver_runs.id"],
            name=op.f("fk_solver_run_events_run_id_solver_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_solver_run_events")),
    )
    op.create_index(
        op.f("ix_solver_run_events_run_id"), "solver_run_events", ["run_id"], unique=False
    )
    op.create_table(
        "publications",
        sa.Column("term_id", sa.UUID(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("solution_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("restored_from_id", sa.UUID(), nullable=True),
        sa.Column("published_by_id", sa.UUID(), nullable=True),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["published_by_id"],
            ["users.id"],
            name=op.f("fk_publications_published_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["restored_from_id"],
            ["publications.id"],
            name=op.f("fk_publications_restored_from_id_publications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["problem_snapshots.id"],
            name=op.f("fk_publications_snapshot_id_problem_snapshots"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["solution_id"],
            ["solutions.id"],
            name=op.f("fk_publications_solution_id_solutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["terms.id"],
            name=op.f("fk_publications_term_id_terms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_publications")),
        sa.UniqueConstraint(
            "term_id", "version_no", name=op.f("uq_publications_term_id_version_no")
        ),
    )
    op.create_index(
        "uq_publications_current",
        "publications",
        ["term_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )
    op.create_table(
        "solution_assignments",
        sa.Column("solution_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.SmallInteger(), nullable=False),
        sa.Column("period", sa.SmallInteger(), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=True),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["solution_id"],
            ["solutions.id"],
            name=op.f("fk_solution_assignments_solution_id_solutions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("solution_id", "session_id", name=op.f("pk_solution_assignments")),
    )
    op.create_table(
        "solution_changes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("solution_id", sa.UUID(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_label", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("affected_instructor_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("affected_group_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("affected_room_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_solution_changes_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["solution_id"],
            ["solutions.id"],
            name=op.f("fk_solution_changes_solution_id_solutions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_solution_changes")),
        sa.UniqueConstraint("solution_id", "seq", name=op.f("uq_solution_changes_solution_id_seq")),
    )
    op.create_index(
        "ix_solution_changes_groups",
        "solution_changes",
        ["affected_group_ids"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_solution_changes_instructors",
        "solution_changes",
        ["affected_instructor_ids"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_solution_changes_rooms",
        "solution_changes",
        ["affected_room_ids"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        op.f("ix_solution_changes_solution_id"), "solution_changes", ["solution_id"], unique=False
    )
    op.create_table(
        "occurrence_exceptions",
        sa.Column("publication_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("occurrence_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("new_date", sa.Date(), nullable=True),
        sa.Column("new_period", sa.SmallInteger(), nullable=True),
        sa.Column("new_room_id", sa.UUID(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notice", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "(kind = 'cancelled') OR (kind = 'relocated' AND new_room_id IS NOT NULL) OR (kind = 'rescheduled' AND new_date IS NOT NULL AND new_period IS NOT NULL)",
            name=op.f("ck_occurrence_exceptions_kind_fields"),
        ),
        sa.CheckConstraint(
            "kind IN ('cancelled', 'relocated', 'rescheduled')",
            name=op.f("ck_occurrence_exceptions_known_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_occurrence_exceptions_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["publications.id"],
            name=op.f("fk_occurrence_exceptions_publication_id_publications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_id"],
            ["users.id"],
            name=op.f("fk_occurrence_exceptions_revoked_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_occurrence_exceptions")),
    )
    op.create_index(
        op.f("ix_occurrence_exceptions_publication_id"),
        "occurrence_exceptions",
        ["publication_id"],
        unique=False,
    )
    op.create_index(
        "uq_occurrence_exceptions_active",
        "occurrence_exceptions",
        ["publication_id", "session_id", "occurrence_date"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_table(
        "publication_assignments",
        sa.Column("publication_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.SmallInteger(), nullable=False),
        sa.Column("period", sa.SmallInteger(), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["publications.id"],
            name=op.f("fk_publication_assignments_publication_id_publications"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "publication_id", "session_id", name=op.f("pk_publication_assignments")
        ),
    )

    # Circular references cannot be declared inside CREATE TABLE; add them once every table exists.
    op.create_foreign_key(
        op.f("fk_scenarios_base_solution_id_solutions"),
        "scenarios",
        "solutions",
        ["base_solution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_solver_runs_source_solution_id_solutions"),
        "solver_runs",
        "solutions",
        ["source_solution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_solutions_base_publication_id_publications"),
        "solutions",
        "publications",
        ["base_publication_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # The audit trail is append-only: rows can be inserted, never changed or removed.
    op.execute(
        """
        CREATE FUNCTION audit_events_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only (% rejected)', TG_OP;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_append_only()")
    op.drop_constraint(
        op.f("fk_scenarios_base_solution_id_solutions"), "scenarios", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_solver_runs_source_solution_id_solutions"), "solver_runs", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_solutions_base_publication_id_publications"), "solutions", type_="foreignkey"
    )
    op.drop_table("publication_assignments")
    op.drop_index(
        "uq_occurrence_exceptions_active",
        table_name="occurrence_exceptions",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.drop_index(
        op.f("ix_occurrence_exceptions_publication_id"), table_name="occurrence_exceptions"
    )
    op.drop_table("occurrence_exceptions")
    op.drop_index(op.f("ix_solution_changes_solution_id"), table_name="solution_changes")
    op.drop_index(
        "ix_solution_changes_rooms", table_name="solution_changes", postgresql_using="gin"
    )
    op.drop_index(
        "ix_solution_changes_instructors", table_name="solution_changes", postgresql_using="gin"
    )
    op.drop_index(
        "ix_solution_changes_groups", table_name="solution_changes", postgresql_using="gin"
    )
    op.drop_table("solution_changes")
    op.drop_table("solution_assignments")
    op.drop_index(
        "uq_publications_current", table_name="publications", postgresql_where=sa.text("is_current")
    )
    op.drop_table("publications")
    op.drop_index(op.f("ix_solver_run_events_run_id"), table_name="solver_run_events")
    op.drop_table("solver_run_events")
    op.drop_index(op.f("ix_solutions_term_id"), table_name="solutions")
    op.drop_index(op.f("ix_solutions_snapshot_id"), table_name="solutions")
    op.drop_index(op.f("ix_solutions_run_id"), table_name="solutions")
    op.drop_table("solutions")
    op.drop_index(op.f("ix_solver_runs_term_id"), table_name="solver_runs")
    op.drop_index(op.f("ix_solver_runs_scenario_id"), table_name="solver_runs")
    op.drop_index("ix_solver_runs_queue", table_name="solver_runs")
    op.drop_table("solver_runs")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index(op.f("ix_student_memberships_group_id"), table_name="student_memberships")
    op.drop_table("student_memberships")
    op.drop_index(op.f("ix_scenarios_term_id"), table_name="scenarios")
    op.drop_table("scenarios")
    op.drop_index(op.f("ix_room_feature_links_feature_id"), table_name="room_feature_links")
    op.drop_table("room_feature_links")
    op.drop_index(op.f("ix_role_assignments_user_id"), table_name="role_assignments")
    op.drop_table("role_assignments")
    op.drop_table("import_batches")
    op.drop_table("fixed_placements")
    op.drop_index(op.f("ix_calendar_feed_tokens_user_id"), table_name="calendar_feed_tokens")
    op.drop_table("calendar_feed_tokens")
    op.drop_index(
        "uq_availability_room",
        table_name="availability_grids",
        postgresql_where=sa.text("room_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_availability_instructor",
        table_name="availability_grids",
        postgresql_where=sa.text("instructor_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_availability_group",
        table_name="availability_grids",
        postgresql_where=sa.text("group_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_availability_activity",
        table_name="availability_grids",
        postgresql_where=sa.text("activity_id IS NOT NULL"),
    )
    op.drop_table("availability_grids")
    op.drop_index(op.f("ix_activity_rooms_room_id"), table_name="activity_rooms")
    op.drop_table("activity_rooms")
    op.drop_index(op.f("ix_activity_instructors_instructor_id"), table_name="activity_instructors")
    op.drop_table("activity_instructors")
    op.drop_index(op.f("ix_activity_groups_group_id"), table_name="activity_groups")
    op.drop_table("activity_groups")
    op.drop_table("activity_features")
    op.drop_table("users")
    op.drop_table("timing_variant_periods")
    op.drop_index(op.f("ix_student_groups_term_id"), table_name="student_groups")
    op.drop_index(op.f("ix_student_groups_programme_id"), table_name="student_groups")
    op.drop_index(op.f("ix_student_groups_parent_id"), table_name="student_groups")
    op.drop_table("student_groups")
    op.drop_index(op.f("ix_slot_settings_term_id"), table_name="slot_settings")
    op.drop_table("slot_settings")
    op.drop_index(op.f("ix_rooms_room_type_id"), table_name="rooms")
    op.drop_index(op.f("ix_rooms_department_id"), table_name="rooms")
    op.drop_index(op.f("ix_rooms_building_id"), table_name="rooms")
    op.drop_table("rooms")
    op.drop_index(op.f("ix_activities_term_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_course_id"), table_name="activities")
    op.drop_table("activities")
    op.drop_index(op.f("ix_timing_variants_term_id"), table_name="timing_variants")
    op.drop_table("timing_variants")
    op.drop_index(op.f("ix_programmes_department_id"), table_name="programmes")
    op.drop_table("programmes")
    op.drop_table("problem_snapshots")
    op.drop_table("periods")
    op.drop_index(op.f("ix_objective_profiles_term_id"), table_name="objective_profiles")
    op.drop_table("objective_profiles")
    op.drop_index(op.f("ix_instructors_department_id"), table_name="instructors")
    op.drop_table("instructors")
    op.drop_index(op.f("ix_courses_department_id"), table_name="courses")
    op.drop_table("courses")
    op.drop_index(op.f("ix_constraint_rules_term_id"), table_name="constraint_rules")
    op.drop_table("constraint_rules")
    op.drop_table("campus_travel_times")
    op.drop_index(op.f("ix_buildings_campus_id"), table_name="buildings")
    op.drop_table("buildings")
    op.drop_table("activity_types")
    op.drop_index(op.f("ix_worker_heartbeats_last_seen_at"), table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")
    op.drop_table("terms")
    op.drop_table("room_types")
    op.drop_table("room_features")
    op.drop_table("login_throttles")
    op.drop_table("institution")
    op.drop_index(op.f("ix_idempotency_records_created_at"), table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index(op.f("ix_departments_parent_id"), table_name="departments")
    op.drop_table("departments")
    op.drop_table("campuses")
    op.drop_table("calendar_events")
    op.drop_index(op.f("ix_audit_events_term_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_occurred_at"), table_name="audit_events")
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_index("ix_audit_events_departments", table_name="audit_events", postgresql_using="gin")
    op.drop_index(op.f("ix_audit_events_actor_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_action"), table_name="audit_events")
    op.drop_table("audit_events")
