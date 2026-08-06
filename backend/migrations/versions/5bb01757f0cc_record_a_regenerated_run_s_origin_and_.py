"""Record a regenerated run's origin and overrides

Revision ID: 5bb01757f0cc
Revises: 04462f0db630
Create Date: 2026-08-06 17:57:43.191889

FR-23. A run produced by accepting a recommendation records which run and
candidate it came from, which of the three catalogue actions was accepted, and
the locks and exclusions it solved under - composed along the chain (C-20).

⚠️ `overrides` is NOT NULL with a server default of `{}`. Autogenerate emitted
it NOT NULL with no default, which cannot be applied to a table that already
holds runs; every existing run predates regeneration and correctly has no
overrides, so an empty object is the right value for them rather than a
placeholder. The default is left in place so the same is true of any row a
future writer inserts without naming the column.

`origin_run_id` is deliberately not a foreign key. It is provenance: a run must
not become undeletable because a later one cites it, and a cascade would delete
the regenerated run along with its origin - destroying exactly the record
invariant 6 exists to keep.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5bb01757f0cc"
down_revision: str | None = "04462f0db630"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("origin_run_id", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("origin_candidate_id", sa.String(length=64), nullable=True))
    op.add_column("runs", sa.Column("origin_action_kind", sa.String(length=32), nullable=True))
    op.add_column("runs", sa.Column("origin_action_detail", sa.String(length=512), nullable=True))
    op.add_column(
        "runs",
        sa.Column("overrides", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index(op.f("ix_runs_origin_run_id"), "runs", ["origin_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_runs_origin_run_id"), table_name="runs")
    op.drop_column("runs", "overrides")
    op.drop_column("runs", "origin_action_detail")
    op.drop_column("runs", "origin_action_kind")
    op.drop_column("runs", "origin_candidate_id")
    op.drop_column("runs", "origin_run_id")
