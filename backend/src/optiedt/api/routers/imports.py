"""Staged CSV/XLSX imports: upload, map columns, review the validation report, commit."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import select

from optiedt.api.deps import DbSession, PrincipalDep, SettingsDep
from optiedt.api.schemas.common import Out, Schema
from optiedt.errors import AppError, PermissionDenied
from optiedt.models import ImportBatch
from optiedt.security.permissions import Permission
from optiedt.services import imports

router = APIRouter(prefix="/imports", tags=["imports"])

PREVIEW_ROWS = 20


class ColumnOut(Out):
    name: str
    label: str
    kind: str
    required: bool
    example: str


class SpecOut(Out):
    code: str
    label: str
    term_scoped: bool
    columns: list[ColumnOut]


class ImportOut(Out):
    id: uuid.UUID
    entity_type: str
    term_id: uuid.UUID | None
    filename: str
    status: str
    headers: list[str]
    preview: list[list[str]]
    row_count: int
    mapping: dict[str, Any]
    report: dict[str, Any]
    created_at: datetime
    committed_at: datetime | None


class MappingIn(Schema):
    columns: dict[str, Annotated[int, Field(ge=0, le=200)]]
    update_existing: bool = True


def _out(batch: ImportBatch) -> ImportOut:
    return ImportOut(
        id=batch.id,
        entity_type=batch.entity_type,
        term_id=batch.term_id,
        filename=batch.filename,
        status=batch.status,
        headers=batch.headers,
        preview=batch.rows[:PREVIEW_ROWS],
        row_count=len(batch.rows),
        mapping=batch.mapping,
        report=batch.report,
        created_at=batch.created_at,
        committed_at=batch.committed_at,
    )


class TooLarge(AppError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            f"The file is larger than {limit // (1024 * 1024)} MB.", code="too_large", status=413
        )


@router.get("/specs", response_model=list[SpecOut])
def list_specs(principal: PrincipalDep) -> list[SpecOut]:
    """What can be imported and the columns of each kind."""
    if not principal.can(Permission.IMPORTS_RUN):
        raise PermissionDenied()
    return [SpecOut.model_validate(spec) for spec in imports.SPECS.values()]


@router.get("/templates/{entity_type}.{fmt}")
def download_template(
    entity_type: str, fmt: Literal["csv", "xlsx"], principal: PrincipalDep
) -> Response:
    if not principal.can(Permission.IMPORTS_RUN):
        raise PermissionDenied()
    headers, example = imports.template(entity_type)
    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerow(example)
        return Response(
            "﻿" + buffer.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{entity_type}.csv"'},
        )
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = entity_type
    sheet.append(headers)
    sheet.append(example)
    output = io.BytesIO()
    workbook.save(output)
    return Response(
        output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{entity_type}.xlsx"'},
    )


@router.get("", response_model=list[ImportOut])
def list_imports(
    db: DbSession,
    principal: PrincipalDep,
    entity_type: str | None = None,
    term_id: uuid.UUID | None = None,
) -> list[ImportOut]:
    if not principal.can(Permission.IMPORTS_RUN):
        raise PermissionDenied()
    statement = select(ImportBatch).order_by(ImportBatch.created_at.desc()).limit(100)
    if not principal.scope(Permission.IMPORTS_RUN).everywhere:
        statement = statement.where(ImportBatch.created_by_id == principal.user_id)
    if entity_type is not None:
        statement = statement.where(ImportBatch.entity_type == entity_type)
    if term_id is not None:
        statement = statement.where(ImportBatch.term_id == term_id)
    return [_out(batch) for batch in db.scalars(statement)]


@router.post("", response_model=ImportOut, status_code=201)
async def upload(
    db: DbSession,
    principal: PrincipalDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="A .csv or .xlsx file")],
    entity_type: Annotated[str, Form(max_length=32)],
    term_id: Annotated[uuid.UUID | None, Form()] = None,
) -> ImportOut:
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise TooLarge(settings.max_upload_bytes)
    batch = imports.upload(
        db,
        principal,
        entity_type=entity_type,
        term_id=term_id,
        filename=file.filename or "upload",
        content=content,
    )
    db.commit()
    return _out(batch)


@router.get("/{batch_id}", response_model=ImportOut)
def get_import(batch_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> ImportOut:
    return _out(imports.get_batch(db, principal, batch_id))


@router.put("/{batch_id}/mapping", response_model=ImportOut)
def set_mapping(
    batch_id: uuid.UUID, body: MappingIn, db: DbSession, principal: PrincipalDep
) -> ImportOut:
    batch = imports.set_mapping(
        db, principal, batch_id, columns=body.columns, update_existing=body.update_existing
    )
    db.commit()
    return _out(batch)


@router.post("/{batch_id}/commit", response_model=ImportOut)
def commit(batch_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> ImportOut:
    try:
        batch = imports.commit(db, principal, batch_id)
    except AppError:
        db.rollback()
        raise
    db.commit()
    return _out(batch)


@router.delete("/{batch_id}", status_code=204)
def discard(batch_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> None:
    imports.discard(db, principal, batch_id)
    db.commit()
