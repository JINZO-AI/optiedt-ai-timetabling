"""FR-19 — record every run with its data, seed, weights and results.

FR-19 carries **two** of the nine acceptance criteria, and they are different
claims about the same record:

    "Two runs with the same data, weights and seed produce the same candidates
    in the same order."   (docs/testing-strategy.md §4: repeat a run)

    "Every published timetable traces back to its run, seed and weights."

The first needs the real engine and is marked `solver`; the second is about
what the application assembles and runs against the fake. They live in one file
because they are one requirement, and splitting them would invite the reader to
think FR-19 is finished when only half of it is.

⚠️ `tests/integration/test_reproducibility.py` pins reproducibility against the
engine directly, at the production worker count. This file makes the same claim
about **two runs a user launches through the API**, which is what the criterion
says. Neither replaces the other.
"""

from __future__ import annotations

import pytest

from tests.acceptance.conftest import (
    PRODUCTION_BUDGET,
    PRODUCTION_SEED,
    Application,
    solve_at_production_settings,
)

pytestmark = pytest.mark.acceptance


# ── the trace, against the fake solver ─────────────────────────────────


def test_a_published_timetable_carries_its_run_seed_and_weights(
    application: Application,
) -> None:
    run = application.launch()
    candidate = run["candidates"][0]["id"]

    published = application.client.post(
        f"/api/runs/{run['id']}/candidates/{candidate}/publish", json={}
    )
    assert published.status_code in (200, 201), published.text

    body = published.json()
    assert body["run"] == run["id"]
    assert body["seed"] == run["seed"]
    assert body["weights"] == run["weights"]
    assert body["modelVersion"] == run["modelVersion"]
    assert body["deterministicBudget"] == run["deterministicBudget"]


def test_the_trace_is_returned_by_listing_not_only_by_publishing(
    application: Application,
) -> None:
    """A criterion satisfied only in the response to the act that created the
    record is not satisfied at all - nobody re-publishes a timetable in order
    to read what produced it."""
    run = application.launch()
    candidate = run["candidates"][0]["id"]
    application.client.post(f"/api/runs/{run['id']}/candidates/{candidate}/publish", json={})

    listed = application.client.get("/api/publications")

    assert listed.status_code == 200
    records = listed.json()
    assert records
    for record in records:
        assert record["run"] and record["seed"] is not None
        assert record["weights"] and record["modelVersion"]


def test_the_whole_weight_vector_is_traced_including_the_zero_weight_one(
    application: Application,
) -> None:
    """A score is only recomputable by hand from EVERY weight.

    S10 carries weight 0 and is the one a summary would drop first, which is
    exactly why it is the one asserted.
    """
    run = application.launch()
    candidate = run["candidates"][0]["id"]
    body = application.client.post(
        f"/api/runs/{run['id']}/candidates/{candidate}/publish", json={}
    ).json()

    assert set(body["weights"]) == {"S2", "S3", "S4", "S5", "S6", "S7", "S10"}


def test_the_published_timetable_carries_the_placements_it_names(
    application: Application,
) -> None:
    """The trace has to reach the timetable, not merely the run that made it."""
    run = application.launch()
    candidate = run["candidates"][0]
    body = application.client.post(
        f"/api/runs/{run['id']}/candidates/{candidate['id']}/publish", json={}
    ).json()

    assert body["candidate"]["id"] == candidate["id"]
    assert len(body["candidate"]["placements"]) == len(candidate["placements"])


# ── reproducibility, against the real engine ───────────────────────────


@pytest.fixture(scope="module")
def two_identical_runs(
    production_portfolio: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """The same request twice - the criterion's exact wording.

    The first is the portfolio FR-3 and FR-13 also use; the second is solved
    here, because "repeat a run" is not a question one run can answer. That
    keeps the sweep at two production solves rather than four.

    ⚠️ Bounded by a DETERMINISTIC budget, never by wall clock (ADR-011). A
    reproducibility test bounded by seconds would pass on one machine and fail
    on another, and the failure would look like a solver bug.

    ⚠️ The second run is launched into a FRESH application - new store, new
    executor, new solver - so what is compared is two runs of the software, not
    one run read twice out of one process's memory.
    """
    return production_portfolio, solve_at_production_settings()


@pytest.mark.solver
def test_two_runs_produce_the_same_candidates_in_the_same_order(
    two_identical_runs: tuple[dict[str, object], dict[str, object]],
) -> None:
    first, second = two_identical_runs

    assert [c["profileName"] for c in first["candidates"]] == [
        c["profileName"] for c in second["candidates"]
    ]
    assert [c["score"] for c in second["candidates"]] == pytest.approx(
        [c["score"] for c in first["candidates"]]
    )


@pytest.mark.solver
def test_the_placements_themselves_are_identical(
    two_identical_runs: tuple[dict[str, object], dict[str, object]],
) -> None:
    """Same order and same scores could hold while the timetables differed.

    Two arrangements can score alike, so agreeing on the ranking is weaker
    than the criterion - which says the same CANDIDATES.
    """
    first, second = two_identical_runs

    def arrangement(run: dict[str, object]) -> list[set[tuple[object, ...]]]:
        return [
            {(p["session"], p["slot"], p["room"]) for p in candidate["placements"]}
            for candidate in run["candidates"]
        ]

    assert arrangement(first) == arrangement(second)


@pytest.mark.solver
def test_the_sub_scores_are_identical_too(
    two_identical_runs: tuple[dict[str, object], dict[str, object]],
) -> None:
    first, second = two_identical_runs

    def sub_scores(run: dict[str, object]) -> list[dict[str, float]]:
        return [
            {s["criterion"]: s["normalised"] for s in candidate["subScores"]}
            for candidate in run["candidates"]
        ]

    for left, right in zip(sub_scores(first), sub_scores(second), strict=True):
        assert left.keys() == right.keys()
        for code in left:
            assert left[code] == pytest.approx(right[code])


@pytest.mark.solver
def test_the_run_records_the_seed_and_budget_it_was_given(
    two_identical_runs: tuple[dict[str, object], dict[str, object]],
) -> None:
    """Without this the reproducibility claim is unverifiable by anyone else:
    "the same seed and weights" is only checkable if the run says what they
    were."""
    for run in two_identical_runs:
        assert run["seed"] == PRODUCTION_SEED
        assert run["deterministicBudget"] == PRODUCTION_BUDGET
        assert run["modelVersion"]
        assert set(run["weights"]) == {"S2", "S3", "S4", "S5", "S6", "S7", "S10"}
