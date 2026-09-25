"""Reading the audit trail, filtered to what the caller may see."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Session

from optiedt.models import AuditEvent
from optiedt.security.permissions import Permission, Principal
from optiedt.services.crud import page


def list_events(
    db: Session,
    principal: Principal,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    term_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    q: str | None = None,
    offset: int,
    limit: int,
) -> tuple[Sequence[AuditEvent], int]:
    principal.require(Permission.AUDIT_READ)
    scope = principal.scope(Permission.AUDIT_READ)
    statement = select(AuditEvent).order_by(AuditEvent.id.desc())
    if not scope.everywhere:
        departments = sorted(scope.departments)
        statement = statement.where(
            AuditEvent.department_ids.overlap(cast(departments, ARRAY(UUID(as_uuid=True))))
        )
    if entity_type:
        statement = statement.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        statement = statement.where(AuditEvent.entity_id == entity_id)
    if actor_id:
        statement = statement.where(AuditEvent.actor_id == actor_id)
    if action:
        statement = statement.where(AuditEvent.action.startswith(action))
    if term_id:
        statement = statement.where(AuditEvent.term_id == term_id)
    if since:
        statement = statement.where(AuditEvent.occurred_at >= since)
    if until:
        statement = statement.where(AuditEvent.occurred_at < until)
    if q:
        statement = statement.where(AuditEvent.summary.ilike(f"%{q.strip()}%"))
    return page(db, statement, offset=offset, limit=limit)
