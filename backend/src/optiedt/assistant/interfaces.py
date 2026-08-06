"""The AI assistant service.

An adapter around an external language model API. Stateless between calls,
holds NO database credential, reached through a provider-agnostic client, and
switchable off by configuration.

It explains, answers, phrases and reports. It never places a session, never
computes a score, never decides an order. See ADR-006.

May NOT import the persistence layer or the solver — enforced by .importlinter.

⚠️ **`ContextBuilder.build` takes FACTS, not a run id, and the change is not
cosmetic.** The scaffold declared ``build(kind, run_id: str, ...)``, which
cannot be implemented without looking a run up, which needs a store, which is
the database — the exact thing invariant 4 forbids. The signature and the
invariant could not both be honoured, so the signature moved: the caller has
the store and assembles a ``RunFacts``; the assistant looks nothing up.

See docs/ai-integration.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from optiedt.analysis.interfaces import Decomposition
from optiedt.domain.entities import Candidate, CandidateId, ConstraintCode


class RequestKind(StrEnum):
    """The four bounded request types. Each has its own context schema."""

    EXPLAIN_CANDIDATE = "EXPLAIN_CANDIDATE"  # one candidate
    COMPARE_CANDIDATES = "COMPARE_CANDIDATES"  # two candidates
    ANSWER_QUESTION = "ANSWER_QUESTION"  # bounded by the run
    PRODUCE_REPORT = "PRODUCE_REPORT"  # one run


@dataclass(frozen=True, slots=True)
class RunFacts:
    """Everything about one run the assistant may be shown.

    Assembled by the caller — which has the run store — and handed in whole.
    **The assistant never looks anything up**, so this type is the boundary
    invariant 4 draws: what is not in here cannot reach the model, and adding a
    field is a deliberate act rather than a side effect of a query.

    ⚠️ Carries no `Student`, no teacher name and no e-mail address, because
    `Candidate` and the weights do not have them. That is data minimisation
    holding by construction rather than by review — and it matters, since the
    Kaggle archive this project deliberately did not load carries 3,000 rows of
    names, e-mail addresses and postal addresses (docs/open-questions.md).
    """

    run_id: str
    seed: int
    deterministic_budget: float
    model_version: str
    weights: dict[ConstraintCode, float]
    candidates: tuple[Candidate, ...]
    criterion_names: dict[ConstraintCode, str] = field(default_factory=dict)
    """Codes to human labels, from the instance catalogue. Labels only - a
    label is not a figure and is not subject to the grounding check."""

    published: CandidateId | None = None
    decomposition: Decomposition | None = None
    """Set for COMPARE_CANDIDATES. Computed by the analysis layer, never here."""


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

    ⚠️ **`figures` is also the grounding check's whole vocabulary.** A number
    the answer may legitimately state has to be IN here, so leaving a figure
    out does not merely withhold it — it makes any answer mentioning it get
    discarded. That is the safe direction to fail in, and it is why each
    builder adds the counts a sentence would naturally use.
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


class AssistantUnavailableError(Exception):
    """The service could not answer: disabled, unreachable, refused, or timed
    out. Never propagated to a caller — `Assistant` catches it and returns the
    computed form, which is what degraded mode means."""


class AssistantAdapter(Protocol):
    """Provider-agnostic client. One adapter, switchable off by configuration.

    Deliberately typed without reference to any vendor SDK: the specification
    requires the service be reachable through a single interface that can be
    disabled without affecting any other function.
    """

    @property
    def enabled(self) -> bool: ...

    def complete(self, context: ContextPayload, prompt: str, timeout_seconds: float) -> str:
        """Raise `AssistantUnavailableError` rather than returning a message."""
        ...


class ContextBuilder(Protocol):
    """Selects, from facts the caller supplies, only what is needed to answer."""

    def build(
        self,
        kind: RequestKind,
        facts: RunFacts,
        candidate: CandidateId | None = None,
        other: CandidateId | None = None,
        question: str | None = None,
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


@dataclass(frozen=True, slots=True)
class AssistantAnswer:
    """Text, and how it was obtained.

    ⚠️ **`generated` is not decoration.** A reader has to be able to tell a
    sentence a language model wrote from one the application computed, and the
    two are displayed differently for that reason. An answer that fell back —
    because the service is off, failed, or produced an ungrounded figure — is
    the computed form and says so.
    """

    text: str
    generated: bool
    fallback_reason: str | None = None


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

    def explain_candidate(self, facts: RunFacts, candidate: CandidateId) -> AssistantAnswer: ...

    def compare_candidates(
        self, facts: RunFacts, candidate: CandidateId, other: CandidateId
    ) -> AssistantAnswer: ...

    def answer_question(self, facts: RunFacts, question: str) -> AssistantAnswer: ...

    def produce_report(self, facts: RunFacts) -> AssistantAnswer: ...
