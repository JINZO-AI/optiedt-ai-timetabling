"""The computed form: what the reader gets when no model speaks.

⚠️ **This is not a placeholder, and it is not "the degraded case".** It is the
default configuration — `assistant_enabled` is False out of the box — so this
text is what the application shows unless somebody deliberately turns a
language model on. It is also what is shown when the service fails, times out,
or returns a figure the grounding check rejects.

Invariant 5 in one file: *everything works with the assistant switched off,
only text disappears.* What disappears is the PROSE; the figures are all here,
because they were computed by `analysis/` either way.

⚠️ **Nothing here computes anything.** Every number is read out of `RunFacts`,
which the analysis layer produced. This module formats; it does not derive. A
mean, a percentage or a difference calculated here would be the assistant
producing a figure of its own — invariant 4 — even though no model is involved,
because the figure would then exist in only one place and be unverifiable
against the score the screen shows.
"""

from __future__ import annotations

from optiedt.assistant.interfaces import RunFacts
from optiedt.domain.entities import Candidate, CandidateId

SCORE_DIGITS = 3
"""Matches ComparisonScreen's COMPARISON_DIGITS. Two figures about the same
candidate shown at different precisions on two screens is how a reader
concludes the application cannot add up."""


def _candidate(facts: RunFacts, candidate_id: CandidateId) -> Candidate | None:
    return next((c for c in facts.candidates if c.id == candidate_id), None)


def _label(facts: RunFacts, code: str) -> str:
    name = facts.criterion_names.get(code)
    return f"{code} ({name})" if name else code


def _raw(value: float) -> str:
    """A measured value as the rest of the interface renders it.

    ⚠️ Found by looking at the running application rather than by a test: S6's
    raw value printed as `1.9183673469387754` here while the comparison table
    two panels above showed `1.92` for the same figure. Nothing was wrong with
    either, and the page still looked like two parts of one application
    disagreeing about a number.

    Matches `ComparisonScreen`'s rule exactly - integers whole, everything else
    to two decimals - because the same figure must read the same way wherever
    it appears.
    """
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"


def explain_candidate(facts: RunFacts, candidate_id: CandidateId) -> str:
    """The sub-scores, in the order the analysis layer reported them."""
    candidate = _candidate(facts, candidate_id)
    if candidate is None:
        return f"Candidate {candidate_id} is not part of run {facts.run_id}."

    lines = [
        f"Candidate {candidate.id}, profile \u201c{candidate.profile_name}\u201d, "
        f"score {candidate.score:.{SCORE_DIGITS}f}/100.",
        f"{len(candidate.placements)} sessions placed.",
        "",
        "Sub-scores, measured value then normalised value (1 = best):",
    ]
    for sub in candidate.sub_scores:
        weight = facts.weights.get(sub.criterion)
        weight_text = "" if weight is None else f", weight {weight}"
        lines.append(
            f"  {_label(facts, sub.criterion)} : {_raw(sub.raw_value)} "
            f"→ {sub.normalised:.{SCORE_DIGITS}f}{weight_text}"
        )
    lines.append("")
    lines.append(
        "The score is the weighted sum of these normalised values, multiplied by 100. "
        "It can be recomputed by hand."
    )
    return "\n".join(lines)


def compare_candidates(facts: RunFacts, a_id: CandidateId, b_id: CandidateId) -> str:
    """The decomposition, term by term. It IS the score calculation read out."""
    if facts.decomposition is None:
        return (
            f"No decomposition was supplied for {a_id} and {b_id}. "
            "The comparison is computed by the analysis layer."
        )

    decomposition = facts.decomposition
    difference = f"{decomposition.score_difference:.{SCORE_DIGITS}f}"
    lines = [
        f"Score difference between {decomposition.candidate_a} and "
        f"{decomposition.candidate_b}: {difference} point(s).",
        "",
        "Contribution of each criterion, 100 x weight x (n(A) - n(B)):",
    ]
    for contribution in decomposition.contributions:
        lines.append(
            f"  {_label(facts, contribution.criterion)} : "
            f"{contribution.value:.{SCORE_DIGITS}f} "
            f"(weight {contribution.weight}, "
            f"{contribution.normalised_a:.{SCORE_DIGITS}f} against "
            f"{contribution.normalised_b:.{SCORE_DIGITS}f})"
        )
    lines.append("")
    lines.append(
        "These contributions sum exactly to the difference in score: this is not a "
        "summary of the calculation, it is the calculation."
    )
    return "\n".join(lines)


def answer_question(facts: RunFacts, question: str) -> str:
    """⚠️ It does NOT answer the question, and says so.

    Answering a question in ordinary language is the one thing here that needs
    a language model. With none available the honest response is to say the
    question was not answered and show what is known — never to guess, and
    never to stay silent in a way that reads as an answer.
    """
    del question  # Recorded by the caller; repeating it here answers nothing.
    lines = [
        "The language service is unavailable or switched off, so this question "
        "received no written answer.",
        "",
        f"What is known about run {facts.run_id}:",
        f"  seed {facts.seed}, search budget {facts.deterministic_budget}, "
        f"model {facts.model_version}",
        f"  {len(facts.candidates)} candidate(s):",
    ]
    for candidate in facts.candidates:
        lines.append(
            f"    {candidate.id} — {candidate.profile_name} — "
            f"{candidate.score:.{SCORE_DIGITS}f}/100"
        )
    return "\n".join(lines)


def produce_report(facts: RunFacts) -> str:
    """The run, its candidates and its publication — the report's own figures.

    PPM §8.3 makes this the FIRST thing cut under time pressure, with
    explanations and answers kept. Cutting the model's prose leaves this, which
    is why the reduction is survivable at all.
    """
    lines = [
        f"Run {facts.run_id}",
        f"  seed: {facts.seed}",
        f"  search budget: {facts.deterministic_budget}",
        f"  model version: {facts.model_version}",
        "",
        "Weights in force - one vector prices every candidate:",
    ]
    for code in sorted(facts.weights):
        lines.append(f"  {_label(facts, code)} : {facts.weights[code]}")

    lines.append("")
    lines.append(f"Candidates ({len(facts.candidates)}), best first:")
    for index, candidate in enumerate(facts.candidates):
        published = " - published" if candidate.id == facts.published else ""
        lines.append(
            f"  {index + 1}. {candidate.id} — {candidate.profile_name} — "
            f"{candidate.score:.{SCORE_DIGITS}f}/100 — "
            f"{len(candidate.placements)} sessions placed{published}"
        )

    if facts.published is None:
        lines.append("")
        lines.append("No candidate from this run has been published.")
    return "\n".join(lines)
