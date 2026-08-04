"""The declarative base, and the naming convention migrations depend on.

The convention is not cosmetic. Alembic's autogenerate compares the metadata
against the live database, and PostgreSQL names an unnamed constraint for
itself — so without a deterministic convention a later `--autogenerate` emits
spurious drops and recreates for constraints that never changed. Set once,
here, before the first migration exists; changing it afterwards means renaming
every constraint already in the database.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
