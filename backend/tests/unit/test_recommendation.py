"""FR-16 - the recommendation rule.

docs/scoring-and-explanation.md states it in three sentences: the
recommendation designates the candidate of highest score, states the rule
that produced it, and signals a dominated top candidate alongside. "That is
the entire rule."

Two things are checked here with roughly equal weight: that the right
candidate is named, and that nothing MORE than the stated rule crept in - no
tie-break of its own, no score floor, no quiet substitution of the runner-up.
An unstated rule is the failure mode, because the whole value of FR-16 is
that the department can check the sentence.

⚠️ One of the three sentences describes a state that cannot occur. See
test_a_dominated_candidate_can_never_rank_first - the proof is short and it
is why Recommendation.dominated_by is always None. Recorded under C-14 in
docs/open-questions.md rather than resolved here.
"""

from __future__ import annotations

import pytest

from optiedt.analysis.ranking import RECOMMENDATION_RULE, DefaultRanker
from optiedt.domain.entities import Candidate, ConstraintCode, SubScore

CODES: tuple[ConstraintCode, ...] = ("S2", "S3", "S4", "S5", "S6", "S7", "S10")
WEIGHTS: dict[ConstraintCode, float] = {
    "S2": 0.25,
    "S3": 0.15,
    "S4": 0.10,
    "S5": 0.20,
    "S6": 0.10,
    "S7": 0.10,
    "S10": 0.0,
}


def _candidate(candidate_id: str, *normalised: float) -> Candidate:
    return Candidate(
        id=candidate_id,
        run="run-1",
        profile_name="balanced",
        cost=0,
        score=0.0,
        placements=(),
        sub_scores=tuple(
            SubScore(criterion=code, raw_value=0.0, normalised=value)
            for code, value in zip(CODES, normalised, strict=True)
        ),
    )


def _uniform(candidate_id: str, value: float) -> Candidate:
    return _candidate(candidate_id, *([value] * len(CODES)))


@pytest.fixture
def ranker() -> DefaultRanker:
    return DefaultRanker(weights=WEIGHTS)


def test_the_highest_scoring_candidate_is_recommended(ranker):
    recommendation = ranker.recommend(
        [_uniform("low", 0.2), _uniform("high", 0.9), _uniform("middle", 0.5)]
    )

    assert recommendation is not None
    assert recommendation.candidate == "high"


def test_the_rule_is_stated_and_is_the_documented_one(ranker):
    """The sentence is the deliverable, not a decoration: FR-16 exists so the
    department can check "recommended because it has the highest score under
    the weights in force"."""
    recommendation = ranker.recommend([_uniform("a", 0.5), _uniform("b", 0.7)])

    assert recommendation is not None
    assert recommendation.rule == RECOMMENDATION_RULE
    assert recommendation.rule == "highest score under the weights in force"


def test_the_reported_score_is_the_recommended_candidates_own_score(ranker):
    """Recomputable by hand from the sub-scores and weights recorded with the
    run - the property the whole scoring design exists to preserve."""
    top = _uniform("top", 0.8)
    recommendation = ranker.recommend([_uniform("other", 0.3), top])

    assert recommendation is not None
    assert recommendation.score == pytest.approx(ranker.scorer.score(top, WEIGHTS))


def test_an_empty_portfolio_yields_no_recommendation(ranker):
    """An infeasible run reaches here with no candidates (see
    services/portfolio.py). Recommending nothing in particular would be worse
    than recommending nothing."""
    assert ranker.recommend([]) is None


def test_a_single_candidate_is_recommended_and_is_not_dominated(ranker):
    recommendation = ranker.recommend([_uniform("only", 0.4)])

    assert recommendation is not None
    assert recommendation.candidate == "only"
    assert recommendation.dominated_by is None


def test_a_dominated_candidate_can_never_rank_first(ranker):
    """The proof behind the point above, as an executable statement.

    If B dominates A then n_i(B) > n_i(A) for EVERY criterion, so

        score(B) - score(A) = 100 * sum( w_i * (n_i(B) - n_i(A)) )

    is a sum of non-negative terms, and renormalised weights sum to 1 so at
    least one weight is positive. Hence score(B) > score(A) strictly, and A
    cannot be top-ranked. Non-negativity of the weights is what makes this
    hold - which is exactly why analysis/scoring.py refuses a negative one.
    """
    dominated = _candidate("dominated", 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70)
    dominator = _candidate("dominator", 0.11, 0.21, 0.31, 0.41, 0.51, 0.61, 0.71)

    verdicts = {v.candidate: v.dominated_by for v in ranker.dominance([dominated, dominator])}
    assert verdicts["dominated"] == "dominator", "the fixture must actually be dominated"

    assert ranker.rank([dominated, dominator])[0].id == "dominator"


def test_the_recommendation_is_therefore_never_flagged_dominated(ranker):
    """Consequence of the proof above: Recommendation.dominated_by is
    unreachable under a linear weighted sum with non-negative weights.

    The field is kept rather than deleted because
    docs/scoring-and-explanation.md requires the signal, and because a change
    to the dominance rule (C-14) or to the scoring function would make it
    reachable again. It is dead today, and it must be dead for a reason
    someone can check - not quietly absent.
    """
    dominated = _candidate("dominated", 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70)
    dominator = _candidate("dominator", 0.11, 0.21, 0.31, 0.41, 0.51, 0.61, 0.71)

    recommendation = ranker.recommend([dominated, dominator])

    assert recommendation is not None
    assert recommendation.candidate == "dominator"
    assert recommendation.dominated_by is None


def test_dominance_still_reports_non_top_candidates(ranker):
    """The dominance test is not dead in general - only the "top candidate is
    dominated" case is unreachable. A dominated runner-up is ordinary, and
    the comparison screen can still say so."""
    best = _candidate("best", 0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 0.90)
    middling = _candidate("middling", 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50)

    verdicts = {v.candidate: v.dominated_by for v in ranker.dominance([best, middling])}

    assert verdicts["middling"] == "best"
    assert verdicts["best"] is None


def test_the_recommendation_agrees_with_the_head_of_the_ranking(ranker):
    """A recommendation naming a candidate the displayed list did not show
    first would be indefensible however correct its arithmetic."""
    candidates = [_uniform("a", 0.3), _uniform("b", 0.8), _uniform("c", 0.55)]

    recommendation = ranker.recommend(candidates)

    assert recommendation is not None
    assert recommendation.candidate == ranker.rank(candidates)[0].id


def test_the_recommendation_does_not_depend_on_input_order(ranker):
    """FR-19 requires two runs on the same data to agree; a recommendation
    that flipped with read order would break that without touching a
    placement."""
    candidates = [_uniform("a", 0.5), _uniform("b", 0.5), _uniform("c", 0.5)]

    forward = ranker.recommend(list(candidates))
    backward = ranker.recommend(list(reversed(candidates)))

    assert forward is not None and backward is not None
    assert forward.candidate == backward.candidate


def test_tied_candidates_are_separated_by_the_ranking_tie_break_not_a_new_rule(ranker):
    """FR-16 states no tie-break of its own - "that is the entire rule" - so a
    tie must resolve exactly as rank() resolves it, never by a second policy
    invented inside recommend()."""
    tied_a = _candidate("alpha", 0.5, 0.9, 0.5, 0.5, 0.5, 0.5, 0.5)
    tied_b = _candidate("beta", 0.5, 0.9, 0.5, 0.5, 0.5, 0.5, 0.5)

    recommendation = ranker.recommend([tied_a, tied_b])

    assert recommendation is not None
    assert recommendation.candidate == ranker.rank([tied_a, tied_b])[0].id
