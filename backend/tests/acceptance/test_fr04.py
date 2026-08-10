"""FR-4 — improve the quality criteria within a time limit.

    Verified against SRS §3.2 Table 7, quoted (docs/testing-strategy.md §4):
    input      "Weights of the criteria and time limit"
    processing "Minimisation of the weighted penalty within the limit"
    output     "Best solution found when the limit is reached"

    And SRS §6.4, which gives the objective its form and one operative rule:
    "minimise Σ ( weight_i * violations_i )"
    "A criterion of weight zero is measured and displayed but does not
     influence the order."

⚠️ **FR-4 has no row in SRS Table 35**, the acceptance-test table. It has a
detailed §3.2 row instead, which is the opposite shape from C-9's four (Table 35
row absent *and* §3.2 row absent) and is why this file can exist while FR-10's
cannot. The distinction is set out in docs/testing-strategy.md §4; do not
collapse the two.

⚠️ **This file deliberately does NOT re-assert what neighbouring tests already
establish, and the omissions are the interesting part:**

- *That raising a criterion's weight lowers its violations* is
  `acceptance/test_fr13.py::test_a_favouring_profile_wins_its_headline_criterion`.
  It is FR-4's mechanism seen through FR-13's portfolio, and asserting it twice
  would double the cost of the sweep to widen no claim.
- *That the deterministic budget binds per worker* is
  `integration/test_reproducibility.py::test_the_deterministic_budget_binds_per_worker`.
  ⚠️ **The run-level figure is NOT bounded by the budget** and an acceptance
  test asserting `deterministicTimeUsed <= deterministicBudget` would be wrong:
  `CpSolver.deterministic_time` reports the **sum across workers**, so a run at
  budget 45 on four workers reported 45.76 and one at budget 30 on sixteen
  reported ~84 (docs/status.md, Measurements). Reading that sum as an overrun is
  the recorded C-2 error, and it cost this project a documented "~11* overshoot"
  that never existed.
- *That the solver's own objective value agrees with the analysis layer's* is
  `integration/test_objective_matches_analysis.py`. It cannot be asserted from
  here anyway: `SolverOutput.cost` is informational only, and ADR-011 records
  `CpSolver.objective_value` sitting a few units above the objective at the
  solution actually returned. **Nothing in this file is built on `cost`.**

What is left is FR-4's own, and none of it is covered elsewhere: that the two
inputs of Table 7 are real inputs a caller supplies and the run records, that
every criterion the objective prices is measured on the solution that comes
back, that §6.4's zero-weight rule holds in both halves, and that the search
ends on its deterministic limit with a complete answer rather than on the
wall-clock backstop.
"""

from __future__ import annotations

import pytest

from tests.acceptance.conftest import SOFT_CODES, Application

pytestmark = pytest.mark.acceptance

#: The criterion SRS §6.4 Table 28 gives a default weight of 0.00.
ZERO_WEIGHT_CODE = "S10"


def test_the_caller_supplies_the_time_limit_and_the_run_records_it(
    application: Application,
) -> None:
    """Half of Table 7's input row, and the half a caller can get wrong.

    A run that quietly substituted the configured default would look identical
    on screen and would make every reproduction attempt fail against the trace
    it published (FR-19).
    """
    run = application.launch(deterministicBudget=7.5)

    assert run["deterministicBudget"] == 7.5


def test_the_run_records_the_weights_of_the_criteria_it_optimised_under(
    application: Application,
) -> None:
    """The other half of Table 7's input row.

    Exactly the seven soft codes: the weighted penalty is over quality
    criteria, and a hard rule appearing here would mean something priced a
    constraint the solver is supposed to guarantee.
    """
    run = application.launch()
    weights = run["weights"]

    assert isinstance(weights, dict)
    assert set(weights) == SOFT_CODES
    assert all(value >= 0.0 for value in weights.values()), (
        "a negative weight would invert the criterion it prices and break the "
        "monotonicity the ranking rests on"
    )


def test_the_weights_recorded_are_the_catalogue_s_and_not_a_constant(
    application: Application,
) -> None:
    """`data/instance/constraint_catalogue.csv` is the authority on weights.

    Read from the instance the API itself serves rather than from a literal
    here, so editing the catalogue moves the run and this test together - which
    is the whole point of the weights being data.
    """
    run = application.launch()
    catalogue = application.client.get("/api/instance").json()["constraints"]
    expected = {c["code"]: c["defaultWeight"] for c in catalogue if c["kind"] == "SOFT"}

    assert run["weights"] == pytest.approx(expected)


def test_every_criterion_the_objective_prices_is_measured_on_the_solution_returned(
    application: Application,
) -> None:
    """Table 7's output row has teeth only if the penalty was measurable.

    "Minimisation of the weighted penalty" is a claim about Σ(w_i * v_i), and a
    criterion carrying a weight but no measured value on the returned candidate
    would make one term of that sum unverifiable by anyone.
    """
    run = application.launch()
    priced = set(run["weights"])

    for candidate in run["candidates"]:
        measured = {s["criterion"] for s in candidate["subScores"]}
        assert measured == priced, (
            f"{candidate['id']}: priced {sorted(priced - measured)} without measuring it"
        )


def test_a_criterion_of_weight_zero_is_measured_and_displayed(
    application: Application,
) -> None:
    """SRS §6.4, first half of the zero-weight rule.

    S10 (midday break) carries weight 0.00 in the catalogue. "Measured and
    displayed" is the specification's own wording, and dropping it because it
    prices nothing would leave a reader unable to tell "the midday break was
    considered and this candidate keeps it" from "nobody looked".
    """
    run = application.launch()

    assert run["weights"][ZERO_WEIGHT_CODE] == 0.0

    for candidate in run["candidates"]:
        measured = {s["criterion"]: s for s in candidate["subScores"]}
        assert ZERO_WEIGHT_CODE in measured, "a zero weight removed the criterion from the report"
        assert isinstance(measured[ZERO_WEIGHT_CODE]["rawValue"], int | float)


def test_a_criterion_of_weight_zero_does_not_influence_the_order(
    application: Application,
) -> None:
    """SRS §6.4, second half - and it is an exact zero, not a small one.

    The contribution of criterion i to a score difference is
    100 * w_i * (n_i(A) - n_i(B)), so w_i = 0 makes the term vanish however far
    apart the two candidates sit on it. Asserting `== 0.0` rather than
    `approx(0)` is deliberate: a weight that had drifted to 1e-9 would still
    round to zero on screen while quietly deciding a tie.
    """
    run = application.launch()
    candidates = run["candidates"]
    assert len(candidates) >= 2

    response = application.client.get(
        f"/api/runs/{run['id']}/comparison",
        params={"a": candidates[0]["id"], "b": candidates[1]["id"]},
    )
    assert response.status_code == 200, response.text

    term = next(c for c in response.json()["contributions"] if c["criterion"] == ZERO_WEIGHT_CODE)

    assert term["weight"] == 0.0
    assert term["value"] == 0.0


@pytest.mark.solver
def test_the_search_ends_on_its_deterministic_limit_with_a_complete_solution(
    production_portfolio: dict[str, object],
) -> None:
    """Table 7's output row against the real engine: "**best solution found
    when the limit is reached**".

    Three things together are what that sentence promises, and each can fail
    independently:

    1. The run **completes** rather than failing - the limit ends the search
       with an answer. At too small a budget CP-SAT returns `UNKNOWN` and the
       run lands in `FAILED`, because the engine refuses to present a
       non-answer as a timetable (acceptance/conftest.py, measured).
    2. What comes back is a **complete** timetable, all 218 sessions placed -
       not the best partial arrangement the search happened to hold.
    3. The solve ended on its **deterministic** budget and not on the
       wall-clock ceiling, which ADR-011 calls a hang backstop and not a normal
       exit path. A run that routinely ended there would not be reproducible
       whatever its seed said.

    ⚠️ No assertion here compares `deterministicTimeUsed` with
    `deterministicBudget`: that figure is the sum across workers and exceeds
    the budget by design (see this module's docstring, and C-2).
    """
    from optiedt.api import deps

    deps.get_settings.cache_clear()
    ceiling = deps.get_settings().solver_wall_clock_ceiling_seconds

    assert production_portfolio["state"] == "COMPLETED"
    assert production_portfolio["error"] is None
    assert production_portfolio["candidates"], "the limit was reached with no solution to show"

    for candidate in production_portfolio["candidates"]:
        assert len(candidate["placements"]) == 218, (
            f"{candidate['id']} is a partial timetable, not a best solution found"
        )

    wall = production_portfolio["wallClockSeconds"]
    assert wall < ceiling * len(production_portfolio["candidates"]), (
        f"the run spent {wall:.1f} s against a per-solve hang backstop of {ceiling} s - "
        "if a solve is ending on the ceiling, ADR-011's reproducibility argument no "
        "longer holds"
    )
