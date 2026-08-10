"""FR-14 — compare two candidates criterion by criterion on the same screen.

    Verified against SRS §3.2 Table 15, quoted (docs/testing-strategy.md §4):
    input      "Two candidates of the same run"
    processing "Reading of the sub-scores recorded for each"
    output     "Table of the criteria with the two values and their difference"

⚠️ **FR-14 has no row in SRS Table 35.** Its §3.2 row is the promise, which is
why this file can exist while FR-10's cannot — see docs/testing-strategy.md §4.

⚠️ **FR-14 and FR-15 are two requirements over one endpoint, and the split
matters.** FR-15 is *"state each criterion's contribution to the difference"*
and its criterion is the identity — the contributions sum to the score
difference — which `acceptance/test_fr15.py` verifies. FR-14 is the table
itself: **two candidates of the same run**, **their two recorded values**, and
**a difference per criterion**. Nothing here re-asserts the sum; nothing there
asserts the input row. Read together they cover the endpoint; read separately
neither is redundant.

The rendered half is `frontend/src/features/comparison/ContributionsTable.test.tsx`,
which reads the figures back out of the DOM — "on the same screen" is a claim
only a rendering test can make.
"""

from __future__ import annotations

import pytest

from tests.acceptance.conftest import SOFT_CODES, Application

pytestmark = pytest.mark.acceptance


def _comparison(application: Application, run_id: object, a: str, b: str) -> dict[str, object]:
    response = application.client.get(f"/api/runs/{run_id}/comparison", params={"a": a, "b": b})
    assert response.status_code == 200, response.text
    return dict(response.json())


def test_two_candidates_of_the_same_run_are_compared(application: Application) -> None:
    """Table 15's input row, and the comparison echoes which two it read.

    A table that did not name its own columns would be unusable next to a
    portfolio of three: the reader could not tell which candidate is A.
    """
    run = application.launch()
    a, b = run["candidates"][0]["id"], run["candidates"][1]["id"]

    body = _comparison(application, run["id"], a, b)

    assert body["candidateA"] == a
    assert body["candidateB"] == b


def test_a_candidate_from_another_run_cannot_be_compared(
    application: Application,
) -> None:
    """ "Of the **same** run" is a constraint, not a description.

    ⚠️ **This is the assertion with the most at stake in the file.** Each run
    records its own weight vector, and the decomposition
    `score(A) - score(B) = 100 * Σ(w_i * (n_i(A) - n_i(B)))` holds only when one
    vector prices both sides. A cross-run comparison would return a table of
    real-looking figures whose column does not add up to anything — and it
    would look exactly like a working comparison.

    404 rather than 422: from the endpoint's point of view the candidate does
    not exist, because a run is where candidates are looked up.
    """
    first = application.launch()
    second = application.launch()

    foreign = second["candidates"][0]["id"]
    mine = first["candidates"][0]["id"]
    assert foreign not in {c["id"] for c in first["candidates"]}, (
        "the two runs reused a candidate id, so this test would pass for the wrong reason"
    )

    response = application.client.get(
        f"/api/runs/{first['id']}/comparison", params={"a": mine, "b": foreign}
    )

    assert response.status_code == 404, response.text


def test_a_candidate_cannot_be_compared_with_itself(application: Application) -> None:
    """Also "two candidates".

    Refused rather than answered with a table of zeros: a screen full of zeros
    reads as "these two are identical", which is a statement about the
    portfolio, not about a mis-click.
    """
    run = application.launch()
    same = run["candidates"][0]["id"]

    response = application.client.get(
        f"/api/runs/{run['id']}/comparison", params={"a": same, "b": same}
    )

    assert response.status_code == 422, response.text


def test_the_table_carries_one_row_per_criterion(application: Application) -> None:
    """ "Table of the **criteria**" — all seven, in a stable order.

    Sorted rather than incidental, because the reader is invited to check the
    column by hand and a table that reordered itself between two runs of the
    same comparison would make that impossible.
    """
    run = application.launch()
    body = _comparison(
        application, run["id"], run["candidates"][0]["id"], run["candidates"][1]["id"]
    )

    codes = [c["criterion"] for c in body["contributions"]]

    assert set(codes) == SOFT_CODES
    assert codes == sorted(codes)


def test_each_row_carries_the_two_values(application: Application) -> None:
    """ "…with the **two values**".

    Both sides on one row is what makes the table a comparison rather than two
    reports side by side: the reader sees S3 for A and S3 for B without holding
    a place in a second list.
    """
    run = application.launch()
    body = _comparison(
        application, run["id"], run["candidates"][0]["id"], run["candidates"][1]["id"]
    )

    for row in body["contributions"]:
        assert "normalisedA" in row and "normalisedB" in row
        assert isinstance(row["normalisedA"], int | float)
        assert isinstance(row["normalisedB"], int | float)


def test_the_two_values_are_the_sub_scores_recorded_with_each_candidate(
    application: Application,
) -> None:
    """Table 15's processing row, verbatim: "**Reading** of the sub-scores
    **recorded** for each".

    Not "recomputation of". A candidate is immutable once recorded (invariant 6)
    and its sub-scores were measured when it was produced; a comparison that
    recomputed them from the placements would be answering a subtly different
    question and could drift from the figures shown beside it on the same
    screen — the candidate summary reads `subScores`, this table would read
    something else, and the two would disagree in front of the reader.

    Compared exactly, not approximately: these must be the same numbers, not
    numbers that agree.
    """
    run = application.launch()
    a, b = run["candidates"][0], run["candidates"][1]
    body = _comparison(application, run["id"], a["id"], b["id"])

    recorded_a = {s["criterion"]: s["normalised"] for s in a["subScores"]}
    recorded_b = {s["criterion"]: s["normalised"] for s in b["subScores"]}

    for row in body["contributions"]:
        code = row["criterion"]
        assert row["normalisedA"] == recorded_a[code], f"{code}: A's value was not read from A"
        assert row["normalisedB"] == recorded_b[code], f"{code}: B's value was not read from B"


def test_the_difference_between_the_two_values_is_readable_from_the_row(
    application: Application,
) -> None:
    """ "…and **their difference**".

    The row carries the two values and the weighted term, so the difference is
    recoverable and its *direction* must match: a contribution favouring A while
    A's value is the lower one would put a plus sign against a loss.

    ⚠️ A criterion carrying weight zero is exempt from the direction check, not
    from the row — S10 contributes exactly 0.0 however far apart the two values
    sit, which is SRS §6.4's rule and is asserted in `test_fr04`.
    """
    run = application.launch()
    body = _comparison(
        application, run["id"], run["candidates"][0]["id"], run["candidates"][1]["id"]
    )

    compared = 0
    for row in body["contributions"]:
        difference = row["normalisedA"] - row["normalisedB"]
        if row["weight"] == 0.0 or difference == 0.0:
            continue
        compared += 1
        assert (row["value"] > 0) is (difference > 0), (
            f"{row['criterion']}: value {row['value']} disagrees in sign with "
            f"n(A) - n(B) = {difference}"
        )

    assert compared, "the two candidates differ on no weighted criterion — nothing was compared"


def test_a_criterion_the_two_candidates_agree_on_reads_as_no_difference(
    application: Application,
) -> None:
    """Equal values must give exactly zero, not a rounding artefact.

    The table is presented as the score calculation read term by term, so a row
    where the two candidates genuinely agree has to show nothing rather than a
    trailing figure the reader would try to explain.
    """
    run = application.launch()
    body = _comparison(
        application, run["id"], run["candidates"][0]["id"], run["candidates"][1]["id"]
    )

    for row in body["contributions"]:
        if row["normalisedA"] == row["normalisedB"]:
            assert row["value"] == 0.0, f"{row['criterion']}: equal values gave {row['value']}"
