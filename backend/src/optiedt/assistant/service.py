"""The assistant as the application uses it.

One shape, applied to all four request kinds:

    build the context  ->  ask the model  ->  CHECK EVERY FIGURE  ->  show it
                              |                      |
                              +-- failed ------------+-- ungrounded
                                          |
                                          v
                                    the computed form

⚠️ **There is no path from a failure to an error the caller must handle.** Every
method returns an `AssistantAnswer`; a caller cannot forget to degrade, because
degrading is what this module does instead of raising. That is invariant 5
expressed as a type rather than as a convention: *everything works with the
assistant switched off, only text disappears.*

⚠️ **An ungrounded answer is discarded whole, not repaired.** Not the sentence
containing the bad figure - the entire answer. A model that invented one number
was not reasoning from the context, and the rest of what it wrote has no better
claim to be true; keeping the parts that happen to contain no digits would be
salvaging prose whose basis has just been shown to be unreliable.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from optiedt.assistant import computed
from optiedt.assistant.adapter import DisabledAdapter
from optiedt.assistant.context import DefaultContextBuilder, UnknownCandidateError
from optiedt.assistant.interfaces import (
    AnswerVerifier,
    AssistantAdapter,
    AssistantAnswer,
    AssistantUnavailableError,
    ContextBuilder,
    ContextPayload,
    RequestKind,
    RunFacts,
)
from optiedt.assistant.verifier import DefaultAnswerVerifier
from optiedt.domain.entities import Candidate, CandidateId, ConstraintCode

if TYPE_CHECKING:
    from optiedt.analysis.interfaces import Decomposition

logger = logging.getLogger(__name__)

_PROMPTS = {
    RequestKind.EXPLAIN_CANDIDATE: (
        "Explique en trois à cinq phrases pourquoi ce candidat obtient ce score "
        "et où sont ses faiblesses."
    ),
    RequestKind.COMPARE_CANDIDATES: (
        "Explique en trois à cinq phrases ce qui distingue ces deux candidats, "
        "en t'appuyant sur les contributions fournies."
    ),
    RequestKind.PRODUCE_REPORT: (
        "Rédige un compte rendu court et lisible de cette exécution et du candidat retenu."
    ),
}


@dataclass(frozen=True, slots=True)
class DefaultAssistant:
    """Implements `Assistant`."""

    adapter: AssistantAdapter = field(default_factory=DisabledAdapter)
    builder: ContextBuilder = field(default_factory=DefaultContextBuilder)
    verifier: AnswerVerifier = field(default_factory=DefaultAnswerVerifier)
    timeout_seconds: float = 10.0

    @property
    def enabled(self) -> bool:
        return self.adapter.enabled

    # ── the four requests ──────────────────────────────────────────────

    def explain_candidate(self, facts: RunFacts, candidate: CandidateId) -> AssistantAnswer:
        return self._answer(
            kind=RequestKind.EXPLAIN_CANDIDATE,
            facts=facts,
            fallback=lambda: computed.explain_candidate(facts, candidate),
            candidate=candidate,
        )

    def compare_candidates(
        self, facts: RunFacts, candidate: CandidateId, other: CandidateId
    ) -> AssistantAnswer:
        return self._answer(
            kind=RequestKind.COMPARE_CANDIDATES,
            facts=facts,
            fallback=lambda: computed.compare_candidates(facts, candidate, other),
            candidate=candidate,
            other=other,
        )

    def answer_question(self, facts: RunFacts, question: str) -> AssistantAnswer:
        return self._answer(
            kind=RequestKind.ANSWER_QUESTION,
            facts=facts,
            fallback=lambda: computed.answer_question(facts, question),
            question=question,
            prompt=(
                "Réponds à la question de l'utilisateur en t'appuyant uniquement sur "
                "le contexte. Si le contexte ne contient pas de quoi répondre, dis-le "
                "et ne propose aucun chiffre.\n\nQuestion : " + question
            ),
        )

    def produce_report(self, facts: RunFacts) -> AssistantAnswer:
        return self._answer(
            kind=RequestKind.PRODUCE_REPORT,
            facts=facts,
            fallback=lambda: computed.produce_report(facts),
        )

    # ── the one path all four take ─────────────────────────────────────

    def _answer(
        self,
        kind: RequestKind,
        facts: RunFacts,
        fallback: Callable[[], str],
        candidate: CandidateId | None = None,
        other: CandidateId | None = None,
        question: str | None = None,
        prompt: str | None = None,
    ) -> AssistantAnswer:
        try:
            context = self.builder.build(
                kind, facts, candidate=candidate, other=other, question=question
            )
        except UnknownCandidateError as exc:
            # A caller error, not a service failure - but it still must not
            # raise: the screen shows the computed form, which says the same
            # thing in the reader's language.
            return AssistantAnswer(text=fallback(), generated=False, fallback_reason=str(exc))

        try:
            text = self.adapter.complete(context, prompt or _PROMPTS[kind], self.timeout_seconds)
        except AssistantUnavailableError as exc:
            return AssistantAnswer(text=fallback(), generated=False, fallback_reason=str(exc))

        outcome = self.verifier.verify(text, context)
        if not outcome.grounded:
            # ⚠️ Logged, because a service that regularly invents figures is a
            # fact about the deployment its operator needs, and a silent
            # fallback looks exactly like a service nobody turned on.
            logger.warning(
                "assistant answer discarded: %s not present in the context for run %s",
                outcome.unverified_numbers,
                facts.run_id,
            )
            return AssistantAnswer(
                text=fallback(),
                generated=False,
                fallback_reason=(
                    "the answer contained figures absent from the context "
                    f"({', '.join(str(n) for n in outcome.unverified_numbers)}), "
                    "so it was discarded"
                ),
            )

        return AssistantAnswer(text=text, generated=True)


def assistant_from_settings(
    enabled: bool, base_url: str, api_key: str, model: str, timeout_seconds: float
) -> DefaultAssistant:
    """Built from configuration, in one place.

    ⚠️ `enabled` is checked HERE rather than inside the adapter, so that
    switching the service off produces the `DisabledAdapter` - which cannot
    reach the network at all - instead of a configured adapter that merely
    declines. Off means off.
    """
    from optiedt.assistant.adapter import HttpAssistantAdapter

    adapter: AssistantAdapter = (
        HttpAssistantAdapter(base_url=base_url, api_key=api_key, model=model)
        if enabled
        else DisabledAdapter()
    )
    return DefaultAssistant(adapter=adapter, timeout_seconds=timeout_seconds)


def facts_from_run(
    run_id: str,
    seed: int,
    deterministic_budget: float,
    model_version: str,
    weights: dict[ConstraintCode, float],
    candidates: Iterable[Candidate],
    criterion_names: dict[ConstraintCode, str] | None = None,
    published: CandidateId | None = None,
    decomposition: Decomposition | None = None,
) -> RunFacts:
    """Assemble `RunFacts` from what a caller already holds.

    Here rather than in `api/` or `services/` so that the SHAPE of what may
    reach the model is decided inside the assistant package, where invariant 4
    is the local concern - while the LOOKUP stays outside it, where the store
    is. A caller passes values; it never passes a connection.
    """
    return RunFacts(
        run_id=run_id,
        seed=seed,
        deterministic_budget=deterministic_budget,
        model_version=model_version,
        weights=dict(weights),
        candidates=tuple(candidates),
        criterion_names=dict(criterion_names or {}),
        published=published,
        decomposition=decomposition,
    )


__all__ = [
    "ContextPayload",
    "DefaultAssistant",
    "assistant_from_settings",
    "facts_from_run",
]
