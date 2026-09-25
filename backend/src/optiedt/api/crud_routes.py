"""Registers get/create/update/delete routes for a reference-data ``Resource``.

This module deliberately does not use ``from __future__ import annotations``: FastAPI reads
the endpoint annotations at registration time, and here they are the schema classes passed in.
"""

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from optiedt.api.deps import DbSession, PrincipalDep
from optiedt.api.schemas.reference import Patch
from optiedt.security.permissions import Permission
from optiedt.services import resources
from optiedt.services.crud import get_or_404
from optiedt.services.resources import Resource


def register_crud(
    router: APIRouter,
    resource: Resource,
    *,
    create_schema: type[BaseModel],
    patch_schema: type[Patch],
    out_schema: type[BaseModel],
    read_permission: Permission = Permission.REFERENCE_READ,
) -> None:
    label = resource.label.capitalize()

    def get_one(record_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> Any:
        principal.require(read_permission)
        return out_schema.model_validate(get_or_404(db, resource.model, record_id, label))

    def create(body: create_schema, db: DbSession, principal: PrincipalDep) -> Any:  # type: ignore[valid-type]
        record = resources.create(db, principal, resource, body.model_dump())  # type: ignore[attr-defined]
        db.commit()
        db.refresh(record)
        return out_schema.model_validate(record)

    def update(
        record_id: uuid.UUID,
        body: patch_schema,  # type: ignore[valid-type]
        db: DbSession,
        principal: PrincipalDep,
    ) -> Any:
        record = resources.update(
            db,
            principal,
            resource,
            record_id,
            version=body.version,  # type: ignore[attr-defined]
            values=body.changes(),  # type: ignore[attr-defined]
        )
        db.commit()
        db.refresh(record)
        return out_schema.model_validate(record)

    def remove(record_id: uuid.UUID, db: DbSession, principal: PrincipalDep) -> None:
        resources.delete(db, principal, resource, record_id)
        db.commit()

    router.add_api_route(
        "/{record_id}",
        get_one,
        methods=["GET"],
        response_model=out_schema,
        summary=f"Get a {resource.label}",
    )
    router.add_api_route(
        "",
        create,
        methods=["POST"],
        response_model=out_schema,
        status_code=201,
        summary=f"Create a {resource.label}",
    )
    router.add_api_route(
        "/{record_id}",
        update,
        methods=["PATCH"],
        response_model=out_schema,
        summary=f"Update a {resource.label}",
    )
    router.add_api_route(
        "/{record_id}",
        remove,
        methods=["DELETE"],
        status_code=204,
        summary=f"Delete a {resource.label} that nothing references",
    )
