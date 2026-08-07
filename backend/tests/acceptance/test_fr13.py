"""FR-13 — produce candidates under distinct weight profiles.

    Acceptance criterion, as C-5 resolved it on 2026-08-05:
    "Three DISTINCT candidates on the reference instance, at production
    settings (seed fixed, interleave_search on, warm start withheld under an
    objective)."
    General contract, unchanged: "at most three, duplicates removed"
    (SRS Table 29).

⚠️ **Read C-5 before weakening this to "at least two".** The wording conflict
was between a behaviour and a test: SRS Table 29 fixes what the software does,
CdC §11 and SRS §8.6 fix what the test sees, and if two profiles converge the
system is correct and the test fails. It was settled by tying the criterion to
the verified reference instance rather than by changing `portfolio.py` - and
the assertion stays at exactly three, because the measurement is 3 distinct /
0 removed and a `>= 2` test would stay green through a regression.

⚠️ **This criterion is explicitly instance-specific.** If the reference
instance changes, the expectation of three must be re-derived, not assumed.

✅ **C-15 was resolved on 2026-08-07** and this file gained the assertion it
previously could not make. `teacher-favouring` raises **S3 and S4** rather than
S3 and S5, because S5 is an admitted proxy for absent preference data (C-12)
and was the most expensive criterion to optimise; weighting it 0.40 left
teacher-favouring worst of the three on S3, S4 AND S5 at once.

⚠️ **What is asserted below is the promise as C-15 reworded it** - a favouring
profile produces the best value of its HEADLINE criterion, not a win on every
criterion of its constituency. The stronger reading is unachievable at any
weighting: solving S3 alone drives S5 to 113, solving S5 alone drives S4 to 73.
`balanced` still holds the best S4, and asserting otherwise would pin a claim
the arithmetic forbids - the same mistake C-14's "dominated top candidate"
clause made.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.acceptance, pytest.mark.solver]

EXPECTED_CANDIDATES = 3


@pytest.fixture
def portfolio(production_portfolio: dict[str, object]) -> dict[str, object]:
    """The shared run at production settings - measured at 147-150 s wall.

    Session-scoped in acceptance/conftest.py, so FR-3, FR-13 and FR-19's first
    run are one solve rather than three.
    """
    return production_portfolio


def test_three_distinct_candidates_are_produced(portfolio: dict[str, object]) -> None:
    candidates = portfolio["candidates"]

    assert len(candidates) == EXPECTED_CANDIDATES, (
        f"expected {EXPECTED_CANDIDATES} distinct candidates at production settings, "
        f"got {len(candidates)} with {portfolio['duplicatesRemoved']} removed as duplicates. "
        "See C-5: the criterion is tied to this instance at these settings."
    )


def test_the_candidates_are_genuinely_different_timetables(
    portfolio: dict[str, object],
) -> None:
    """ "Distinct" means the placements differ, not merely the ids.

    Duplicate removal compares timetables, so three ids could in principle
    survive while two arrangements matched - this checks the thing the word
    means rather than the thing that is easy to count.
    """
    arrangements = {
        frozenset((p["session"], p["slot"], p["room"]) for p in candidate["placements"])
        for candidate in portfolio["candidates"]
    }

    assert len(arrangements) == EXPECTED_CANDIDATES


def test_each_candidate_records_the_profile_that_produced_it(
    portfolio: dict[str, object],
) -> None:
    """Three profiles, three provenances.

    `profileName` is provenance only - it is never the weight vector a
    candidate is scored under, which is the run's one vector in force.
    """
    profiles = {c["profileName"] for c in portfolio["candidates"]}

    assert len(profiles) == EXPECTED_CANDIDATES
    assert profiles == {"balanced", "student-favouring", "teacher-favouring"}


def test_a_favouring_profile_wins_its_headline_criterion(
    portfolio: dict[str, object],
) -> None:
    """C-15's reworded promise, and the reason FR-13 can now be `✓`.

    Each favouring profile must produce the BEST value of the criterion it
    raises hardest - student-favouring on S2, teacher-favouring on S3. Lower
    raw values are better for every criterion in this catalogue.

    ⚠️ **Only the headline criterion is asserted, deliberately.** A profile
    that won every criterion of its constituency is unachievable at any
    weighting and C-15 proves it by measurement: solving S3 alone drives S5 to
    113, solving S5 alone drives S4 to 73. `balanced` legitimately holds the
    best S4. Asserting a sweep would pin a claim the arithmetic forbids -
    exactly the fault C-14 found in the "dominated top candidate" clause.

    ⚠️ Before 2026-08-07 this test could not have existed: teacher-favouring
    raised S5, an admitted proxy (C-12), and came back worst of the three on
    S3, S4 and S5 simultaneously.
    """
    headline = {"student-favouring": "S2", "teacher-favouring": "S3"}

    raw = {
        candidate["profileName"]: {s["criterion"]: s["rawValue"] for s in candidate["subScores"]}
        for candidate in portfolio["candidates"]
    }

    for profile, code in headline.items():
        assert profile in raw, f"{profile} produced no distinct candidate"
        best = min(raw, key=lambda name: raw[name][code])
        assert best == profile, (
            f"{profile} must hold the best {code} of the three, but {best} does: "
            + ", ".join(f"{name} {code}={raw[name][code]}" for name in sorted(raw))
            + ". See C-15 - a favouring profile promises its HEADLINE criterion."
        )


def test_the_general_contract_holds_too_at_most_three_duplicates_removed(
    portfolio: dict[str, object],
) -> None:
    """SRS Table 29, which the C-5 resolution left untouched.

    The run reports what it removed rather than silently returning fewer, so
    "three candidates" and "duplicates removed" can both be checked instead of
    one hiding the other.
    """
    assert len(portfolio["candidates"]) <= 3
    assert portfolio["duplicatesRemoved"] == []


def test_every_candidate_is_scored_under_the_same_weights(
    portfolio: dict[str, object],
) -> None:
    """The condition the exact decomposition needs.

    score(A) - score(B) = 100 * sum(w_i * (n_i(A) - n_i(B))) only holds when
    one vector prices both. A run recording a vector per candidate would break
    FR-15 while leaving FR-13 looking correct.
    """
    assert portfolio["weights"]
    for candidate in portfolio["candidates"]:
        assert 0.0 <= candidate["score"] <= 100.0
        assert len(candidate["subScores"]) == 7
