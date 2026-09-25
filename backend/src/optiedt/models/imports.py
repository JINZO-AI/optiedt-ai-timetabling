"""Staged file imports: uploaded, mapped, validated, then committed in one transaction."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from optiedt.db.base import Base, UuidPk

IMPORT_STATUSES = ("uploaded", "committed", "discarded")


class ImportBatch(UuidPk, Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN (" + ", ".join(f"'{s}'" for s in IMPORT_STATUSES) + ")",
            name="known_status",
        ),
    )

    entity_type: Mapped[str] = mapped_column(String(32))
    term_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="uploaded")
    headers: Mapped[list[str]] = mapped_column(JSONB)
    rows: Mapped[list[list[str]]] = mapped_column(JSONB)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    committed_at: Mapped[datetime | None]
