"""FR-17 — signal a candidate that another dominates.

    Acceptance criterion, from docs/scoring-and-explanation.md §Dominance:
    "A candidate that another is at least as good on every criterion and
    strictly better on at least one is dominated, and the interface signals it
    wherever it appears in the portfolio."

⚠️ **This criterion did not exist in a testable form until 2026-08-05.** FR-17
is one of the four requirements C-9 records as having no input/processing/
output row in the SRS, and the statement it did carry - "signal a *recommended*
candidate that another dominates" - describes a state the arithmetic forbids.
C-14's resolution reworded §Dominance, and that wording is what this file
verifies. **C-9 itself is still open** for FR-6, FR-10 and FR-18.

The display half is `frontend/src/features/comparison/DominanceNotice.test.tsx`
- in particular that an empty verdict list reads as "checked, none found"
rather than as a screen that does nothing.
"""

from __future__ import annotations

import pytest

from tests.acceptance.conftest import Application

pytestmark = pytest.mark.acceptance


def _verdicts(application: Application, run_id: object) -> list[dict[str, object]]:
    response = application.client.get(f"/api/runs/{run_id}/dominance")
    assert response.status_code == 200, response.text
    return list(response.json())


def test_every_candidate_receives_a_verdict(application: Application) -> None:
    """A verdict for each, not only for the dominated ones.

    A list containing only the dominated would leave a reader unable to tell
    "this candidate was checked and is fine" from "this candidate was not in
    the list I was given".
    """
    run = application.launch()
    verdicts = _verdicts(application, run["id"])

    assert {v["candidate"] for v in verdicts} == {c["id"] for c in run["candidates"]}


def test_a_verdict_names_its_dominator_rather_than_a_flag(application: Application) -> None:
    """`dominatedBy` carries an id, not a boolean.

    "This candidate is dominated" is not actionable; "this candidate is
    dominated by that one" lets the reader open the pair and see it.
    """
    run = application.launch()
    verdicts = _verdicts(application, run["id"])

    ids = {c["id"] for c in run["candidates"]}
    for verdict in verdicts:
        assert set(verdict) == {"candidate", "dominatedBy"}
        if verdict["dominatedBy"] is not None:
            assert verdict["dominatedBy"] in ids
            assert verdict["dominatedBy"] != verdict["candidate"]


def test_the_verdicts_agree_with_the_sub_scores_the_run_reports(
    application: Application,
) -> None:
    """The criterion re-derived from the figures on the same page.

    The point of dominance is that it is exact and needs no weights, so it can
    be recomputed by anyone holding the sub-scores. This recomputes it from the
    run payload rather than trusting the endpoint to agree with itself.
    """
    run = application.launch()
    verdicts = {v["candidate"]: v["dominatedBy"] for v in _verdicts(application, run["id"])}

    by_id = {
        c["id"]: {s["criterion"]: s["normalised"] for s in c["subScores"]}
        for c in run["candidates"]
    }

    for candidate, own in by_id.items():
        expected = any(
            other != candidate
            and all(values[code] >= own[code] for code in own)
            and any(values[code] > own[code] for code in own)
            for other, values in by_id.items()
        )
        assert (verdicts[candidate] is not None) is expected, (
            f"{candidate}: endpoint says dominated={verdicts[candidate] is not None}, "
            f"the sub-scores it reported say {expected}"
        )


def test_the_top_ranked_candidate_is_never_reported_dominated(
    application: Application,
) -> None:
    """Not an observation - a consequence.

    Every term of score(B) - score(A) is non-negative when B dominates A, and
    where the sum is zero TIE_BREAK_ORDER covers all seven criteria and still
    favours B. So the head of the ranking cannot carry this flag, and a screen
    that presented its silence as a finding would be reporting arithmetic as
    evidence (C-14).
    """
    run = application.launch()
    verdicts = {v["candidate"]: v["dominatedBy"] for v in _verdicts(application, run["id"])}
    top = run["candidates"][0]["id"]

    assert verdicts[top] is None


def test_the_recommendation_never_carries_a_dominance_flag(application: Application) -> None:
    """The same statement where FR-16 exposes it.

    `dominatedBy` on the recommendation is provably always null. It is checked
    rather than removed so that it stays dead visibly - if it ever fires, the
    score has stopped being a linear weighted sum with non-negative weights.
    """
    run = application.launch()
    response = application.client.get(f"/api/runs/{run['id']}/recommendation")

    assert response.status_code == 200
    assert response.json()["dominatedBy"] is None
