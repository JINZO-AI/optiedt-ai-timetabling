"""FR-24 — answer a question in ordinary language about a run.

    Acceptance criterion (docs/testing-strategy.md §4):
    "Ask a question whose answer is not in the context. The assistant says it
    cannot answer, and INVENTS NO FIGURE."

⚠️ **Read the criterion carefully: it is written about the case the feature
CANNOT serve.** It does not ask whether a good question gets a good answer —
that would be a claim about a language model, which no test in this repository
makes (C-21). It asks what happens at the edge, because that is where a
language model does the damage this project cannot absorb: a plausible figure
nobody computed, sitting beside real ones, in a document a department must
defend.

**Two ways the requirement can be met, and both are tested.** A model that says
"I cannot answer" satisfies it directly. A model that answers anyway with an
invented figure is caught by the grounding check and its answer discarded — so
the requirement holds even when the model does not cooperate. **The second is
the one that matters**, because it does not depend on the model behaving.
"""

from __future__ import annotations

import pytest

from optiedt.api import deps
from optiedt.assistant.interfaces import AssistantUnavailableError, ContextPayload
from optiedt.assistant.service import DefaultAssistant

pytestmark = pytest.mark.acceptance


class _Scripted:
    """A fake adapter — C-21. It also records the context it was shown, which
    is how the data-minimisation assertions below are made."""

    def __init__(self, reply: str = "", error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.seen: list[ContextPayload] = []

    @property
    def enabled(self) -> bool:
        return True

    def complete(self, context: ContextPayload, prompt: str, timeout_seconds: float) -> str:
        del timeout_seconds
        self.seen.append(context)
        self.prompt = prompt
        if self.error is not None:
            raise self.error
        return self.reply


@pytest.fixture
def run(application):
    return application.launch()


def _ask(application, run, question: str):
    response = application.client.post(
        f"/api/assistant/runs/{run['id']}/question", json={"question": question}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _with_assistant(application, adapter):
    application.client.app.dependency_overrides[deps.get_assistant] = lambda: DefaultAssistant(
        adapter=adapter
    )


# ── the criterion ──────────────────────────────────────────────────────


def test_a_model_that_declines_is_passed_through(application, run) -> None:
    """The cooperative case. No figure, so nothing to verify, so it stands."""
    _with_assistant(
        application,
        _Scripted(reply="Le contexte fourni ne permet pas de répondre à cette question."),
    )

    answer = _ask(application, run, "Combien d'étudiants sont inscrits en L3 ?")

    assert answer["generated"] is True
    assert "ne permet pas de répondre" in answer["text"]


def test_a_model_that_invents_a_figure_is_stopped(application, run) -> None:
    """⚠️ **The clause that carries the requirement.**

    The criterion says the assistant invents no figure. A prompt asking it not
    to is not a guarantee — it is a request. What makes the requirement hold
    is that an answer containing a figure absent from the context is discarded
    whether the model cooperated or not.
    """
    _with_assistant(application, _Scripted(reply="Il y a 425 étudiants concernés."))

    answer = _ask(application, run, "Combien d'étudiants sont inscrits en L3 ?")

    assert answer["generated"] is False
    assert "425" not in answer["text"]
    assert "425" in (answer["fallbackReason"] or "")


def test_the_fallback_says_the_question_was_not_answered(application, run) -> None:
    """⚠️ It must not read as an answer. Silence, or a screen showing only the
    run's figures, would let a reader take the figures FOR the answer."""
    _with_assistant(application, _Scripted(reply="Il y a 425 étudiants concernés."))

    answer = _ask(application, run, "Combien d'étudiants sont inscrits en L3 ?")

    assert "received no written answer" in answer["text"]


def test_with_the_service_off_the_question_is_still_answered_honestly(application, run) -> None:
    """The default configuration. 200, and text that says plainly that no
    answer was written — never a 503, and never silence."""
    answer = _ask(application, run, "Pourquoi ce candidat est-il le premier ?")

    assert answer["generated"] is False
    assert "unavailable or switched off" in answer["text"]
    assert "received no written answer" in answer["text"]


def test_a_service_failure_does_not_reach_the_caller(application, run) -> None:
    _with_assistant(application, _Scripted(error=AssistantUnavailableError("timed out")))

    answer = _ask(application, run, "Pourquoi ?")

    assert answer["generated"] is False
    assert "timed out" in (answer["fallbackReason"] or "")


# ── data minimisation, at the one boundary that carries it ─────────────


def test_the_question_context_carries_no_personal_data(application, run) -> None:
    """The Kaggle archive this project deliberately did not load carries 3,000
    rows of names, e-mail addresses and postal addresses (docs/open-questions.md),
    and `docs/ai-integration.md` requires that no such field ever reach this
    payload.

    Here it holds **by construction** — `RunFacts` has no field that could
    carry one — and this test is what would notice if a field were added.
    """
    adapter = _Scripted(reply="Rien à signaler.")
    _with_assistant(application, adapter)

    _ask(application, run, "Qui enseigne le lundi ?")

    context = adapter.seen[0]
    serialised = repr(context).lower()
    for forbidden in ("@", "email", "mail", "phone", "téléphone", "adresse", "nom "):
        assert forbidden not in serialised, f"{forbidden!r} reached the assistant context"


def test_the_question_reaches_the_model_as_a_label_not_as_a_figure(application, run) -> None:
    adapter = _Scripted(reply="Rien à signaler.")
    _with_assistant(application, adapter)

    _ask(application, run, "Pourquoi 42 ?")

    context = adapter.seen[0]
    assert context.labels["question"] == "Pourquoi 42 ?"


def test_the_context_is_bounded_by_the_run(application, run) -> None:
    """Every candidate's score and sub-scores, and the run's parameters — not
    654 rows of placements, which would swamp the context to serve a question
    that is almost never about one specific session."""
    adapter = _Scripted(reply="Rien à signaler.")
    _with_assistant(application, adapter)

    _ask(application, run, "Quel candidat est le meilleur ?")

    figures = adapter.seen[0].figures
    assert figures["candidate1.score"] == run["candidates"][0]["score"]
    assert not any(key.startswith("placement.") for key in figures)


def test_an_unknown_run_is_404(application) -> None:
    assert (
        application.client.post(
            "/api/assistant/runs/nope/question", json={"question": "Pourquoi ?"}
        ).status_code
        == 404
    )
