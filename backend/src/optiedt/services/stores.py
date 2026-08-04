"""Which store implementation a process uses, decided in one place.

**This module exists so that `optiedt.api` never imports `optiedt.db`.**
`docs/architecture.md`'s module map gives the API layer `domain` and `services`
and nothing else, and `.importlinter`'s `api-cannot-reach-the-database`
contract turns that into a build failure. Without a factory here, `api/deps.py`
would have to name `SqlRunStore` itself.

The choice is configuration, not detection. A store that silently fell back to
memory when the database was unreachable would lose every run of that session
while the application looked healthy — and FR-19 is precisely the requirement
that runs survive. `persistence = "memory"` has to be asked for.
"""

from __future__ import annotations

from optiedt.core.config import Settings
from optiedt.services.availability import AvailabilityStore, InMemoryAvailabilityStore
from optiedt.services.publications import InMemoryPublicationStore, PublicationStore
from optiedt.services.runs import InMemoryRunStore, RunStore
from optiedt.services.users import InMemoryUserStore, UserStore

MEMORY = "memory"
DATABASE = "database"


def build_run_store(settings: Settings) -> RunStore:
    if settings.persistence == MEMORY:
        return InMemoryRunStore()
    return _sql_run_store(settings)


def build_availability_store(settings: Settings) -> AvailabilityStore:
    if settings.persistence == MEMORY:
        return InMemoryAvailabilityStore()
    return _sql_availability_store(settings)


def build_user_store(settings: Settings) -> UserStore:
    if settings.persistence == MEMORY:
        return InMemoryUserStore()
    return _sql_user_store(settings)


def build_publication_store(settings: Settings) -> PublicationStore:
    if settings.persistence == MEMORY:
        return InMemoryPublicationStore()
    return _sql_publication_store(settings)


# Imported inside the functions, not at module level: `optiedt.db` pulls in
# SQLAlchemy and the whole mapper registry, and a process configured for
# `memory` has no reason to pay for it - nor to fail at import time if the
# driver is missing.


def _sql_run_store(settings: Settings) -> RunStore:
    from optiedt.db.repositories import SqlRunStore
    from optiedt.db.session import get_session_factory

    return SqlRunStore(get_session_factory(settings.database_url))


def _sql_availability_store(settings: Settings) -> AvailabilityStore:
    from optiedt.db.repositories import SqlAvailabilityStore
    from optiedt.db.session import get_session_factory

    return SqlAvailabilityStore(get_session_factory(settings.database_url))


def _sql_user_store(settings: Settings) -> UserStore:
    from optiedt.db.repositories import SqlUserStore
    from optiedt.db.session import get_session_factory

    return SqlUserStore(get_session_factory(settings.database_url))


def _sql_publication_store(settings: Settings) -> PublicationStore:
    from optiedt.db.repositories import SqlPublicationStore
    from optiedt.db.session import get_session_factory

    return SqlPublicationStore(get_session_factory(settings.database_url))
