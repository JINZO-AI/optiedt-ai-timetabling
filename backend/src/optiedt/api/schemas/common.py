"""Shared schema building blocks."""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

Code = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32, pattern=r"^\S+$")
]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]


class Schema(BaseModel):
    """Request bodies reject unknown fields so a typo is an error, not a silent no-op."""

    model_config = ConfigDict(extra="forbid")


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class Versioned(Schema):
    version: int


class Patch(Schema):
    """Partial update. Only fields present in the request change; ``null`` clears a field
    only where the field is optional."""

    version: int
    required_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _no_null_for_required(self) -> Patch:
        for name in self.required_fields & self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be empty")
        return self

    def changes(self) -> dict[str, object]:
        return self.model_dump(exclude_unset=True, exclude={"version"})
