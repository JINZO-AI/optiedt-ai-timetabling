"""Writing to the append-only audit trail."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from optiedt.context import client_ip_var, request_id_var
from optiedt.models import AuditEvent
from optiedt.security.permissions import Principal

SYSTEM_LABEL = "system"


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID | Decimal):
        return str(value)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list | tuple | set | frozenset):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def field_changes(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, list[Any]]:
    """``{field: [old, new]}`` for every field whose value differs."""
    return {
        key: [_jsonable(before.get(key)), _jsonable(after.get(key))]
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }


def snapshot_fields(entity: object, fields: Iterable[str]) -> dict[str, Any]:
    return {name: getattr(entity, name) for name in fields}


def record(
    db: Session,
    actor: Principal | None,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str | None,
    summary: str,
    changes: Mapping[str, Any] | None = None,
    reason: str | None = None,
    term_id: uuid.UUID | None = None,
    department_ids: Iterable[uuid.UUID | None] = (),
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor.user_id if actor else None,
        actor_label=actor.label if actor else SYSTEM_LABEL,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        term_id=term_id,
        department_ids=sorted({d for d in department_ids if d is not None}),
        summary=summary,
        changes=_jsonable(dict(changes)) if changes else None,
        reason=reason,
        request_id=request_id_var.get(),
        ip_address=client_ip_var.get(),
    )
    db.add(event)
    return event
