"""FR-22 — explain a candidate's quality from computed figures.

    Acceptance criterion (docs/testing-strategy.md §4, shared with FR-25):
    "Switch the language service off in configuration; explanations and reports
    fall back to computed form; EVERY OTHER FUNCTION UNAFFECTED."

⚠️ **This row was ⛔ out of scope from Phase 6's close until Phase 7 M3.**

**The criterion is about the service being OFF**, which is the default
configuration, so the whole of it is verified with no provider, no key and no
network. That is not a convenience — invariant 5 says everything works with the
assistant switched off and only text disappears, and a criterion written about
the off state is what makes that testable at all.

C-21: **no test here calls a live provider.** The generated-answer half uses a
scripted fake, which can be made to fabricate a figure on demand — the failure
the grounding check exists to catch, and one a real model can only be hoped to
produce on the day the suite runs.
"""

from __future__ import annotations

import pytest

from optiedt.api import deps
from optiedt.assistant.interfaces import AssistantUnavailableError, ContextPayload
from optiedt.assistant.service import DefaultAssistant

pytestmark = pytest.mark.acceptance


class _Scripted:
    """A fake adapter. See C-21 and this module's docstring."""

    def __init__(self, reply: str | None = None, error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.calls = 0

    @property
    def enabled(self) -> bool:
        return True

    def complete(self, context: ContextPayload, prompt: str, timeout_seconds: float) -> str:
        del context, prompt, timeout_seconds
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.reply or ""


@pytest.fixture
def run(application):
    """One completed run over the fake solver — the criterion is about the
    APPLICATION, not the engine."""
    return application.launch()


def _explain(application, run, candidate_id: str):
    response = application.client.get(
        f"/api/assistant/runs/{run['id']}/candidates/{candidate_id}/explanation"
    )
    assert response.status_code == 200, response.text
    return response.json()


# ── the criterion: switched off, everything still works ────────────────


def test_with_the_service_off_an_explanation_is_still_returned(application, run) -> None:
    """200 and text, not 503. The service being off is the DEFAULT, not a
    fault, and a reader who gets an error learns something untrue about the
    application."""
    candidate = run["candidates"][0]

    answer = _explain(application, run, candidate["id"])

    assert answer["generated"] is False
    assert answer["text"].strip()


def test_the_computed_form_carries_the_candidate_s_real_figures(application, run) -> None:
    """ "Only text disappears" — the FIGURES must all still be there, because
    `analysis/` computed them either way."""
    candidate = run["candidates"][0]

    answer = _explain(application, run, candidate["id"])

    assert f"{candidate['score']:.3f}" in answer["text"]
    for sub in candidate["subScores"]:
        assert f"{sub['normalised']:.3f}" in answer["text"]


def test_the_fallback_says_why_rather_than_pretending(application, run) -> None:
    answer = _explain(application, run, run["candidates"][0]["id"])

    assert answer["fallbackReason"] is not None
    assert "switched off" in answer["fallbackReason"]


def test_every_other_function_is_unaffected_with_the_service_off(application, run) -> None:
    """The criterion's second half, and the one that would actually hurt.

    Checked against the routes a user needs rather than asserted: the run
    reads back, its candidates carry their scores, the comparison decomposes,
    dominance answers, and publication works — all with no language service.
    """
    candidate_ids = [c["id"] for c in run["candidates"]]

    assert application.client.get(f"/api/runs/{run['id']}").status_code == 200
    assert application.client.get("/api/instance").status_code == 200
    assert (
        application.client.get(
            f"/api/runs/{run['id']}/comparison?a={candidate_ids[0]}&b={candidate_ids[1]}"
        ).status_code
        == 200
    )
    assert application.client.get(f"/api/runs/{run['id']}/dominance").status_code == 200
    assert application.client.get(f"/api/runs/{run['id']}/recommendation").status_code == 200
    assert (
        application.client.post(
            f"/api/runs/{run['id']}/candidates/{candidate_ids[0]}/publish"
        ).status_code
        == 201
    )


def test_the_report_also_falls_back_and_names_every_candidate(application, run) -> None:
    """FR-25's half of the same criterion."""
    response = application.client.get(f"/api/assistant/runs/{run['id']}/report")

    assert response.status_code == 200
    answer = response.json()
    assert answer["generated"] is False
    for candidate in run["candidates"]:
        assert candidate["id"] in answer["text"]


# ── with a service: grounded answers pass, invented figures do not ─────


def _with_assistant(application, adapter):
    """Substitute the adapter, keeping the real builder and verifier.

    The grounding check is the thing under test, so it must be the real one.
    """
    application.client.app.dependency_overrides[deps.get_assistant] = lambda: DefaultAssistant(
        adapter=adapter
    )


def test_a_grounded_explanation_is_returned_as_generated(application, run) -> None:
    candidate = run["candidates"][0]
    _with_assistant(application, _Scripted(reply=f"Ce candidat obtient {candidate['score']:.3f}."))

    answer = _explain(application, run, candidate["id"])

    assert answer["generated"] is True
    assert answer["fallbackReason"] is None


def test_an_explanation_inventing_a_figure_is_discarded(application, run) -> None:
    """The failure the whole feature is built around: a plausible number nobody
    computed. It looks exactly like the figures beside it, so a reader cannot
    catch it by eye — which is why the application must."""
    candidate = run["candidates"][0]
    _with_assistant(application, _Scripted(reply="Ce candidat laisse 4271 minutes de temps mort."))

    answer = _explain(application, run, candidate["id"])

    assert answer["generated"] is False
    assert "4271" not in answer["text"]
    assert "4271" in (answer["fallbackReason"] or "")
    # And what the reader gets instead is the real figure.
    assert f"{candidate['score']:.3f}" in answer["text"]


def test_a_service_failure_falls_back_without_reaching_the_caller(application, run) -> None:
    _with_assistant(application, _Scripted(error=AssistantUnavailableError("timed out")))

    answer = _explain(application, run, run["candidates"][0]["id"])

    assert answer["generated"] is False
    assert "timed out" in (answer["fallbackReason"] or "")


def test_an_unknown_run_is_404_even_with_the_service_off(application) -> None:
    assert (
        application.client.get(
            "/api/assistant/runs/nope/candidates/whatever/explanation"
        ).status_code
        == 404
    )
