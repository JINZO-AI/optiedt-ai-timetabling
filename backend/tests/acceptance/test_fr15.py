"""FR-15 — state each criterion's contribution to the difference.

    Acceptance criterion (docs/testing-strategy.md §4):
    "Compare two candidates → sum of contributions equals the score difference."

This is the identity the whole explanation feature rests on:

    score(A) - score(B) = 100 * sum( w_i * ( n_i(A) - n_i(B) ) )

⚠️ **The DISPLAYED half of this criterion is not verified here and cannot be.**
Rounding happens in the component, and rounding each term independently does
not preserve the sum - a real defect found in Phase 4 M5, fixed with
largest-remainder rounding. `frontend/src/features/comparison/
ContributionsTable.test.tsx` renders the table and reads the figures back out
of the DOM. What this file verifies is that the API hands the interface an
identity that holds exactly; both halves are needed and neither substitutes
for the other.
"""

from __future__ import annotations

import pytest

from tests.acceptance.conftest import Application

pytestmark = pytest.mark.acceptance


def _compare(application: Application, run: dict[str, object]) -> dict[str, object]:
    candidates = run["candidates"]
    assert isinstance(candidates, list) and len(candidates) >= 2
    a, b = candidates[0]["id"], candidates[1]["id"]
    response = application.client.get(f"/api/runs/{run['id']}/comparison", params={"a": a, "b": b})
    assert response.status_code == 200, response.text
    return dict(response.json())


def test_the_contributions_sum_to_the_score_difference(application: Application) -> None:
    run = application.launch()
    body = _compare(application, run)

    total = sum(c["value"] for c in body["contributions"])

    assert total == pytest.approx(body["scoreDifference"], abs=1e-9)


def test_every_criterion_appears_in_the_decomposition(application: Application) -> None:
    """Including the ones that contribute nothing.

    A criterion omitted because its contribution is zero would make the column
    add up while hiding that it was considered - and the reader could not tell
    "no difference on S10" from "S10 was not looked at".
    """
    run = application.launch()
    body = _compare(application, run)

    codes = {c["criterion"] for c in body["contributions"]}
    assert codes == {"S2", "S3", "S4", "S5", "S6", "S7", "S10"}


def test_each_contribution_is_recomputable_from_the_figures_beside_it(
    application: Application,
) -> None:
    """The term-by-term claim, not just the total.

    docs/scoring-and-explanation.md says the contribution shown to the user is
    the score calculation read term by term. A total that agrees while
    individual terms are wrong would satisfy the sum test above and break the
    promise the feature actually makes.
    """
    run = application.launch()
    body = _compare(application, run)

    for contribution in body["contributions"]:
        expected = (
            100.0
            * contribution["weight"]
            * (contribution["normalisedA"] - contribution["normalisedB"])
        )
        assert contribution["value"] == pytest.approx(expected, abs=1e-9), (
            f"{contribution['criterion']} is not 100 x weight x (n_A - n_B)"
        )


def test_the_weights_used_are_the_run_s_weights_in_force(application: Application) -> None:
    """One vector prices both sides, or the identity does not hold at all.

    A candidate's `profileName` is provenance - how the placement was obtained
    - never its own scoring weight (docs/scoring-and-explanation.md). The
    decomposition's weights are renormalised to sum to 1, so they are compared
    as a ratio against the run's recorded vector rather than element-wise.
    """
    run = application.launch()
    body = _compare(application, run)

    recorded = dict(run["weights"])
    total = sum(recorded.values())
    assert total > 0

    for contribution in body["contributions"]:
        expected = recorded[contribution["criterion"]] / total
        assert contribution["weight"] == pytest.approx(expected, abs=1e-9)
