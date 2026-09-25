"""The audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from optiedt.api.deps import DbSession, PageDep, PrincipalDep
from optiedt.api.schemas.audit import AuditEventOut
from optiedt.api.schemas.common import Page
from optiedt.services import audit_query

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=Page[AuditEventOut])
def list_audit_events(
    db: DbSession,
    principal: PrincipalDep,
    paging: PageDep,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    term_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> Page[AuditEventOut]:
    items, total = audit_query.list_events(
        db,
        principal,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        action=action,
        term_id=term_id,
        since=since,
        until=until,
        q=q,
        offset=paging.offset,
        limit=paging.page_size,
    )
    return Page(
        items=[AuditEventOut.model_validate(e) for e in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )
