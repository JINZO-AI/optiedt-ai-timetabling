"""What the model is shown, and nothing else.

Two jobs, and the second is easy to miss:

1. **Data minimisation.** The payload carries aggregated figures, codes and
   labels. No student name, no teacher e-mail address, no personal identifier.
   Here that holds by construction rather than by review — `RunFacts` has no
   field that could carry one.

2. **Supplying the grounding check's vocabulary.** `numbers(answer)` must be a
   subset of `numbers(context)`, so a figure a sentence would naturally state
   has to be in `figures` or the whole answer is discarded. Each builder below
   therefore adds the COUNTS a sentence uses ("the three candidates", "218
   sessions") and not only the scores. Leaving one out fails safe - the answer
   is thrown away rather than shown ungrounded - but it fails.

⚠️ **Rounded forms are included deliberately.** A model given 79.8163 writes
"79.82" far more often than it writes the full value, and a check that
discarded every such answer would leave the feature permanently in fallback.
So each score is published at full precision AND at the two precisions the
interface itself displays. This is a decision about what "the figure appears in
the context" means, not a loosening of the check: 79.82 IS the displayed form
of that score, and the screen shows exactly that.
"""

from __future__ import annotations

from dataclasses import dataclass

from optiedt.assistant.interfaces import ContextPayload, RequestKind, RunFacts
from optiedt.domain.entities import Candidate, CandidateId

DISPLAY_PRECISIONS = (2, 3)
"""What the interface itself renders. ComparisonScreen uses 3 for scores and
contributions, the candidate list uses 2. A model that quotes either is
quoting the screen."""


class UnknownCandidateError(Exception):
    """The candidate is not part of the run whose facts were supplied."""


@dataclass(frozen=True, slots=True)
class DefaultContextBuilder:
    """Implements `ContextBuilder`."""

    def build(
        self,
        kind: RequestKind,
        facts: RunFacts,
        candidate: CandidateId | None = None,
        other: CandidateId | None = None,
        question: str | None = None,
    ) -> ContextPayload:
        if kind is RequestKind.EXPLAIN_CANDIDATE:
            return self._explain(facts, _require(facts, candidate))
        if kind is RequestKind.COMPARE_CANDIDATES:
            return self._compare(facts, _require(facts, candidate), _require(facts, other))
        if kind is RequestKind.ANSWER_QUESTION:
            return self._question(facts, question or "")
        return self._report(facts)

    # ── one candidate ──────────────────────────────────────────────────

    def _explain(self, facts: RunFacts, candidate: Candidate) -> ContextPayload:
        figures = _run_figures(facts)
        figures.update(_candidate_figures(candidate, prefix=""))
        for code, weight in facts.weights.items():
            figures[f"weight.{code}"] = weight
        return ContextPayload(
            kind=RequestKind.EXPLAIN_CANDIDATE,
            figures=_with_display_forms(figures),
            identifiers=(facts.run_id, candidate.id, candidate.profile_name),
            labels=_labels(facts),
        )

    # ── two candidates ─────────────────────────────────────────────────

    def _compare(self, facts: RunFacts, a: Candidate, b: Candidate) -> ContextPayload:
        figures = _run_figures(facts)
        figures.update(_candidate_figures(a, prefix="a."))
        figures.update(_candidate_figures(b, prefix="b."))
        for code, weight in facts.weights.items():
            figures[f"weight.{code}"] = weight

        # The decomposition is computed by analysis/ranking.py and passed in.
        # ⚠️ It is NOT recomputed here: the assistant may not produce a figure
        # of its own, and re-deriving one is producing it (invariant 4).
        if facts.decomposition is not None:
            figures["score.difference"] = facts.decomposition.score_difference
            for contribution in facts.decomposition.contributions:
                figures[f"contribution.{contribution.criterion}"] = contribution.value

        return ContextPayload(
            kind=RequestKind.COMPARE_CANDIDATES,
            figures=_with_display_forms(figures),
            identifiers=(facts.run_id, a.id, b.id, a.profile_name, b.profile_name),
            labels=_labels(facts),
        )

    # ── a question about the run ───────────────────────────────────────

    def _question(self, facts: RunFacts, question: str) -> ContextPayload:
        """Bounded by the run: every candidate's score and sub-scores, and the
        run's own parameters. Not the placements of all three - 654 rows of
        (session, slot, room) would swamp the context to answer a question that
        is almost never about one specific session.

        ⚠️ A question the context cannot answer is the POINT of FR-24's
        acceptance criterion, not a gap: the assistant must say it cannot
        answer and invent no figure. Widening the context to make more
        questions answerable would not change that requirement.
        """
        figures = _run_figures(facts)
        for index, candidate in enumerate(facts.candidates):
            figures.update(_candidate_figures(candidate, prefix=f"candidate{index + 1}."))
        for code, weight in facts.weights.items():
            figures[f"weight.{code}"] = weight

        labels = _labels(facts)
        labels["question"] = question
        return ContextPayload(
            kind=RequestKind.ANSWER_QUESTION,
            figures=_with_display_forms(figures),
            identifiers=(facts.run_id, *(c.id for c in facts.candidates)),
            labels=labels,
        )

    # ── a report on the run ────────────────────────────────────────────

    def _report(self, facts: RunFacts) -> ContextPayload:
        figures = _run_figures(facts)
        for index, candidate in enumerate(facts.candidates):
            figures.update(_candidate_figures(candidate, prefix=f"candidate{index + 1}."))
        for code, weight in facts.weights.items():
            figures[f"weight.{code}"] = weight

        labels = _labels(facts)
        if facts.published is not None:
            labels["published"] = facts.published
        return ContextPayload(
            kind=RequestKind.PRODUCE_REPORT,
            figures=_with_display_forms(figures),
            identifiers=(
                facts.run_id,
                *(c.id for c in facts.candidates),
                *((facts.published,) if facts.published is not None else ()),
            ),
            labels=labels,
        )


# ── shared assembly ────────────────────────────────────────────────────


def _require(facts: RunFacts, candidate_id: CandidateId | None) -> Candidate:
    for candidate in facts.candidates:
        if candidate.id == candidate_id:
            return candidate
    raise UnknownCandidateError(
        f"candidate {candidate_id!r} is not among run {facts.run_id!r}'s "
        f"{len(facts.candidates)} candidates. The assistant is shown one run's "
        "facts and looks nothing up."
    )


def _run_figures(facts: RunFacts) -> dict[str, float]:
    """The run's own parameters, and the counts a sentence would use."""
    return {
        "run.seed": float(facts.seed),
        "run.deterministicBudget": facts.deterministic_budget,
        "run.candidateCount": float(len(facts.candidates)),
        "run.criterionCount": float(len(facts.weights)),
    }


def _candidate_figures(candidate: Candidate, prefix: str) -> dict[str, float]:
    figures: dict[str, float] = {
        f"{prefix}score": candidate.score,
        f"{prefix}placementCount": float(len(candidate.placements)),
    }
    for sub in candidate.sub_scores:
        figures[f"{prefix}raw.{sub.criterion}"] = sub.raw_value
        figures[f"{prefix}normalised.{sub.criterion}"] = sub.normalised
    return figures


def _labels(facts: RunFacts) -> dict[str, str]:
    labels = {f"criterion.{code}": name for code, name in facts.criterion_names.items()}
    labels["modelVersion"] = facts.model_version
    return labels


def _with_display_forms(figures: dict[str, float]) -> dict[str, float]:
    """Each figure, plus the forms the interface actually renders.

    See the module docstring: this decides what "the figure appears in the
    context" means. It does not weaken the check - a number the answer states
    still has to BE one of these - it only admits the rounding the screen
    itself performs.
    """
    enriched = dict(figures)
    for key, value in figures.items():
        for digits in DISPLAY_PRECISIONS:
            rounded = round(value, digits)
            if rounded != value:
                enriched[f"{key}~{digits}"] = rounded
    return enriched
