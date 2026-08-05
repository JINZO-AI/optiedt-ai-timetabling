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

import pytest
from hypothesis import given
from hypothesis import strategies as st

from optiedt.analysis.interfaces import Bounds
from optiedt.analysis.ranking import DefaultRanker
from optiedt.analysis.scoring import DefaultScorer, normalise
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
    raw=st.floats(min_value=0.0, max_value=500.0, allow_nan=False),
    improvement=st.floats(min_value=1e-3, max_value=500.0, allow_nan=False),
    maximum=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False),
    weight_values=st.tuples(*[_weight for _ in CODES]),
    code_index=st.integers(min_value=0, max_value=len(CODES) - 1),
)
def test_reducing_a_raw_violation_count_never_lowers_the_score(
    raw, improvement, maximum, weight_values, code_index
):
    """Monotonicity as the specification actually states it: "reducing
    VIOLATIONS of one criterion never lowers the score".

    test_reducing_one_violation_never_lowers_the_score above only covers
    normalised -> score, which is monotone by inspection given non-negative
    weights. The claim that matters spans raw_value -> normalise -> score, and
    it is normalise() that carries the sign flip (n_i = 1 - ...) that makes
    "fewer violations" mean "higher score". Get that inversion backwards and
    the application would rank the worst timetable first while every other
    property test stayed green.
    """
    bounds = Bounds(minimum=0.0, maximum=maximum)
    better_raw = max(0.0, raw - improvement)
    weights = _weights(weight_values)
    scorer = DefaultScorer()

    def score_for(value: float) -> float:
        normalised = normalise(value, bounds)
        values = tuple(normalised if i == code_index else 0.5 for i in range(len(CODES)))
        return scorer.score(_candidate("k", values), weights)

    assert score_for(better_raw) >= score_for(raw) - 1e-9


@given(
    values=st.tuples(*[_normalised for _ in CODES]),
    weight_values=st.tuples(*[_weight for _ in CODES]),
)
def test_a_candidate_tied_on_one_criterion_is_reported_dominated(values, weight_values):
    """Pins the PARETO reading adopted 2026-08-05 (C-14): at least as good on
    every criterion, strictly better on at least one.

    ⚠️ This test asserted the OPPOSITE until that date, under the strict
    reading docs/scoring-and-explanation.md then carried ("improves on every
    criterion"), and it existed to stop anyone "fixing" the ``>`` to ``>=`` by
    accident. The reading was changed deliberately, so the test is inverted
    rather than deleted - the case it covers is exactly the one that decided
    C-14. S10 carries weight 0, nothing optimises for it, so a candidate beaten
    on all six WEIGHTED criteria and tied on the seventh is ordinary, and the
    strict rule called it not dominated - silent precisely where the signal
    exists to speak.

    The reading is a specification decision, not a keyboard one: see
    ranking.py's dominance docstring and C-14 in docs/open-questions.md before
    changing it back.
    """
    weights = _weights(weight_values)
    worse = _candidate("worse", values)
    # Strictly better everywhere except the last criterion, where it ties.
    better_values = tuple(
        v if i == len(CODES) - 1 else min(1.0, v + 0.5) for i, v in enumerate(values)
    )
    if better_values == values:
        return  # every criterion already at the ceiling; nothing improved
    better = _candidate("better", better_values)
    ranker = DefaultRanker(weights=weights)

    verdicts = {v.candidate: v.dominated_by for v in ranker.dominance([worse, better])}
    assert verdicts["worse"] == "better"
    assert verdicts["better"] is None


@given(
    values=st.tuples(*[_normalised for _ in CODES]),
    weight_values=st.tuples(*[_weight for _ in CODES]),
)
def test_two_candidates_equal_on_every_criterion_dominate_neither(values, weight_values):
    """The edge the Pareto rule introduces and the strict rule could not reach.

    Under ">= everywhere" alone, two identical candidates would each dominate
    the other, and the report would name a compromise where there is only a
    duplicate. The second clause - strictly better on at least one - is what
    refuses, and it must be tested as a property because it is the whole
    difference between Pareto and "no worse anywhere".

    Not hypothetical: services/portfolio.py removes duplicate TIMETABLES, but
    two different timetables can score identically on all seven criteria.
    """
    weights = _weights(weight_values)
    a = _candidate("A", values)
    b = _candidate("B", values)
    ranker = DefaultRanker(weights=weights)

    verdicts = {v.candidate: v.dominated_by for v in ranker.dominance([a, b])}

    assert verdicts["A"] is None
    assert verdicts["B"] is None


@given(weight_values=st.tuples(*[_weight for _ in CODES]))
def test_a_candidate_with_no_sub_scores_is_never_dominated(weight_values):
    """``all()`` over an empty criterion set is vacuously true, so a candidate
    carrying no sub-scores would otherwise be reported as dominated by an
    arbitrary other candidate on no evidence whatsoever.

    Under the strict reading this needed an explicit guard in
    ``DefaultRanker.dominance``. Under Pareto (C-14) it falls out of the rule -
    ``any()`` over the same empty set is False, so the second clause refuses -
    and the guard was removed as dead code. This test is what keeps the
    behaviour pinned now that no line of source states it."""
    weights = _weights(weight_values)
    empty = Candidate(
        id="empty",
        run="run-1",
        profile_name="balanced",
        cost=0,
        score=0.0,
        placements=(),
        sub_scores=(),
    )
    other = _candidate("other", (0.5,) * len(CODES))
    ranker = DefaultRanker(weights=weights)

    verdicts = {v.candidate: v.dominated_by for v in ranker.dominance([empty, other])}
    assert verdicts["empty"] is None


@given(
    base_values=st.tuples(
        *[st.floats(min_value=0.0, max_value=0.8, allow_nan=False) for _ in CODES]
    ),
    margin=st.floats(min_value=1e-3, max_value=0.19, allow_nan=False),
    weight_values=st.tuples(*[_weight for _ in CODES]),
)
def test_a_dominated_candidate_is_never_recommended(base_values, margin, weight_values):
    """FR-16's third sentence describes an unreachable state, and this is the
    universal form of that claim.

    The specification said "a dominated top candidate is signalled alongside" -
    but under a linear weighted sum with non-negative weights a dominated
    candidate cannot BE the top candidate:

        score(B) - score(A) = 100 * sum( w_i * (n_i(B) - n_i(A)) )

    with every term non-negative when B dominates A. Under the strict reading
    at least one weight was positive and one gain strict, so score(B) >
    score(A) outright. ⚠️ Under PARETO (C-14) the sum can be exactly zero -
    when the only strict gain falls on the zero-weight S10 - and the claim
    still holds, because TIE_BREAK_ORDER covers all seven criteria and resolves
    the tie in B's favour. **Adopting Pareto did not revive this field**, and
    that was checked rather than assumed.

    The signal is therefore still dead code. It is kept because the
    specification names it and because a non-linear score or a negative weight
    would revive it - but it must be dead provably, not by accident. Tested as
    a property rather than an example because the claim is universal over
    weights and sub-scores.
    """
    dominated_values = base_values
    dominator_values = tuple(min(1.0, v + margin) for v in base_values)
    if dominator_values == dominated_values:
        return  # margin vanished at the ceiling; nothing dominates anything

    weights = _weights(weight_values)
    ranker = DefaultRanker(weights=weights)
    dominated = _candidate("dominated", dominated_values)
    dominator = _candidate("dominator", dominator_values)

    recommendation = ranker.recommend([dominated, dominator])

    assert recommendation is not None
    assert recommendation.dominated_by is None, (
        "a dominated candidate was recommended - either the weights went "
        "negative or the score stopped being a linear weighted sum"
    )


@given(weight_values=st.tuples(*[_weight for _ in CODES]))
def test_a_negative_weight_is_refused_rather_than_ranked_on(weight_values):
    """Monotonicity follows from weight non-negativity and nothing else, so a
    negative weight does not merely skew the order - it breaks a property the
    department is told holds. It must fail loudly, not silently invert."""
    weights = {**_weights(weight_values), CODES[0]: -0.1}
    with pytest.raises(ValueError, match="non-negative"):
        DefaultScorer().score(_candidate("k", (0.5,) * len(CODES)), weights)


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
