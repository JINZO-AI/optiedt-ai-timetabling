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
        return f"Le candidat {candidate_id} ne fait pas partie de l’exécution {facts.run_id}."

    lines = [
        f"Candidat {candidate.id}, profil « {candidate.profile_name} », "
        f"score {candidate.score:.{SCORE_DIGITS}f}/100.",
        f"{len(candidate.placements)} séances placées.",
        "",
        "Sous-scores, valeur mesurée puis valeur normalisée (1 = le meilleur) :",
    ]
    for sub in candidate.sub_scores:
        weight = facts.weights.get(sub.criterion)
        weight_text = "" if weight is None else f", poids {weight}"
        lines.append(
            f"  {_label(facts, sub.criterion)} : {_raw(sub.raw_value)} "
            f"→ {sub.normalised:.{SCORE_DIGITS}f}{weight_text}"
        )
    lines.append("")
    lines.append(
        "Le score est la somme pondérée de ces valeurs normalisées, multipliée par 100. "
        "Il se recalcule à la main."
    )
    return "\n".join(lines)


def compare_candidates(facts: RunFacts, a_id: CandidateId, b_id: CandidateId) -> str:
    """The decomposition, term by term. It IS the score calculation read out."""
    if facts.decomposition is None:
        return (
            f"Aucune décomposition n’a été fournie pour {a_id} et {b_id}. "
            "La comparaison est calculée par la couche d’analyse."
        )

    decomposition = facts.decomposition
    difference = f"{decomposition.score_difference:.{SCORE_DIGITS}f}"
    lines = [
        f"Différence de score entre {decomposition.candidate_a} et "
        f"{decomposition.candidate_b} : {difference} point(s).",
        "",
        "Contribution de chaque critère, 100 × poids × (n(A) − n(B)) :",
    ]
    for contribution in decomposition.contributions:
        lines.append(
            f"  {_label(facts, contribution.criterion)} : "
            f"{contribution.value:.{SCORE_DIGITS}f} "
            f"(poids {contribution.weight}, "
            f"{contribution.normalised_a:.{SCORE_DIGITS}f} contre "
            f"{contribution.normalised_b:.{SCORE_DIGITS}f})"
        )
    lines.append("")
    lines.append(
        "La somme de ces contributions est exactement la différence des scores : "
        "ce n’est pas un résumé du calcul, c’est le calcul."
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
        "Le service de langage est indisponible ou désactivé : cette question n’a pas "
        "reçu de réponse rédigée.",
        "",
        f"Ce qui est connu de l’exécution {facts.run_id} :",
        f"  graine {facts.seed}, budget déterministe {facts.deterministic_budget}, "
        f"modèle {facts.model_version}",
        f"  {len(facts.candidates)} candidat(s) :",
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
        f"Exécution {facts.run_id}",
        f"  graine : {facts.seed}",
        f"  budget déterministe : {facts.deterministic_budget}",
        f"  version du modèle : {facts.model_version}",
        "",
        "Poids en vigueur — un seul vecteur valorise tous les candidats :",
    ]
    for code in sorted(facts.weights):
        lines.append(f"  {_label(facts, code)} : {facts.weights[code]}")

    lines.append("")
    lines.append(f"Candidats ({len(facts.candidates)}), du meilleur au moins bon :")
    for index, candidate in enumerate(facts.candidates):
        published = " — publié" if candidate.id == facts.published else ""
        lines.append(
            f"  {index + 1}. {candidate.id} — {candidate.profile_name} — "
            f"{candidate.score:.{SCORE_DIGITS}f}/100 — "
            f"{len(candidate.placements)} séances placées{published}"
        )

    if facts.published is None:
        lines.append("")
        lines.append("Aucun candidat de cette exécution n’a été publié.")
    return "\n".join(lines)
