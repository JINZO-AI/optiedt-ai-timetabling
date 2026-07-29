"""The AI assistant service.

An adapter around an external language model API. Stateless between calls,
holds NO database credential, reached through a provider-agnostic client, and
switchable off by configuration.

It explains, answers, phrases and reports. It never places a session, never
computes a score, never decides an order. See ADR-006.

May NOT import the persistence layer or the solver — enforced by .importlinter.

See docs/ai-integration.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class RequestKind(StrEnum):
    """The four bounded request types. Each has its own context schema."""

    EXPLAIN_CANDIDATE = "EXPLAIN_CANDIDATE"  # one candidate
    COMPARE_CANDIDATES = "COMPARE_CANDIDATES"  # two candidates
    ANSWER_QUESTION = "ANSWER_QUESTION"  # bounded by the run
    PRODUCE_REPORT = "PRODUCE_REPORT"  # one run


@dataclass(frozen=True, slots=True)
class ContextPayload:
    """What the model receives. Nothing else is sent.

    The context builder assembles only the figures needed to answer:

      EXPLAIN_CANDIDATE   sub-scores, normalised values, weights in force, score
      COMPARE_CANDIDATES  both sets of sub-scores and the contributions
      ANSWER_QUESTION     placements concerned, scores of the run, calendar
      PRODUCE_REPORT      run parameters, all candidates with scores, publication

    DATA MINIMISATION is a requirement, not a courtesy: the payload carries
    aggregated figures, codes and labels. No student name, no teacher email
    address and no personal identifier leaves the institution.
    """

    kind: RequestKind
    figures: dict[str, float]
    identifiers: tuple[str, ...]
    labels: dict[str, str]


@dataclass(frozen=True, slots=True)
class VerificationOutcome:
    """Result of the grounding check.

        numbers(answer) ⊆ numbers(context)

    If the inclusion does not hold, the answer is DISCARDED and the computed
    form is displayed instead. The same fallback applies when the service
    errors or exceeds its timeout.

    Be honest about what this establishes. It detects a figure the model
    invented. It does NOT establish that the rest of the sentence is correct,
    and no requirement depends on it doing so — which is precisely why no
    decision the department must defend rests on this service.
    """

    grounded: bool
    unverified_numbers: tuple[float, ...] = ()


class AssistantAdapter(Protocol):
    """Provider-agnostic client. One adapter, switchable off by configuration.

    Deliberately typed without reference to any vendor SDK: the specification
    requires the service be reachable through a single interface that can be
    disabled without affecting any other function.
    """

    def complete(self, context: ContextPayload, prompt: str, timeout_seconds: float) -> str: ...


class ContextBuilder(Protocol):
    """Selects, from the run, only the figures needed to answer."""

    def build(
        self, kind: RequestKind, run_id: str, question: str | None = None
    ) -> ContextPayload: ...


class AnswerVerifier(Protocol):
    """Checks every numeric token in the answer against the context."""

    def verify(self, answer: str, context: ContextPayload) -> VerificationOutcome: ...


class SuggestionMatcher(Protocol):
    """Maps a phrased suggestion onto the recommendation catalogue.

    A suggestion is not executable in the form the model produces it. Before
    being offered it is matched against the three catalogue actions; one that
    matches nothing is displayed as a REMARK and carries no control to act on it
    (ADR-007).

    Returns a RecommendationAction, or None for a remark.
    """

    def match(self, suggestion: str) -> object | None: ...


class Assistant(Protocol):
    """The service as the application uses it.

    Every method must degrade gracefully. If the service is unreachable,
    refuses, times out, fails the grounding check, or is switched off in
    configuration, the caller receives the COMPUTED FORM instead — and
    generation, scoring, ranking, comparison, regeneration and publication all
    remain available in full. Only text disappears.

    This is an acceptance test (FR-22, FR-25), not an aspiration.
    """

    @property
    def enabled(self) -> bool: ...

    def explain_candidate(self, candidate_id: str) -> str: ...

    def answer_question(self, run_id: str, question: str) -> str: ...

    def produce_report(self, run_id: str) -> str: ...
