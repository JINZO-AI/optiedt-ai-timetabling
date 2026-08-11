"""FR-6 — order the candidates by score.

    Acceptance criterion — **SRS §6.7, quoted verbatim**, located through SRS
    Table 36 which maps FR-6 → §6.7 "Order by decreasing score":

    "The candidates are ordered by decreasing score. Equal scores are separated
    by the criteria taken in the order of their weights."

⚠️ **This criterion is the supervisor's own words**, unlike FR-10's and FR-18's
in this same directory, which are labelled project decisions. It is the
strongest source class the project has — Table 36 names the section explicitly,
which is more than the §3.2 rows Phase 10 closed four requirements against.
`docs/testing-strategy.md` §4 keeps the three classes in separate tables so a
reader can tell which is which.

⚠️ **Two sentences, and the second is the one that is easy to leave untested.**
Any implementation gets "decreasing score" right by accident; the tie-break is
where a wrong order hides, because on the reference instance ties do not occur
and the path is never exercised. So the tie-break is tested against
**constructed** candidates whose scores are equal by construction, through the
same `DefaultRanker` the API uses.

⚠️ **Rank order is DATA, not presentation.** `frontend/src/types/domain.ts`
says "in rank order, best first - display this order, do not sort", and
`db/models.py` carries `Candidate.rank_order` so the order survives a restart.
A test that sorted the response before checking it would be verifying its own
sort.
"""

from __future__ import annotations

import pytest

from optiedt.analysis.ranking import TIE_BREAK_ORDER, DefaultRanker
from optiedt.analysis.scoring import DefaultScorer
from optiedt.domain.entities import Candidate, SubScore

pytestmark = pytest.mark.acceptance

SOFT_CODES = ("S2", "S3", "S4", "S5", "S6", "S7", "S10")


def test_the_candidates_come_back_in_decreasing_score(application) -> None:
    """The first sentence, through the path a user takes.

    Read from `GET /runs/{id}` exactly as the generation screen reads it, and
    **not sorted here** — the order asserted is the order served.
    """
    run = application.launch()
    assert run["state"] == "COMPLETED", run["error"]

    scores = [c["score"] for c in run["candidates"]]

    assert len(scores) >= 2, "an ordering claim needs at least two candidates"
    assert scores == sorted(scores, reverse=True)


def test_the_dedicated_candidates_endpoint_serves_the_same_order(application) -> None:
    """`GET /runs/{id}/candidates` is what the timetable screen reads.

    Two endpoints serving one run must not disagree about which candidate is
    first — a reader comparing two screens would have no way to tell which was
    right.
    """
    run = application.launch()
    listed = application.client.get(f"/api/runs/{run['id']}/candidates")

    assert listed.status_code == 200, listed.text
    assert [c["id"] for c in listed.json()] == [c["id"] for c in run["candidates"]]


def test_the_recommended_candidate_is_the_first_of_that_order(application) -> None:
    """FR-16 selects "the first"; this checks the two agree about which it is.

    Not a duplicate of `test_fr16`: that verifies the recommendation names a
    rule and a candidate, this verifies the ORDER it selects from is the one
    the user was shown.
    """
    run = application.launch()
    recommended = application.client.get(f"/api/runs/{run['id']}/recommendation")

    assert recommended.status_code == 200, recommended.text
    assert recommended.json()["candidate"] == run["candidates"][0]["id"]


# ── The second sentence: equal scores, separated by weight order ────────


def _candidate(cid: str, normalised: dict[str, float]) -> Candidate:
    """A candidate whose sub-scores are stated directly.

    Constructed rather than solved: two candidates with *exactly* equal scores
    do not arise on the reference instance, so the tie-break path would never
    be reached by a run. An untested branch that only executes on a tie is a
    branch that first executes in front of a department.
    """
    return Candidate(
        id=cid,
        run="r1",
        profile_name="balanced",
        cost=0,
        score=0.0,
        placements=(),
        sub_scores=tuple(
            SubScore(criterion=code, raw_value=0.0, normalised=normalised[code])
            for code in SOFT_CODES
        ),
    )


def test_equal_scores_are_separated_by_the_criteria_in_weight_order() -> None:
    """**The second sentence, and the whole reason this file exists.**

    Two candidates with **bit-identical** scores: equal weights on S3 and S6,
    and the two values swapped between them, so the weighted sums are the same
    float. They then differ on S3, which precedes S6 in the tie-break order, so
    the candidate better on S3 must come first.

    ⚠️ **The tie has to be exact, and constructing one is not a formality.**
    Two candidates that are equal *in decimal arithmetic* are usually NOT equal
    as floats — measured, on the first draft of this test: weights 0.4/0.2 and
    values chosen to cancel give 49.99999999999999 against 50.0, a difference
    of 7.1e-15, and the score comparison then decides before the tie-break is
    ever consulted. See the boundary test below, which records that behaviour
    rather than hiding it.

    ⚠️ **Whose weights order the criteria is genuinely ambiguous in §6.7**, and
    the run's weights are equal here, so the applicable order is the documented
    one: `TIE_BREAK_ORDER`, the catalogue default weights descending, ties among
    equal defaults broken by code. That is a fixed, total order — the run's own
    vector could not supply one, since a profile may give several criteria the
    same weight or zero. Recorded as a reading, not asserted as the only one.
    """
    weights = {"S2": 0.0, "S3": 0.25, "S4": 0.0, "S5": 0.0, "S6": 0.25, "S7": 0.0, "S10": 0.0}
    flat = dict.fromkeys(SOFT_CODES, 0.5)

    # ⚠️ **The ids are chosen so that alphabetical order CONTRADICTS the
    # expected one**, and that is not decoration. `rank()` pre-sorts by id for
    # a total order, so with ids in the "natural" order this test passed even
    # with the tie-break deleted from the sort key — the id sort supplied the
    # same answer by accident. Found by mutation, not by review.
    better_on_s3 = _candidate("z-better-on-s3", {**flat, "S3": 0.6, "S6": 0.3})
    better_on_s6 = _candidate("a-better-on-s6", {**flat, "S3": 0.3, "S6": 0.6})

    scorer = DefaultScorer()
    assert scorer.score(better_on_s3, weights) == scorer.score(better_on_s6, weights), (
        "the scores must be bit-identical, or this tests the first sentence again"
    )
    assert TIE_BREAK_ORDER.index("S3") < TIE_BREAK_ORDER.index("S6")

    ranked = DefaultRanker(weights=weights).rank([better_on_s6, better_on_s3])

    assert [c.id for c in ranked] == ["z-better-on-s3", "a-better-on-s6"]


def test_the_tie_break_does_not_depend_on_the_order_given() -> None:
    """A ranking that depended on input order would be a ranking of nothing.

    `docs/scoring-and-explanation.md` §Ordering states this as a property in its
    own right: "The order must not depend on the order in which candidates are
    read — this is a tested property, not an assumption."
    """
    weights = {"S2": 0.0, "S3": 0.25, "S4": 0.0, "S5": 0.0, "S6": 0.25, "S7": 0.0, "S10": 0.0}
    flat = dict.fromkeys(SOFT_CODES, 0.5)
    better_on_s3 = _candidate("z-better-on-s3", {**flat, "S3": 0.6, "S6": 0.3})
    better_on_s6 = _candidate("a-better-on-s6", {**flat, "S3": 0.3, "S6": 0.6})
    ranker = DefaultRanker(weights=weights)

    one_way = [c.id for c in ranker.rank([better_on_s6, better_on_s3])]
    other_way = [c.id for c in ranker.rank([better_on_s3, better_on_s6])]

    assert one_way == other_way == ["z-better-on-s3", "a-better-on-s6"]


def test_the_tie_break_falls_through_every_criterion_before_giving_up() -> None:
    """Including S10, which carries weight 0 and is still consulted.

    ⚠️ Not a curiosity: C-14 records that ties on the zero-weight criterion are
    "ordinary rather than rare", and that a rule which skipped it was silent
    exactly where it mattered. Two candidates identical on the six weighted
    criteria must still be separated, and by S10.
    """
    weights = {"S2": 0.25, "S3": 0.25, "S4": 0.0, "S5": 0.0, "S6": 0.0, "S7": 0.0, "S10": 0.0}
    flat = dict.fromkeys(SOFT_CODES, 0.5)
    # Ids again ordered against the expectation - see the note above.
    better = _candidate("z-better-on-s10", {**flat, "S10": 0.9})
    worse = _candidate("a-worse-on-s10", {**flat, "S10": 0.1})

    scorer = DefaultScorer()
    assert scorer.score(better, weights) == scorer.score(worse, weights)

    ranked = DefaultRanker(weights=weights).rank([worse, better])

    assert [c.id for c in ranked] == ["z-better-on-s10", "a-worse-on-s10"]


def test_scores_differing_only_by_floating_point_noise_are_not_treated_as_equal() -> None:
    """⚠️ **A documented limit of the implementation, recorded rather than fixed.**

    Two candidates equal under decimal arithmetic can differ as floats — here by
    **7.1e-15** — and the score comparison then decides before §6.7's tie-break
    is reached. The department sees two identical printed scores ordered by a
    difference in the 15th decimal, which it cannot reproduce by hand.

    **Three fixes were considered and all three were rejected. Measured, not
    assumed:**

    - **Exact/rational arithmetic** — REFUTED by measurement. Computing the
      score with `fractions.Fraction` still gives
      `675539944105574375/13510798882111488` against `50`: the inexactness is in
      the *inputs* (the floats 0.4, 0.2 and 0.6, for which `0.4 + 0.2 != 0.6`),
      not in the arithmetic, so no amount of precision creates the tie.
    - **A tolerance or a rounded sort key** — rejected as an **invented
      requirement**. §6.7 says "equal scores"; it says nothing about scores that
      *print* the same. Choosing a quantum would be choosing an arbitrary
      threshold the specification does not state.
    - **Comparing the underlying criterion values instead of the score** —
      rejected: that is what the tie-break already does, *after* the score
      comparison, which is the order §6.7 itself prescribes.

    **What is asserted here is the behaviour as it is**, so that a future change
    to it is a deliberate act and not an accident. ⚠️ **Revisit this if a real
    portfolio ever produces two candidates whose displayed scores are equal** —
    it has not on the reference instance, where the three differ by more than a
    point.
    """
    weights = {"S2": 0.0, "S3": 0.4, "S4": 0.0, "S5": 0.0, "S6": 0.2, "S7": 0.0, "S10": 0.0}
    flat = dict.fromkeys(SOFT_CODES, 0.5)
    a = _candidate("a", {**flat, "S3": 0.6, "S6": 0.3})
    b = _candidate("b", {**flat, "S3": 0.5, "S6": 0.5})

    scorer = DefaultScorer()
    difference = abs(scorer.score(a, weights) - scorer.score(b, weights))

    assert 0 < difference < 1e-12, "equal in decimal, unequal as floats"
    assert f"{scorer.score(a, weights):.2f}" == f"{scorer.score(b, weights):.2f}", (
        "and identical once printed, which is what a reader sees"
    )
    # The higher float wins on score; the tie-break is never consulted.
    assert [c.id for c in DefaultRanker(weights=weights).rank([a, b])] == ["b", "a"]


def test_candidates_alike_in_every_scored_respect_still_have_one_fixed_order() -> None:
    """⚠️ **The last resort of the ordering, and the only thing that makes it
    total.**

    Two candidates equal on score AND on every one of the seven tie-break
    criteria are separated by nothing the specification names — so `rank()`
    falls back to the id. Without that fallback the answer would depend on the
    order the candidates arrived in, and
    `docs/scoring-and-explanation.md` §Ordering states the opposite as a
    property: "The order must not depend on the order in which candidates are
    read."

    ⚠️ This is the assertion the three tests above CANNOT make, because each of
    them is separated by the tie-break before the fallback is reached. Mutation
    testing is what showed that: deleting the id pre-sort left all of them
    green.
    """
    weights = {"S2": 0.5, "S3": 0.5, "S4": 0.0, "S5": 0.0, "S6": 0.0, "S7": 0.0, "S10": 0.0}
    identical = dict.fromkeys(SOFT_CODES, 0.5)
    first = _candidate("a-twin", identical)
    second = _candidate("z-twin", identical)
    ranker = DefaultRanker(weights=weights)

    assert DefaultScorer().score(first, weights) == DefaultScorer().score(second, weights)

    assert [c.id for c in ranker.rank([second, first])] == ["a-twin", "z-twin"]
    assert [c.id for c in ranker.rank([first, second])] == ["a-twin", "z-twin"]
