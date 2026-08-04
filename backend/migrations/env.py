"""Alembic environment.

⚠️ **The URL comes from the application's own settings, never from
`alembic.ini`.** Two sources for one connection string is how a migration ends
up applied to a different database than the one the API talks to — and on a
machine where another PostgreSQL owns port 5432, that database may well accept
the credentials and take the schema silently (README.md, 2026-08-04). Reading
`Settings` means `OPTIEDT_DATABASE_URL` and `backend/.env` govern both.

`compare_type` is on so that `--autogenerate` notices a column whose type
changed. Off by default in alembic, and a silent no-op is the wrong default for
a schema that is meant to be versioned.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from optiedt.core.config import Settings

# Every model module must be imported for `Base.metadata` to be complete: an
# autogenerate run against a partial metadata emits DROP statements for the
# tables it cannot see.
from optiedt.db import models  # noqa: F401
from optiedt.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", Settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
