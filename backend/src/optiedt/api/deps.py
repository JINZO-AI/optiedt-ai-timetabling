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
from optiedt.services.availability import (
    AvailabilityStore,
    InMemoryAvailabilityStore,
    apply_declarations,
)
from optiedt.services.runs import InMemoryRunStore, RunStore
from optiedt.tasks.executor import RunExecutor, cp_sat_factory

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


@lru_cache(maxsize=1)
def get_run_store() -> RunStore:
    """In-memory in Phase 4; the run record proper is FR-19, Phase 5."""
    return InMemoryRunStore()


def solve_instance() -> Instance:
    """The instance a run actually solves: the loaded one plus declarations.

    This is where FR-2 meets FR-13 — the reason the availability grid is not a
    screen that writes to nothing. Resolved per run rather than cached, so a
    declaration made between two runs is picked up by the second.
    """
    return apply_declarations(get_instance(), get_availability_store())


@lru_cache(maxsize=1)
def get_executor() -> RunExecutor:
    """One executor per process, one solve at a time.

    The solver factory comes from `tasks`, not from here: this layer may not
    import the solver at all (`.importlinter`). The API asks for an executor
    and never names CP-SAT.
    """
    settings = get_settings()
    return RunExecutor(
        store=get_run_store(),
        instance_provider=solve_instance,
        solver_factory=cp_sat_factory(
            workers=settings.solver_workers,
            wall_clock_ceiling_seconds=settings.solver_wall_clock_ceiling_seconds,
        ),
    )


SettingsDep = Annotated[Settings, Depends(get_settings)]
InstanceDep = Annotated[Instance, Depends(get_instance)]
AvailabilityStoreDep = Annotated[AvailabilityStore, Depends(get_availability_store)]
RunStoreDep = Annotated[RunStore, Depends(get_run_store)]
ExecutorDep = Annotated[RunExecutor, Depends(get_executor)]
