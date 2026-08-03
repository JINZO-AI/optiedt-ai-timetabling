"""FR-5, FR-14, FR-15, FR-16, FR-17 — reading and comparing candidates.

**Every figure a screen shows comes from here.** `docs/architecture.md` gives
the presentation layer leave to "display, filter, print, ask" and forbids it to
"compute a score, decide an order". So the ranking order is the order this
module returns, and the contributions are computed here — a frontend that
sorted candidates itself, or recomputed `100 * w * (nA - nB)` in TypeScript,
would have moved a decision across the layer boundary.

The comparison decomposes under the run's **weights in force**, never under a
candidate's producing profile: the identity

    score(A) - score(B) = 100 * sum( w_i * ( n_i(A) - n_i(B) ) )

only holds when the same w_i prices both sides.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from optiedt.api.deps import RunStoreDep
from optiedt.api.schemas import (
    CandidateOut,
    DecompositionOut,
    DominanceVerdictOut,
    RecommendedCandidateOut,
)
from optiedt.domain.entities import Candidate
from optiedt.services.runs import (
    RunRecord,
    candidate_of,
    decomposition_for,
    dominance_for,
    recommendation_for,
)

router = APIRouter(tags=["candidates"])


def _require_run(store: RunStoreDep, run_id: str) -> RunRecord:
    record = store.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No run {run_id!r}")
    return record


def _require_candidate(record: RunRecord, candidate_id: str) -> Candidate:
    candidate = candidate_of(record, candidate_id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No candidate {candidate_id!r} in run {record.run.id!r}",
        )
    return candidate


@router.get(
    "/runs/{run_id}/candidates",
    response_model=list[CandidateOut],
    summary="Candidates of a run, best first",
)
def list_candidates(store: RunStoreDep, run_id: str) -> list[CandidateOut]:
    """Returned in RANK order. The client displays this order, it does not sort."""
    return [CandidateOut.of(c) for c in _require_run(store, run_id).candidates]


@router.get(
    "/runs/{run_id}/candidates/{candidate_id}",
    response_model=CandidateOut,
    summary="One candidate with its placements and sub-scores",
)
def read_candidate(store: RunStoreDep, run_id: str, candidate_id: str) -> CandidateOut:
    record = _require_run(store, run_id)
    return CandidateOut.of(_require_candidate(record, candidate_id))


@router.get(
    "/runs/{run_id}/comparison",
    response_model=DecompositionOut,
    summary="FR-15 — the difference between two candidates, criterion by criterion",
)
def compare(
    store: RunStoreDep,
    run_id: str,
    a: str = Query(description="Candidate id on the left"),
    b: str = Query(description="Candidate id on the right"),
) -> DecompositionOut:
    record = _require_run(store, run_id)
    left = _require_candidate(record, a)
    right = _require_candidate(record, b)
    if left.id == right.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A candidate cannot be compared with itself",
        )
    return DecompositionOut.of(decomposition_for(record, left, right))


@router.get(
    "/runs/{run_id}/dominance",
    response_model=list[DominanceVerdictOut],
    summary="FR-17 — candidates another improves on across the board",
)
def dominance(store: RunStoreDep, run_id: str) -> list[DominanceVerdictOut]:
    """⚠️ The top-ranked candidate is never dominated — provably (C-14).

    A dominated runner-up is ordinary and is what this reports. Do not build a
    "top candidate is dominated" indicator on it; that state cannot occur under
    a linear weighted sum with non-negative weights.
    """
    return [DominanceVerdictOut.of(v) for v in dominance_for(_require_run(store, run_id))]


@router.get(
    "/runs/{run_id}/recommendation",
    response_model=RecommendedCandidateOut | None,
    summary="FR-16 — the candidate put forward, and the rule that chose it",
)
def recommendation(store: RunStoreDep, run_id: str) -> RecommendedCandidateOut | None:
    """None while a run has produced no candidate yet."""
    result = recommendation_for(_require_run(store, run_id))
    return RecommendedCandidateOut.of(result) if result is not None else None
