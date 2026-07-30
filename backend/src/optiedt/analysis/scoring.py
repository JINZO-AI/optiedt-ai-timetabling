"""Scorer implementation and the glue from raw placements to a scored Candidate.

score(k) = 100 * sum(w_i * n_i(k)) - docs/scoring-and-explanation.md. Linear by
construction: no product term, no threshold, no max is introduced anywhere
below, because that identity is what makes the decomposition in ranking.py
exact.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from optiedt.analysis.interfaces import Bounds, Criterion, Scorer
from optiedt.domain.entities import (
    Candidate,
    CandidateId,
    ConstraintCode,
    Placement,
    RunId,
    SubScore,
)
from optiedt.domain.instance import Instance


def normalise(value: float, bounds: Bounds) -> float:
    """n_i(k) = 1 - (v_i(k) - min_i) / (max_i - min_i), with n_i = 1 when
    max_i == min_i (docs/scoring-and-explanation.md: not hypothetical - a
    criterion with no violations anywhere, or a zero-weight criterion, can
    reach it)."""
    if bounds.maximum == bounds.minimum:
        return 1.0
    return 1.0 - (value - bounds.minimum) / (bounds.maximum - bounds.minimum)


def renormalised(weights: dict[ConstraintCode, float]) -> dict[ConstraintCode, float]:
    """Weights renormalised to sum to 1, which is what makes two runs'
    scores comparable (docs/scoring-and-explanation.md).

    Rejects negative weights rather than normalising them. Monotonicity -
    "reducing violations of one criterion never lowers the score" - follows
    from weight non-negativity and nothing else, so a negative weight does not
    merely skew the ranking, it breaks a property the analysis layer is
    property-tested on and the increment-2 weight fitting is required to
    preserve. Failing loudly here is the only place that can catch it before
    it becomes an inexplicable order.

    An all-zero weight vector is returned unchanged (every score becomes 0);
    that is degenerate but not incoherent, and it is what a profile that
    switches every criterion off actually means.
    """
    negative = sorted(code for code, w in weights.items() if w < 0)
    if negative:
        raise ValueError(
            f"negative weight(s) for {', '.join(negative)}: weights must be non-negative "
            "(docs/scoring-and-explanation.md). A negative weight would reward the "
            "violation it is meant to penalise, and breaks monotonicity."
        )
    total = sum(weights.values())
    if total <= 0:
        return dict(weights)
    return {code: w / total for code, w in weights.items()}


@dataclass(frozen=True, slots=True)
class DefaultScorer:
    """score(candidate, weights) = 100 * sum(w_i * candidate's own n_i).

    ``weights`` is a call-time argument, not read off the candidate, on
    purpose: every candidate in a run is compared under the SAME weights in
    force for scoring, regardless of which weight profile's objective steered
    the solver toward that candidate's placements (profile_name is kept only
    as provenance). See ranking.py's module docstring.
    """

    def score(self, candidate: Candidate, weights: dict[ConstraintCode, float]) -> float:
        weights_normalised = renormalised(weights)
        by_code = {s.criterion: s.normalised for s in candidate.sub_scores}
        return 100.0 * sum(w * by_code.get(code, 0.0) for code, w in weights_normalised.items())


def evaluate_candidate(
    *,
    candidate_id: CandidateId,
    run: RunId,
    profile_name: str,
    placements: tuple[Placement, ...],
    cost: int,
    criteria: Sequence[Criterion],
    instance: Instance,
    weights: dict[ConstraintCode, float],
    scorer: Scorer | None = None,
) -> Candidate:
    """Turn a solver's raw placements into an immutable, scored Candidate.

    ``criteria`` and their bounds are instance-derived and stable for every
    candidate of a run (ADR-009) - build them once with
    ``analysis.criteria.build_criteria`` and reuse across candidates rather
    than reconstructing per call.
    """
    unscored = Candidate(
        id=candidate_id,
        run=run,
        profile_name=profile_name,
        cost=cost,
        score=0.0,
        placements=placements,
        sub_scores=(),
    )
    sub_scores = []
    for criterion in criteria:
        value = criterion.raw_value(unscored)
        sub_scores.append(
            SubScore(
                criterion=criterion.code,
                raw_value=value,
                normalised=normalise(value, criterion.bounds(instance)),
            )
        )
    scored = replace(unscored, sub_scores=tuple(sub_scores))
    active_scorer = scorer or DefaultScorer()
    return replace(scored, score=active_scorer.score(scored, weights))
