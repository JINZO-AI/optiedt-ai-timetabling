"""FR-25 — produce a readable report on a run.

    Acceptance criterion (docs/testing-strategy.md §4, shared with FR-22):
    "Switch the language service off in configuration; explanations and REPORTS
    fall back to computed form; every other function unaffected."

⚠️ **FR-25 is *Expected*, not *Necessary* (ADR-010), and it is the first thing
cut if a phase runs late** — PPM §8.3 and `docs/status.md`'s reduction order
both name it, with explanations and answers kept.

**That reduction is survivable precisely because of what is tested here.**
Cutting the report means cutting the model's PROSE, not the route: the computed
form is a complete account of the run's own figures — its parameters, every
candidate with its score, and the published candidate if there is one. A reader
who loses the language service loses the writing, not the report.

C-21: no test calls a live provider.
"""

from __future__ import annotations

import pytest

from optiedt.api import deps
from optiedt.assistant.interfaces import ContextPayload
from optiedt.assistant.service import DefaultAssistant

pytestmark = pytest.mark.acceptance


class _Scripted:
    def __init__(self, reply: str = "") -> None:
        self.reply = reply
        self.seen: list[ContextPayload] = []

    @property
    def enabled(self) -> bool:
        return True

    def complete(self, context: ContextPayload, prompt: str, timeout_seconds: float) -> str:
        del prompt, timeout_seconds
        self.seen.append(context)
        return self.reply


@pytest.fixture
def run(application):
    return application.launch()


def _report(application, run_id: str):
    response = application.client.get(f"/api/assistant/runs/{run_id}/report")
    assert response.status_code == 200, response.text
    return response.json()


# ── the criterion: cut the prose, keep the report ──────────────────────


def test_with_the_service_off_a_report_is_still_produced(application, run) -> None:
    report = _report(application, run["id"])

    assert report["generated"] is False
    assert report["text"].strip()


def test_the_report_carries_the_run_s_own_parameters(application, run) -> None:
    """Seed, budget and model version — the three FR-19's trace is built on.
    A report that omitted them would describe a result nobody could reproduce."""
    text = _report(application, run["id"])["text"]

    assert run["id"] in text
    assert str(run["seed"]) in text
    assert run["modelVersion"] in text


def test_the_report_names_every_candidate_with_its_score(application, run) -> None:
    text = _report(application, run["id"])["text"]

    for candidate in run["candidates"]:
        assert candidate["id"] in text
        assert f"{candidate['score']:.3f}" in text
        assert candidate["profileName"] in text


def test_the_report_carries_the_whole_weight_vector(application, run) -> None:
    """One vector prices every candidate of the run. A report quoting scores
    without the weights that produced them cannot be checked by hand."""
    text = _report(application, run["id"])["text"]

    for code in run["weights"]:
        assert code in text


def test_the_report_says_plainly_when_nothing_was_published(application, run) -> None:
    """⚠️ Silence would read as "a candidate was published and this report does
    not mention it". An absence has to be stated to be an absence."""
    text = _report(application, run["id"])["text"]

    assert "No candidate from this run has been published" in text


def test_the_report_marks_the_published_candidate(application, run) -> None:
    """`docs/ai-integration.md`'s context table gives a report "the published
    timetable". ⚠️ It is looked up by the ROUTER and passed in as a value — the
    assistant may not fetch it (invariant 4)."""
    published = run["candidates"][0]["id"]
    assert (
        application.client.post(f"/api/runs/{run['id']}/candidates/{published}/publish").status_code
        == 201
    )

    text = _report(application, run["id"])["text"]

    assert "published" in text
    published_line = next(line for line in text.splitlines() if published in line)
    assert "published" in published_line


# ── with a service ─────────────────────────────────────────────────────


def _with_assistant(application, adapter):
    application.client.app.dependency_overrides[deps.get_assistant] = lambda: DefaultAssistant(
        adapter=adapter
    )


def test_a_grounded_report_is_returned_as_generated(application, run) -> None:
    score = run["candidates"][0]["score"]
    _with_assistant(application, _Scripted(reply=f"Trois candidats, le meilleur à {score:.3f}."))

    report = _report(application, run["id"])

    assert report["generated"] is True


def test_a_report_inventing_a_figure_is_discarded(application, run) -> None:
    _with_assistant(application, _Scripted(reply="La génération a duré 1847 secondes."))

    report = _report(application, run["id"])

    assert report["generated"] is False
    assert "1847" not in report["text"]
    assert "1847" in (report["fallbackReason"] or "")


def test_the_report_context_carries_every_candidate(application, run) -> None:
    adapter = _Scripted(reply="Rien à signaler.")
    _with_assistant(application, adapter)

    _report(application, run["id"])

    figures = adapter.seen[0].figures
    for index in range(1, len(run["candidates"]) + 1):
        assert f"candidate{index}.score" in figures


def test_an_unknown_run_is_404(application) -> None:
    assert application.client.get("/api/assistant/runs/nope/report").status_code == 404
