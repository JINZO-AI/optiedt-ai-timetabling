"""The assistant: what reaches the model, what comes back, and what is refused.

Three properties carry FR-22, and each is one of the project's invariants:

- **Invariant 4** — the assistant receives a payload, never a database, and
  produces no figure of its own. Tested by checking what the context CONTAINS
  and by checking that a fabricated figure is thrown away.
- **Invariant 5** — everything works with it switched off. Tested by the
  DEFAULT configuration, because `assistant_enabled` is False out of the box.
- **C-21** — no test calls a live provider. Every adapter here is a fake, and
  the fakes can be made to do things a real model only does occasionally, which
  is what makes them the better instrument.

⚠️ **What none of this establishes is that any real provider works.** It
establishes the application's behaviour AROUND one. A first live call is a
deployment step (`docs/demonstration.md`), not a test.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field

import pytest

from optiedt.analysis.interfaces import Contribution, Decomposition
from optiedt.assistant.adapter import DisabledAdapter, HttpAssistantAdapter
from optiedt.assistant.context import DefaultContextBuilder, UnknownCandidateError
from optiedt.assistant.interfaces import (
    AssistantUnavailableError,
    ContextPayload,
    RequestKind,
    RunFacts,
)
from optiedt.assistant.service import DefaultAssistant, assistant_from_settings, facts_from_run
from optiedt.assistant.verifier import DefaultAnswerVerifier
from optiedt.domain.entities import Candidate, Placement, SubScore

WEIGHTS = {"S2": 0.15, "S3": 0.15, "S10": 0.0}


def _candidate(cid: str = "c1", score: float = 79.8163) -> Candidate:
    return Candidate(
        id=cid,
        run="r1",
        profile_name="balanced",
        cost=42,
        score=score,
        placements=(Placement("S0001", 7, "2"), Placement("S0002", 3, "4")),
        sub_scores=(
            SubScore(criterion="S2", raw_value=65.0, normalised=0.869),
            SubScore(criterion="S3", raw_value=22.0, normalised=0.953),
            SubScore(criterion="S10", raw_value=104.0, normalised=0.411),
        ),
    )


def _facts(**overrides) -> RunFacts:
    base = {
        "run_id": "r1",
        "seed": 42,
        "deterministic_budget": 90.0,
        "model_version": "weekly.h1-h12.s2-s10",
        "weights": WEIGHTS,
        "candidates": (_candidate(), _candidate("c2", 79.7943)),
        "criterion_names": {"S2": "Temps mort étudiant", "S3": "Temps mort enseignant"},
    }
    base.update(overrides)
    return RunFacts(**base)  # type: ignore[arg-type]


@dataclass
class ScriptedAdapter:
    """A fake that says exactly what a test needs a model to say.

    ⚠️ **Better than a real model here, not a compromise.** The failure the
    grounding check exists to catch is a fabricated figure, and a fake can
    fabricate one on demand while a real model can only be HOPED to on the day
    the suite runs (C-21).
    """

    reply: str = "Le candidat obtient 79.816 sur 100."
    error: Exception | None = None
    enabled_value: bool = True
    seen: list[ContextPayload] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)

    @property
    def enabled(self) -> bool:
        return self.enabled_value

    def complete(self, context: ContextPayload, prompt: str, timeout_seconds: float) -> str:
        del timeout_seconds
        self.seen.append(context)
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.reply


# ── invariant 5: it works switched off, and that is the DEFAULT ────────


def test_the_default_assistant_is_disabled():
    """`assistant_enabled` is False out of the box, so degraded mode is the
    ordinary configuration rather than a special one."""
    assert DefaultAssistant().enabled is False


def test_switched_off_it_returns_the_computed_form_with_every_figure():
    answer = DefaultAssistant().explain_candidate(_facts(), "c1")

    assert answer.generated is False
    assert "79.816" in answer.text
    assert "0.869" in answer.text and "0.953" in answer.text
    assert "Temps mort étudiant" in answer.text


def test_a_raw_value_reads_the_same_here_as_on_the_comparison_screen():
    """⚠️ Found by looking at the running application, not by a test.

    S6's raw value printed as `1.9183673469387754` while the comparison table
    two panels above showed `1.92` for the same figure. Neither was wrong and
    the page still looked like two parts of one application disagreeing about
    a number.
    """
    facts = _facts(
        candidates=(
            Candidate(
                id="c1",
                run="r1",
                profile_name="balanced",
                cost=1,
                score=80.0,
                placements=(),
                sub_scores=(
                    SubScore(criterion="S6", raw_value=1.9183673469387754, normalised=0.848),
                    SubScore(criterion="S2", raw_value=4.0, normalised=0.994),
                ),
            ),
        )
    )

    text = DefaultAssistant().explain_candidate(facts, "c1").text

    assert "S6 : 1.92 " in text
    assert "1.9183673469387754" not in text
    assert ") : 4 " in text, "an integer raw value must stay whole, not become 4.00"


def test_switched_off_it_says_why_rather_than_failing_silently():
    answer = DefaultAssistant().explain_candidate(_facts(), "c1")
    assert answer.fallback_reason is not None
    assert "switched off" in answer.fallback_reason


def test_settings_that_disable_it_produce_an_adapter_that_cannot_reach_a_network():
    """Off means off: a DisabledAdapter, not a configured one that declines."""
    assistant = assistant_from_settings(
        enabled=False,
        base_url="https://example.invalid",
        api_key="k",
        model="m",
        timeout_seconds=1.0,
    )
    assert isinstance(assistant.adapter, DisabledAdapter)


def test_settings_that_enable_it_produce_the_http_adapter():
    assistant = assistant_from_settings(
        enabled=True,
        base_url="https://example.invalid",
        api_key="k",
        model="m",
        timeout_seconds=1.0,
    )
    assert isinstance(assistant.adapter, HttpAssistantAdapter)


def test_an_enabled_but_unconfigured_adapter_is_not_enabled():
    assert HttpAssistantAdapter(base_url="", api_key="", model="").enabled is False


def test_the_adapter_identifies_itself_rather_than_sending_the_urllib_default(monkeypatch):
    """The request must carry a `User-Agent` that is not `Python-urllib`.

    ⚠️ **Not a cosmetic header.** `urllib` sends `Python-urllib/<version>` when
    none is given, and a CDN-fronted provider refuses that value before the
    request reaches the API - Groq answers HTTP 403 / Cloudflare `error code:
    1010`, which names neither the key nor the model and so reads like an
    authentication fault it is not. That refusal is what left FR-24's first live
    call unable to obtain any answer at all.

    **No live provider is called here (C-21).** `urlopen` is intercepted, so
    what is pinned is the request this module BUILDS, which is the part that was
    wrong - a live call would test the provider's mood instead.
    """
    seen: dict[str, str] = {}

    class _Response:
        def read(self) -> bytes:
            return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    def _fake_urlopen(request, timeout):
        del timeout
        seen.update(request.headers)
        return _Response()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    adapter = HttpAssistantAdapter(base_url="https://example.invalid", api_key="k", model="m")
    adapter.complete(
        ContextPayload(kind=RequestKind.EXPLAIN_CANDIDATE, figures={}, identifiers=(), labels={}),
        "prompt",
        1.0,
    )

    # urllib title-cases header names when they are set through Request(headers=...).
    agent = seen.get("User-agent") or seen.get("User-Agent")
    assert agent, "the adapter sent no User-Agent, so urllib would supply its own"
    assert "python-urllib" not in agent.lower()


# ── invariant 4: the context is the whole boundary ─────────────────────


def test_the_context_carries_figures_codes_and_labels_and_nothing_else():
    context = DefaultContextBuilder().build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")

    assert context.kind is RequestKind.EXPLAIN_CANDIDATE
    assert all(isinstance(v, float) for v in context.figures.values())
    assert all(isinstance(v, str) for v in context.labels.values())
    assert "c1" in context.identifiers


def test_the_context_carries_the_score_and_every_sub_score():
    figures = (
        DefaultContextBuilder()
        .build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
        .figures
    )

    assert figures["score"] == 79.8163
    assert figures["normalised.S2"] == 0.869
    assert figures["raw.S3"] == 22.0
    assert figures["weight.S10"] == 0.0


def test_the_context_carries_the_counts_a_sentence_would_use():
    """Not decoration: a figure the answer may legitimately state has to be in
    the context, so omitting a count makes any answer mentioning it get
    discarded."""
    figures = (
        DefaultContextBuilder()
        .build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
        .figures
    )

    assert figures["run.candidateCount"] == 2.0
    assert figures["placementCount"] == 2.0
    assert figures["run.seed"] == 42.0


def test_the_context_publishes_the_precisions_the_interface_displays():
    """A model given 79.8163 writes "79.82" far more often than the full value.
    The screen shows exactly that, so it is the figure, not a rounding
    allowance smuggled into the check."""
    figures = (
        DefaultContextBuilder()
        .build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
        .figures
    )

    assert 79.82 in figures.values()
    assert 79.816 in figures.values()


def test_a_candidate_outside_the_run_is_refused_rather_than_guessed():
    with pytest.raises(UnknownCandidateError, match="is not among run"):
        DefaultContextBuilder().build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="nope")


def test_the_comparison_context_carries_the_decomposition_it_was_given():
    """⚠️ GIVEN, never recomputed. Re-deriving a contribution here would be the
    assistant producing a figure of its own - invariant 4 - and the two
    derivations would then be free to disagree."""
    decomposition = Decomposition(
        candidate_a="c1",
        candidate_b="c2",
        score_difference=0.022,
        contributions=(
            Contribution(
                criterion="S2", weight=0.15, normalised_a=0.869, normalised_b=0.860, value=0.135
            ),
        ),
    )
    figures = (
        DefaultContextBuilder()
        .build(
            RequestKind.COMPARE_CANDIDATES,
            _facts(decomposition=decomposition),
            candidate="c1",
            other="c2",
        )
        .figures
    )

    assert figures["score.difference"] == 0.022
    assert figures["contribution.S2"] == 0.135


def test_the_question_is_carried_as_a_label_not_as_a_figure():
    context = DefaultContextBuilder().build(
        RequestKind.ANSWER_QUESTION, _facts(), question="Pourquoi ce candidat ?"
    )
    assert context.labels["question"] == "Pourquoi ce candidat ?"


# ── the grounding check ────────────────────────────────────────────────


def test_an_answer_quoting_only_context_figures_is_grounded():
    context = DefaultContextBuilder().build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
    outcome = DefaultAnswerVerifier().verify("Le score est 79.816, S3 vaut 0.953.", context)
    assert outcome.grounded


def test_an_answer_inventing_a_figure_is_not_grounded_and_names_it():
    context = DefaultContextBuilder().build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
    outcome = DefaultAnswerVerifier().verify("Le score est 88.4 sur 100.", context)
    assert not outcome.grounded
    assert 88.4 in outcome.unverified_numbers


def test_a_french_decimal_comma_is_read_as_a_decimal_point():
    """The interface is French and a model writing French produces "79,816".
    Reading that as 79816 would fail a correctly-grounded answer."""
    context = DefaultContextBuilder().build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
    assert DefaultAnswerVerifier().verify("Le score est 79,816.", context).grounded


def test_identifiers_containing_digits_are_not_read_as_figures():
    """S0001, S3, r1 - a digit inside an identifier is not a number the answer
    is claiming, and treating it as one would discard almost every answer."""
    context = DefaultContextBuilder().build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
    assert (
        DefaultAnswerVerifier()
        .verify("Le critère S2 du candidat c1 de l'exécution r1 vaut 0.869.", context)
        .grounded
    )


def test_an_answer_with_no_figure_at_all_is_grounded():
    """Vacuously, and correctly: the check is about invented FIGURES."""
    context = DefaultContextBuilder().build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
    assert DefaultAnswerVerifier().verify("Ce candidat est équilibré.", context).grounded


@pytest.mark.parametrize("invented", ["4271", "1000", "218", "99999"])
def test_an_ungrouped_number_above_999_is_seen(invented):
    """⚠️ **The regression that matters most in this file.**

    The first pattern was `\\d{1,3}(?:[ ]\\d{3})*` - up to three digits, then
    optional space-grouped triples. On `4271` it matched `427`, the trailing
    boundary failed on the `1`, every shorter attempt failed the same way, and
    every later start was refused by the leading boundary. **The number
    produced no match at all**, so the answer passed as grounded.

    A verifier that cannot SEE a number cannot reject it, and the hole sat
    exactly where an invented figure is most plausible - counts of minutes, of
    periods, of sessions. Found by the FR-22 acceptance test, not by review.
    """
    context = DefaultContextBuilder().build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
    outcome = DefaultAnswerVerifier().verify(f"Il reste {invented} minutes.", context)

    assert not outcome.grounded
    assert float(invented) in outcome.unverified_numbers


def test_a_space_grouped_thousand_is_read_as_one_number():
    """ "1 000" is one figure, not 1 and then 0."""
    context = DefaultContextBuilder().build(RequestKind.EXPLAIN_CANDIDATE, _facts(), candidate="c1")
    outcome = DefaultAnswerVerifier().verify("Il reste 1 000 minutes.", context)

    assert outcome.unverified_numbers == (1000.0,)


# ── the service: failure always becomes the computed form ──────────────


def test_a_grounded_answer_is_returned_as_generated():
    adapter = ScriptedAdapter(reply="Score de 79.816, avec S3 à 0.953.")
    answer = DefaultAssistant(adapter=adapter).explain_candidate(_facts(), "c1")

    assert answer.generated is True
    assert answer.text == "Score de 79.816, avec S3 à 0.953."
    assert answer.fallback_reason is None


def test_an_ungrounded_answer_is_discarded_whole():
    """⚠️ Not the offending sentence - the entire answer. A model that invented
    one number was not reasoning from the context, and the rest of what it
    wrote has no better claim to be true."""
    adapter = ScriptedAdapter(reply="Le score est 79.816. Il y a 12 conflits résiduels.")
    answer = DefaultAssistant(adapter=adapter).explain_candidate(_facts(), "c1")

    assert answer.generated is False
    assert "conflits résiduels" not in answer.text
    assert "79.816" in answer.text  # the computed form, which has the real figures
    assert answer.fallback_reason is not None and "12" in answer.fallback_reason


def test_a_service_failure_becomes_the_computed_form():
    adapter = ScriptedAdapter(error=AssistantUnavailableError("timed out after 10s"))
    answer = DefaultAssistant(adapter=adapter).explain_candidate(_facts(), "c1")

    assert answer.generated is False
    assert "timed out" in (answer.fallback_reason or "")


def test_an_unknown_candidate_never_raises_out_of_the_service():
    """A caller error still must not break the screen: invariant 5 says only
    text disappears, and an exception is not text disappearing."""
    answer = DefaultAssistant(adapter=ScriptedAdapter()).explain_candidate(_facts(), "nope")

    assert answer.generated is False
    assert "is not part of run" in answer.text


def test_the_model_is_told_it_may_not_compute_or_rank():
    """The prompt is part of the guarantee, even though it is not what enforces
    it - the grounding check is. Both, because a prompt that asked for a
    ranking would make the check reject far more answers."""
    adapter = ScriptedAdapter()
    DefaultAssistant(adapter=adapter).explain_candidate(_facts(), "c1")

    from optiedt.assistant.adapter import _SYSTEM_PROMPT

    # Whitespace-normalised: the prompt is wrapped for reading, so a phrase can
    # straddle a line break and a naive `in` would fail on correct text.
    prompt = " ".join(_SYSTEM_PROMPT.split())
    assert "compute no score" in prompt
    assert "decide no ranking" in prompt
    assert "place no session" in prompt
    # ⚠️ The prompt is written in English since the interface was translated;
    # the three prohibitions are what this test is about and they are unchanged.
    assert "Answer in English" in prompt


def test_the_adapter_receives_the_context_and_never_the_facts():
    """Invariant 4 at the one place it could be broken by accident."""
    adapter = ScriptedAdapter()
    DefaultAssistant(adapter=adapter).explain_candidate(_facts(), "c1")

    assert len(adapter.seen) == 1
    assert isinstance(adapter.seen[0], ContextPayload)


# ── the helper that assembles facts ────────────────────────────────────


def test_facts_from_run_copies_rather_than_aliasing():
    """The caller holds a RunRecord; a RunFacts that aliased its weights dict
    would let a later mutation change what a past request was shown."""
    weights = dict(WEIGHTS)
    facts = facts_from_run(
        run_id="r1",
        seed=42,
        deterministic_budget=90.0,
        model_version="v",
        weights=weights,
        candidates=[_candidate()],
    )
    weights["S2"] = 99.0

    assert facts.weights["S2"] == 0.15
