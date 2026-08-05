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

⚠️ **FR-13 is not `✓` on this test alone.** C-15 is still open: the objective
weights raw violation counts of incomparable scale, so "teacher-favouring"
measurably improves S5 and not S3. This file asserts what was accepted - three
distinct candidates under distinct profiles - and makes no claim about what a
profile favours, exactly as the comparison screen makes none.
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
