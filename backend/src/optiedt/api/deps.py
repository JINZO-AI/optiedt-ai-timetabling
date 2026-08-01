"""Shared dependencies: settings, the loaded instance, the stores.

The instance is read from the 13 CSVs **once per process** and cached. It is a
frozen dataclass, so sharing one copy between requests is safe, and re-reading
36 KB of CSV on every request would be waste that hides itself.

⚠️ `Settings.instance_path` defaults to `"../data/instance"`, which is relative
to `backend/`. Resolving it against the current working directory would make
the API work under `uvicorn` started from `backend/` and fail under pytest
started from the repository root — a difference that shows up as "the instance
is missing" rather than as a path bug. It is resolved against this file's
location instead, so it does not depend on where the process was started.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from optiedt.core.config import Settings
from optiedt.domain.instance import Instance
from optiedt.instance.loader import load_instance
from optiedt.services.availability import AvailabilityStore, InMemoryAvailabilityStore

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def resolve_instance_path(settings: Settings) -> Path:
    """Absolute path of `data/instance/`, independent of the working directory."""
    configured = Path(settings.instance_path)
    if configured.is_absolute():
        return configured
    return (_BACKEND_ROOT / configured).resolve()


@lru_cache(maxsize=1)
def get_instance() -> Instance:
    """The reference instance, loaded once.

    Deliberately NOT the instance a run solves — that one carries the teachers'
    declarations on top (`services.availability.apply_declarations`). Keeping
    the loaded instance pristine means a declaration can be withdrawn.
    """
    return load_instance(resolve_instance_path(get_settings()))


@lru_cache(maxsize=1)
def get_availability_store() -> AvailabilityStore:
    """In-memory in Phase 4; Phase 5 substitutes a database-backed store."""
    return InMemoryAvailabilityStore()


SettingsDep = Annotated[Settings, Depends(get_settings)]
InstanceDep = Annotated[Instance, Depends(get_instance)]
AvailabilityStoreDep = Annotated[AvailabilityStore, Depends(get_availability_store)]
