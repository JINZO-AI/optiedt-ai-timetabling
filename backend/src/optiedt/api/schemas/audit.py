from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from optiedt.api.schemas.common import Out


class AuditEventOut(Out):
    id: int
    occurred_at: datetime
    actor_id: uuid.UUID | None
    actor_label: str
    action: str
    entity_type: str
    entity_id: str | None
    term_id: uuid.UUID | None
    summary: str
    changes: dict[str, Any] | None
    reason: str | None
    request_id: str | None
