"""The four analysis-layer properties (docs/testing-strategy.md, docs/
scoring-and-explanation.md), verified on randomly generated candidates
rather than hand-picked examples - a property holds for every input, an
example holds for one.

No solver: candidates here are synthetic SubScore tuples, exercising
DefaultScorer/DefaultRanker (analysis/scoring.py, analysis/ranking.py)
directly. What a candidate's placements actually were, and whether a given
raw_value/bounds formula is itself correct, is a different question from
whether the scoring/ranking arithmetic is exact and stable - these tests
answer the second question only.
"""

from __future__ import annotations

import math

from hypothesis import given
from hypothesis import strategies as st

from optiedt.analysis.ranking import DefaultRanker
from optiedt.analysis.scoring import DefaultScorer
from optiedt.domain.entities import Candidate, ConstraintCode, SubScore

CODES: tuple[ConstraintCode, ...] = ("S2", "S3", "S4", "S5", "S6", "S7", "S10")

_normalised = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_weight = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


def _candidate(candidate_id: str, normalised_values: tuple[float, ...]) -> Candidate:
    return Candidate(
        id=candidate_id,
        run="run-1",
        profile_name="balanced",
        cost=0,
        score=0.0,
        placements=(),
        sub_scores=tuple(
            SubScore(criterion=code, raw_value=0.0, normalised=value)
            for code, value in zip(CODES, normalised_values, strict=True)
        ),
    )


def _weights(values: tuple[float, ...]) -> dict[ConstraintCode, float]:
    weights = dict(zip(CODES, values, strict=True))
    # At least one positive weight, or every score collapses to 0 and the
    # properties below become vacuous rather than meaningful.
    if sum(weights.values()) <= 0:
        weights[CODES[0]] = 1.0
    return weights


@given(
    a_values=st.tuples(*[_normalised for _ in CODES]),
    b_values=st.tuples(*[_normalised for _ in CODES]),
    weight_values=st.tuples(*[_weight for _ in CODES]),
)
def test_decomposition_is_exact(a_values, b_values, weight_values):
    """The sum of the contributions equals the difference of the two scores,
    to display precision (docs/scoring-and-explanation.md's own qualifier -
    the acceptance criterion promises display precision, not bitwise
    equality)."""
    weights = _weights(weight_values)
    a = _candidate("A", a_values)
    b = _candidate("B", b_values)
    ranker = DefaultRanker(weights=weights)

    decomposition = ranker.decompose(a, b)
    contribution_sum = sum(c.value for c in decomposition.contributions)

    assert math.isclose(contribution_sum, decomposition.score_difference, abs_tol=1e-6)
    assert math.isclose(
        round(contribution_sum, 6), round(decomposition.score_difference, 6), abs_tol=1e-6
    )


@given(
    values=st.lists(
        st.tuples(*[_normalised for _ in CODES]),
        min_size=2,
        max_size=8,
    ),
    weight_values=st.tuples(*[_weight for _ in CODES]),
)
def test_order_is_invariant_to_input_order(values, weight_values):
    """rank() must not depend on the order candidates are read in."""
    weights = _weights(weight_values)
    candidates = [_candidate(f"c{i}", v) for i, v in enumerate(values)]
    ranker = DefaultRanker(weights=weights)

    forward = ranker.rank(list(candidates))
    reversed_order = ranker.rank(list(reversed(candidates)))

    assert [c.id for c in forward] == [c.id for c in reversed_order]


@given(
    base_values=st.tuples(*[_normalised for _ in CODES]),
    weight_values=st.tuples(*[_weight for _ in CODES]),
    code_index=st.integers(min_value=0, max_value=len(CODES) - 1),
    delta=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_reducing_one_violation_never_lowers_the_score(
    base_values, weight_values, code_index, delta
):
    """Monotonicity: improving one criterion (raising its normalised value -
    n_i=1 is the best situation) never lowers the score. Follows from weight
    non-negativity, which is what the increment-2 weight fitting must
    preserve (docs/scoring-and-explanation.md)."""
    improved_value = base_values[code_index] + delta
    if improved_value > 1.0:
        improved_value = 1.0
    if improved_value == base_values[code_index]:
        return  # already at the ceiling; nothing to improve

    improved_values = tuple(
        improved_value if i == code_index else v for i, v in enumerate(base_values)
    )
    weights = _weights(weight_values)
    scorer = DefaultScorer()

    before = scorer.score(_candidate("before", base_values), weights)
    after = scorer.score(_candidate("after", improved_values), weights)

    assert after >= before - 1e-9


@given(
    base_values=st.tuples(
        *[st.floats(min_value=0.0, max_value=0.9, allow_nan=False) for _ in CODES]
    ),
    margin=st.floats(min_value=1e-3, max_value=0.09, allow_nan=False),
    weight_values=st.tuples(*[_weight for _ in CODES]),
)
def test_dominance_is_detected(base_values, margin, weight_values):
    """A candidate strictly improved by another on EVERY criterion is
    signalled as dominated - exact, needs no parameters
    (docs/scoring-and-explanation.md)."""
    dominated_values = base_values
    dominator_values = tuple(v + margin for v in base_values)
    weights = _weights(weight_values)

    dominated = _candidate("dominated", dominated_values)
    dominator = _candidate("dominator", dominator_values)
    ranker = DefaultRanker(weights=weights)

    verdicts = {v.candidate: v.dominated_by for v in ranker.dominance([dominated, dominator])}

    assert verdicts["dominated"] == "dominator"


@given(
    weight_values=st.tuples(*[_weight for _ in CODES]),
)
def test_incomparable_candidates_are_not_flagged_dominated(weight_values):
    """Two candidates that each win on at least one criterion and lose on at
    least one other must not be reported as dominating one another - most
    candidates are like this (docs/scoring-and-explanation.md: "most
    candidates win on one criterion and lose on another")."""
    a_values = (1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
    b_values = (0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0)
    weights = _weights(weight_values)

    a = _candidate("A", a_values)
    b = _candidate("B", b_values)
    ranker = DefaultRanker(weights=weights)

    verdicts = {v.candidate: v.dominated_by for v in ranker.dominance([a, b])}

    assert verdicts["A"] is None
    assert verdicts["B"] is None
