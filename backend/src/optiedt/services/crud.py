"""Small helpers shared by the data-management services."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from optiedt.errors import NotFound, StaleVersion
from optiedt.services.audit import field_changes, snapshot_fields


def get_or_404[T](db: Session, model: type[T], entity_id: uuid.UUID, label: str) -> T:
    entity = db.get(model, entity_id)
    if entity is None:
        raise NotFound(label)
    return entity


def check_version(entity: Any, expected: int, label: str) -> None:
    if entity.version != expected:
        raise StaleVersion(label)


def apply_changes(entity: object, values: Mapping[str, Any]) -> dict[str, list[Any]]:
    """Assign ``values`` and return ``{field: [old, new]}`` for what actually changed."""
    before = snapshot_fields(entity, values.keys())
    for name, value in values.items():
        setattr(entity, name, value)
    return field_changes(before, snapshot_fields(entity, values.keys()))


def page[T](
    db: Session,
    statement: Select[T],
    *,
    offset: int,
    limit: int,
) -> tuple[Sequence[T], int]:
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    rows = db.scalars(statement.offset(offset).limit(limit)).all()
    return rows, int(total or 0)


def apply_sort[T](
    statement: Select[T],
    sort: str | None,
    columns: Mapping[str, Any],
    default: Iterable[Any],
) -> Select[T]:
    """``sort`` is a comma-separated list of column names, ``-`` prefix for descending."""
    clauses = []
    for part in (sort or "").split(","):
        name = part.strip()
        if not name:
            continue
        descending = name.startswith("-")
        column = columns.get(name.lstrip("-"))
        if column is None:
            continue
        clauses.append(column.desc() if descending else column.asc())
    return statement.order_by(*(clauses or list(default)))


def map_items[T, R](items: Iterable[T], mapper: Callable[[T], R]) -> list[R]:
    return [mapper(item) for item in items]
