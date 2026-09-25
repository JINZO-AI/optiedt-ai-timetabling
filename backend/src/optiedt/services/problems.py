"""Parsed problems of stored snapshots.

Snapshots never change once stored (ADR 0008), so their parsed form is cached per process by
snapshot identifier."""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict

from sqlalchemy.orm import Session

from optiedt.errors import NotFound
from optiedt.models import ProblemSnapshot
from optiedt.problem.model import Problem, build_problem
from optiedt.problem.snapshot import Snapshot

CACHE_SIZE = 8

_cache: OrderedDict[uuid.UUID, Problem] = OrderedDict()
_lock = threading.Lock()


def problem_for(db: Session, snapshot_id: uuid.UUID) -> Problem:
    with _lock:
        cached = _cache.get(snapshot_id)
        if cached is not None:
            _cache.move_to_end(snapshot_id)
            return cached
    row = db.get(ProblemSnapshot, snapshot_id)
    if row is None:
        raise NotFound("Snapshot")
    problem = build_problem(Snapshot.model_validate(row.payload))
    with _lock:
        _cache[snapshot_id] = problem
        _cache.move_to_end(snapshot_id)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return problem
