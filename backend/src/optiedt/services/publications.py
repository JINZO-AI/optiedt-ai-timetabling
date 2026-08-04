"""Publishing a timetable, and the trace it must leave — FR-19's other half.

The acceptance criterion is:

    Every published timetable traces back to its run, seed and weights.

So a publication is **not** a copy of a timetable. It names the candidate and
the run, and `PublishedTimetable` below assembles the trace by reading the run
record — the seed, the weight vector in force and the model version — from the
one place that holds it. A copy would satisfy the words and destroy the
intent: two records of one timetable can disagree, and then nothing says which
was published.

⚠️ **`model_version` is part of the trace, not decoration.** A score is only
comparable across runs computed the same way, so a published timetable whose
score is quoted a year later needs to say which model produced it.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from optiedt.domain.entities import (
    Candidate,
    CandidateId,
    ConstraintCode,
    Publication,
    RunId,
)


class PublicationStore(Protocol):
    """Publications, newest first. `SqlPublicationStore` is the real one."""

    def publish(self, publication: Publication) -> None: ...

    def all(self) -> tuple[Publication, ...]: ...

    def for_candidate(self, candidate: CandidateId) -> Publication | None: ...


@dataclass(frozen=True, slots=True)
class PublishedTimetable:
    """A publication together with everything it traces back to.

    Assembled rather than stored: every field below already exists on the run
    record, and duplicating them here would create a second answer to "what
    seed produced this?" that could drift from the first.
    """

    publication: Publication
    candidate: Candidate
    seed: int
    weights: dict[ConstraintCode, float]
    model_version: str
    deterministic_budget: float


class InMemoryPublicationStore:
    """Dict-backed, guarded by a lock. For tests and `persistence = memory`."""

    def __init__(self) -> None:
        self._by_candidate: dict[CandidateId, Publication] = {}
        self._lock = threading.Lock()

    def publish(self, publication: Publication) -> None:
        with self._lock:
            self._by_candidate[publication.candidate] = publication

    def all(self) -> tuple[Publication, ...]:
        with self._lock:
            return tuple(
                sorted(self._by_candidate.values(), key=lambda p: p.published_at, reverse=True)
            )

    def for_candidate(self, candidate: CandidateId) -> Publication | None:
        with self._lock:
            return self._by_candidate.get(candidate)


def new_publication(candidate: CandidateId, run: RunId, user: str) -> Publication:
    return Publication(
        candidate=candidate,
        run=run,
        published_at=datetime.now(UTC),
        user=user,
    )
