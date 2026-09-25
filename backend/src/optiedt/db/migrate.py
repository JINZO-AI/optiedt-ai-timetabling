"""Programmatic access to Alembic: upgrade, and the schema revision check used by readiness."""

from __future__ import annotations

from functools import lru_cache

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection


def alembic_config(database_url: str | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", "optiedt.db:migrations")
    if database_url:
        config.attributes["database_url"] = database_url
    return config


def upgrade_to_head(database_url: str | None = None) -> None:
    command.upgrade(alembic_config(database_url), "head")


@lru_cache(maxsize=1)
def head_revision() -> str:
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    if head is None:  # pragma: no cover - the package always ships migrations
        raise RuntimeError("no migration scripts found")
    return head


def current_revision(connection: Connection) -> str | None:
    return MigrationContext.configure(connection).get_current_revision()
