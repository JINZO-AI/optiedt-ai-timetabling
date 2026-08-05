"""FR-5 — produce several candidates, each scored out of 100.

    Acceptance criterion (docs/testing-strategy.md §4):
    "Read a candidate → overall score and sub-scores displayed."

Against the fake solver: the criterion is about what the application returns
for a candidate, not about the quality of the placements. Every score read
below is nevertheless computed by `analysis/criteria.py` from real placements
- the fake supplies a timetable, not a score.
"""

from __future__ import annotations

import pytest

from tests.acceptance.conftest import SOFT_CODES, Application

pytestmark = pytest.mark.acceptance


def test_a_candidate_carries_an_overall_score_out_of_100(application: Application) -> None:
    run = application.launch()

    candidates = run["candidates"]
    assert isinstance(candidates, list) and candidates

    for candidate in candidates:
        assert 0.0 <= candidate["score"] <= 100.0


def test_a_candidate_carries_all_seven_sub_scores(application: Application) -> None:
    """All seven, including the zero-weight S10.

    A sub-score is not dropped because nothing optimises for it: the score is
    only recomputable by hand from every criterion and every weight, which is
    the property the whole scoring design exists to preserve
    (docs/scoring-and-explanation.md).
    """
    run = application.launch()

    for candidate in run["candidates"]:
        codes = {s["criterion"] for s in candidate["subScores"]}
        assert codes == set(SOFT_CODES), f"expected all seven criteria, got {sorted(codes)}"


def test_each_sub_score_carries_its_raw_value_and_its_normalised_value(
    application: Application,
) -> None:
    """Both, because only the pair is checkable.

    The normalised value is what the score is built from; the raw value is what
    a reader can count on the timetable. Showing one without the other leaves
    a figure nobody can verify.
    """
    run = application.launch()

    for candidate in run["candidates"]:
        for sub in candidate["subScores"]:
            assert "rawValue" in sub and "normalised" in sub
            assert 0.0 <= sub["normalised"] <= 1.0, (
                f"{sub['criterion']} normalised outside [0,1] - bounds are "
                "instance-derived and must contain every candidate (ADR-009)"
            )


def test_a_candidate_is_readable_on_its_own_endpoint(application: Application) -> None:
    """FR-5 says a candidate is READ, so the criterion needs the read path,
    not merely the field being present in the run payload."""
    run = application.launch()
    candidate_id = run["candidates"][0]["id"]

    response = application.client.get(f"/api/runs/{run['id']}/candidates/{candidate_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == candidate_id
    assert 0.0 <= body["score"] <= 100.0
    assert {s["criterion"] for s in body["subScores"]} == set(SOFT_CODES)


def test_several_candidates_are_produced(application: Application) -> None:
    """ "Several" is FR-5's own word. How many, and that they are DISTINCT, is
    FR-13's criterion and is measured there against the real solver."""
    run = application.launch()

    assert len(run["candidates"]) >= 2
