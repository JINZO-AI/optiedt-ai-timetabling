"""Engine and session factory.

**Built lazily, on first use.** Importing this module must not open a socket:
`optiedt.api.deps` is imported by every test that touches the API, and most of
them inject an in-memory store and never reach a database. An engine created at
import time would make those tests depend on PostgreSQL being up in order to
not use it.

One engine per process, one session per unit of work. `pool_pre_ping` is set
because a development database is routinely stopped and restarted underneath a
running API (`docker compose down`), and the failure without it is a stale
pooled connection surfacing as an error on an unrelated request minutes later.
"""

from __future__ import annotations

from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


@cache
def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, future=True)


@cache
def get_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(database_url), expire_on_commit=False, future=True)
