"""Test harness.

Tests run against a real PostgreSQL database (``OPTIEDT_TEST_DATABASE_URL``); each
pytest-xdist worker gets its own database next to it. The schema is built once per session
with the application's own migrations. Each test runs inside an outer transaction that is
rolled back afterwards; application commits become savepoint releases.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from argon2 import PasswordHasher
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from optiedt.api.app import create_app
from optiedt.api.deps import get_db
from optiedt.config import Settings, get_settings
from optiedt.db.migrate import upgrade_to_head
from optiedt.security import passwords

TEST_DATABASE_URL = os.environ.get(
    "OPTIEDT_TEST_DATABASE_URL",
    "postgresql+psycopg://optiedt:optiedt@localhost:5432/optiedt_test",
)

# Production Argon2 parameters cost ~80 ms per hash; tests create many accounts.
passwords._hasher = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)


def _database_url() -> str:
    """The test database of this process: one per pytest-xdist worker."""
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    if not worker:
        return TEST_DATABASE_URL
    url = make_url(TEST_DATABASE_URL)
    name = f"{url.database}_{worker}"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
            )
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()
    return url.set(database=name).render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        environment="test",
        database_url=_database_url(),
        log_format="console",
        log_level="WARNING",
    )


@pytest.fixture(scope="session")
def engine(settings: Settings) -> Iterator[Engine]:
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    upgrade_to_head(settings.database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    conn = engine.connect()
    outer = conn.begin()
    try:
        yield conn
    finally:
        if outer.is_active:
            outer.rollback()
        conn.close()


@pytest.fixture
def db(connection: Connection) -> Iterator[Session]:
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(settings: Settings, db: Session) -> FastAPI:
    application = create_app(settings)

    def _db() -> Iterator[Session]:
        yield db

    application.dependency_overrides[get_db] = _db
    application.dependency_overrides[get_settings] = lambda: settings
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
