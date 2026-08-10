"""FR-16 — recommend one candidate and state the rule that produced it.

    Verified against SRS §3.2 Table 17, quoted (docs/testing-strategy.md §4):
    input      "Ordered candidates of a run"
    processing "Selection of the first, then verification of dominance"
    output     "Candidate recommended and statement of the rule applied"

    And SRS §6.7, which fixes which candidate that is:
    "The recommendation of FR-16 designates the candidate of highest score."

⚠️ **FR-16 has no row in SRS Table 35.** Its §3.2 row is the promise, which is
why this file can exist while FR-10's cannot — see docs/testing-strategy.md §4.

⚠️ **FR-16 lost a clause on 2026-08-05 and did not gain an implementation.**
Its statement once ended "…and a dominated top candidate is signalled
alongside", which describes a state the arithmetic forbids: under a linear
weighted sum with non-negative weights a dominated candidate cannot outscore
its dominator, and `TIE_BREAK_ORDER` covers all seven criteria so even the tie
Pareto newly admits resolves in the dominator's favour. **C-14 deleted the
clause.** `dominatedBy` is still computed and still provably `None`, kept dead
*visibly* — and `acceptance/test_fr17.py::test_the_recommendation_never_carries_
a_dominance_flag` is where that is asserted, so this file does not repeat it.
What this file checks instead is that the verification named in Table 17's
processing row **actually happened**, which is a different claim from its
result being null.

The displayed half is the recommendation line on the comparison screen
(`features/comparison/ComparisonScreen.tsx`), which prints the candidate and
the rule together — the rule exists to be read, not merely returned.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.acceptance.conftest import Application, wire_application

pytestmark = pytest.mark.acceptance


def _recommendation(application: Application, run_id: object) -> dict[str, object] | None:
    response = application.client.get(f"/api/runs/{run_id}/recommendation")
    assert response.status_code == 200, response.text
    body = response.json()
    return None if body is None else dict(body)


def test_the_recommendation_names_the_candidate_the_run_ranks_first(
    application: Application,
) -> None:
    """Table 17: input "ordered candidates", processing "selection of the first".

    ⚠️ **The order asserted against is the one the run itself returns**, not a
    fresh maximum computed here. A recommendation that named a candidate the
    list did not show first would be indefensible however correct its
    arithmetic — the reader sees a ranked list and a recommendation on the same
    screen, and they must agree.
    """
    run = application.launch()
    recommendation = _recommendation(application, run["id"])

    assert recommendation is not None
    assert recommendation["candidate"] == run["candidates"][0]["id"]


def test_the_recommended_candidate_holds_the_highest_score(
    application: Application,
) -> None:
    """SRS §6.7, verbatim: "the candidate of highest score".

    Checked against the scores the run reported rather than against the
    recommendation's own figure, so the endpoint cannot agree with itself: the
    recommended score must be the maximum over the portfolio *and* be the
    score recorded for that candidate.
    """
    run = application.launch()
    recommendation = _recommendation(application, run["id"])
    assert recommendation is not None

    by_id = {c["id"]: c["score"] for c in run["candidates"]}

    assert recommendation["score"] == by_id[recommendation["candidate"]]
    assert recommendation["score"] == max(by_id.values())


def test_the_rule_that_produced_the_recommendation_is_stated(
    application: Application,
) -> None:
    """Table 17's output row: "…and **statement of the rule applied**".

    Carried as text by the API rather than left for the interface to caption,
    and the same sentence for every candidate: a rule that varied per
    recommendation would not be one rule the department could check once — it
    would be a description of the answer.
    """
    run = application.launch()
    recommendation = _recommendation(application, run["id"])
    assert recommendation is not None

    rule = recommendation["rule"]

    assert isinstance(rule, str) and rule.strip()
    assert "score" in rule.lower(), (
        f"the stated rule is {rule!r}, which does not mention the quantity it ranks on — "
        "a rule the reader cannot match to a figure on the page is a caption"
    )


def test_the_stated_rule_can_be_checked_against_the_figures_beside_it(
    application: Application,
) -> None:
    """The whole point of stating a rule, rather than only an answer.

    "Highest score under the weights in force" is checkable only if both halves
    are on the page: the weights the run holds in force, and every candidate's
    score under them. This asserts the reader has what the sentence asks them
    to verify — and then verifies it.
    """
    run = application.launch()
    recommendation = _recommendation(application, run["id"])
    assert recommendation is not None

    assert run["weights"], "the weights in force are not reported, so the rule names nothing"
    scores = [c["score"] for c in run["candidates"]]
    assert len(scores) >= 2, "a rule about the highest of one candidate checks nothing"

    top = next(c for c in run["candidates"] if c["id"] == recommendation["candidate"])
    assert all(top["score"] >= other for other in scores)


def test_the_recommendation_carries_a_dominance_verdict_agreeing_with_the_run_s(
    application: Application,
) -> None:
    """Table 17's processing row — "…**then verification of dominance**" — as
    far as the API can establish it, which is **not all the way**.

    ⚠️ **Read this before strengthening the name.** A recommendation that
    skipped the verification entirely and hard-coded `None` would pass this
    test, and that is not a gap that can be closed here: the outcome is
    *provably* constant. If B dominates A then every term of score(B) - score(A)
    is non-negative, and where the sum is zero `TIE_BREAK_ORDER` covers all
    seven criteria and still favours B — so the head of the ranking can never
    carry the flag, on any instance, and no run can be constructed in which a
    skipped check and a performed one differ.

    **Verified by deliberate mutation while this file was written**: removing
    the `dominance()` call from `recommend()` left every acceptance test green.
    Recorded rather than papered over. What establishes that the machinery is
    real is `unit/test_recommendation.py::test_dominance_still_reports_non_top_
    candidates`, which builds a portfolio containing a dominated candidate by
    hand — something a solver-produced portfolio cannot be relied on to contain.

    What this test *does* establish, and each of these can fail: the field is
    part of the recommendation's contract rather than dropped as dead; the
    recommended candidate is one the run actually judged; and the verdict
    reported beside the recommendation is that candidate's own, not a constant
    that happens to match nor a neighbour's.
    """
    run = application.launch()
    recommendation = _recommendation(application, run["id"])
    assert recommendation is not None
    assert "dominatedBy" in recommendation, "the verdict was dropped from the contract"

    verdicts = application.client.get(f"/api/runs/{run['id']}/dominance")
    assert verdicts.status_code == 200, verdicts.text
    by_candidate = {v["candidate"]: v["dominatedBy"] for v in verdicts.json()}

    assert by_candidate.keys() == {c["id"] for c in run["candidates"]}, (
        "the run judged a different set of candidates from the one it returned"
    )
    assert recommendation["candidate"] in by_candidate
    assert recommendation["dominatedBy"] == by_candidate[recommendation["candidate"]]


def test_a_run_that_produced_no_candidate_recommends_nothing(
    infeasible_application: Application,
) -> None:
    """ "Ordered candidates of a run" — of which there may be none.

    An instance admitting no timetable reaches this endpoint with an empty
    portfolio. Returning `null` is different from recommending nothing in
    particular: a candidate id invented here would name a timetable that does
    not exist, and the screen would offer it for publication.
    """
    run = infeasible_application.launch()
    assert run["candidates"] == []

    assert _recommendation(infeasible_application, run["id"]) is None


class _InfeasibleSolver:
    """Reports that no timetable exists, then reports a conclusive diagnosis.

    A fake rather than a real infeasible instance: what is under test is the
    recommendation endpoint's behaviour on an empty portfolio, not the engine's
    ability to prove infeasibility — that is FR-8's criterion and it costs a
    real solve. `diagnose` is implemented because the run walks on to stage 3,
    and a fake that raised there would fail the run for the wrong reason.
    """

    def solve(self, request: object) -> object:
        from optiedt.solver.interfaces import SolverOutput

        return SolverOutput(
            placements=(),
            cost=0,
            infeasible=True,
            proven_optimal=False,
            deterministic_time_used=1.0,
            wall_clock_seconds=0.01,
        )

    def diagnose(self, request: object) -> object:
        from optiedt.domain.entities import DiagnosisResult

        return DiagnosisResult(
            conflicting_codes=("H3",),
            is_minimal=True,
            is_conclusive=True,
            detail="fake diagnosis: this run exists to have no candidates",
        )


@pytest.fixture
def infeasible_application() -> Iterator[Application]:
    solver = _InfeasibleSolver()
    with wire_application(lambda: solver) as wired:
        yield wired
