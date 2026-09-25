"""Idempotent POST requests (docs/design/api.md): a request carrying an ``Idempotency-Key``
is performed once per caller and key; a retry with the same key and body replays the stored
response, and the same key with a different body is refused."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Header
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from optiedt.errors import Conflict
from optiedt.models import IdempotencyRecord
from optiedt.security.permissions import Principal

IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$",
        description="Makes the request safe to retry: repeats return the first response.",
    ),
]


def _fingerprint(endpoint: str, body: Any) -> str:
    text = json.dumps([endpoint, body], sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode()).hexdigest()


def _replay(record: IdempotencyRecord, endpoint: str, fingerprint: str) -> JSONResponse:
    if record.endpoint != endpoint or record.request_hash != fingerprint:
        raise Conflict(
            "This Idempotency-Key was already used for a different request.",
            code="idempotency_key_reused",
        )
    return JSONResponse(record.body, status_code=record.status_code)


def perform(
    db: Session,
    principal: Principal,
    key: str | None,
    endpoint: str,
    body: Any,
    action: Callable[[], tuple[int, Any]],
) -> JSONResponse:
    """Runs ``action`` (which returns a status code and a JSON-ready body) at most once per
    key, committing its changes together with the stored response."""
    fingerprint = _fingerprint(endpoint, body)
    if key is not None:
        existing = db.get(IdempotencyRecord, (principal.user_id, key))
        if existing is not None:
            return _replay(existing, endpoint, fingerprint)
    status, response = action()
    if key is not None:
        db.add(
            IdempotencyRecord(
                user_id=principal.user_id,
                key=key,
                endpoint=endpoint,
                request_hash=fingerprint,
                status_code=status,
                body=response,
            )
        )
    try:
        db.commit()
    except IntegrityError:
        # The same key arrived twice at once and the other request won: answer like it.
        db.rollback()
        if key is None:
            raise
        winner = db.get(IdempotencyRecord, (principal.user_id, key))
        if winner is None:
            raise
        return _replay(winner, endpoint, fingerprint)
    return JSONResponse(response, status_code=status)
