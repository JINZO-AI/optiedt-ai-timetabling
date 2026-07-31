"""Ranker: orders candidates, decomposes score differences, detects dominance.

Constructed with the weights IN FORCE for one run, cached at construction the
same way each Criterion in criteria.py caches its Instance - neither
``rank()`` nor ``decompose()`` takes a weights argument (unlike
``Scorer.score()``, which does), so a Ranker is the natural place to hold it.

Why one shared weight vector rather than each candidate's own producing
profile: the three weight profiles (balanced, student-favouring,
teacher-favouring) exist to steer the SOLVER toward diverse placements
(docs/constraint-model.md, "Weight profiles and the portfolio") - they are
not, by themselves, a valid basis for comparing the resulting candidates,
because the decomposition identity

    score(A) - score(B) = 100 * sum(w_i * (n_i(A) - n_i(B)))

only holds when the SAME w_i prices both candidates. Comparing two
candidates under their own two different profiles would need two different
w_i and the identity would not hold. So every candidate of a run is scored
and ranked here against one reference vector - the weights in force
(docs/scoring-and-explanation.md) - regardless of which profile's objective
produced its placements; profile_name on Candidate is kept only as
provenance of how the placement was obtained.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from optiedt.analysis.interfaces import (
    Contribution,
    Decomposition,
    DominanceVerdict,
    Recommendation,
    Scorer,
)
from optiedt.analysis.scoring import DefaultScorer, renormalised
from optiedt.domain.entities import Candidate, ConstraintCode

# Tie-break priority when scores are equal: catalogue default weight,
# descending (S2 .25, S5 .20, S3 .15, S4/S6/S7 .10, S10 0), ties among equal
# defaults broken by code. See docs/scoring-and-explanation.md, "Ordering".
TIE_BREAK_ORDER: tuple[ConstraintCode, ...] = ("S2", "S5", "S3", "S4", "S6", "S7", "S10")

RECOMMENDATION_RULE = "highest score under the weights in force"
"""The entire rule behind a recommendation, FR-16.

A constant, not a formatted string, because docs/scoring-and-explanation.md
makes checkability the point: "'recommended because it has the highest score
under the weights in force' is a sentence the department can check." A rule
that varied per candidate would not be one rule the department could check
once - it would be a caption.
"""


def _sub_scores_by_code(candidate: Candidate) -> dict[ConstraintCode, float]:
    return {s.criterion: s.normalised for s in candidate.sub_scores}


@dataclass(frozen=True, slots=True)
class DefaultRanker:
    """Implements the ``Ranker`` protocol against one fixed weight vector."""

    weights: dict[ConstraintCode, float]
    scorer: Scorer = field(default_factory=DefaultScorer)

    def rank(self, candidates: list[Candidate]) -> list[Candidate]:
        """Decreasing score; ties broken by TIE_BREAK_ORDER, then by id for a
        total order that cannot depend on input order (the tested
        invariance-of-order property).

        Sorted by id first and by score/tie-break second, relying on
        ``sorted``'s stability, rather than folding the id into one mixed
        float/str tuple key."""

        def sort_key(candidate: Candidate) -> tuple[float, ...]:
            by_code = _sub_scores_by_code(candidate)
            score = self.scorer.score(candidate, self.weights)
            tie_break = tuple(-by_code.get(code, 0.0) for code in TIE_BREAK_ORDER)
            return (-score, *tie_break)

        stable_by_id = sorted(candidates, key=lambda c: c.id)
        return sorted(stable_by_id, key=sort_key)

    def decompose(self, a: Candidate, b: Candidate) -> Decomposition:
        weights_normalised = renormalised(self.weights)
        a_by_code = _sub_scores_by_code(a)
        b_by_code = _sub_scores_by_code(b)
        codes = sorted(set(a_by_code) | set(b_by_code) | set(weights_normalised))

        contributions = []
        for code in codes:
            weight = weights_normalised.get(code, 0.0)
            normalised_a = a_by_code.get(code, 0.0)
            normalised_b = b_by_code.get(code, 0.0)
            contributions.append(
                Contribution(
                    criterion=code,
                    weight=weight,
                    normalised_a=normalised_a,
                    normalised_b=normalised_b,
                    value=100.0 * weight * (normalised_a - normalised_b),
                )
            )

        score_a = self.scorer.score(a, self.weights)
        score_b = self.scorer.score(b, self.weights)
        return Decomposition(
            candidate_a=a.id,
            candidate_b=b.id,
            score_difference=score_a - score_b,
            contributions=tuple(contributions),
        )

    def dominance(self, candidates: list[Candidate]) -> list[DominanceVerdict]:
        """A candidate is dominated iff some OTHER candidate is STRICTLY
        better on EVERY criterion.

        The strict reading is what docs/scoring-and-explanation.md states -
        "a candidate that another improves on **every** criterion" - and is
        deliberately NOT the textbook Pareto rule ("at least as good on all,
        strictly better on one"). Two consequences worth knowing, because
        they are visible in real output rather than theoretical:

        - A candidate beaten on six criteria but merely TIED on the seventh
          is reported as not dominated. Under Pareto it would be dominated.
        - S10 carries weight 0, so nothing optimises for it and ties on it
          are common - which under this rule can mask a genuine compromise.

        Whether to move to the Pareto rule is a specification decision, not a
        keyboard one (CLAUDE.md), so the documented wording is implemented as
        written and the risk is recorded in docs/open-questions.md instead of
        being resolved here. Exact and weight-independent either way.

        A candidate carrying NO sub-scores is never dominated: ``all()`` over
        an empty criterion set is vacuously true, which would otherwise report
        it as dominated by an arbitrary other candidate on no evidence at all.
        """
        sub_scores_by_id = {c.id: _sub_scores_by_code(c) for c in candidates}
        scores_by_id = {c.id: self.scorer.score(c, self.weights) for c in candidates}

        verdicts = []
        for candidate in candidates:
            own = sub_scores_by_id[candidate.id]
            dominators = (
                [
                    other
                    for other in candidates
                    if other.id != candidate.id
                    and all(
                        sub_scores_by_id[other.id].get(code, 0.0) > own.get(code, 0.0)
                        for code in own
                    )
                ]
                if own
                else []
            )
            dominated_by = None
            if dominators:
                best = max(dominators, key=lambda o: (scores_by_id[o.id], o.id))
                dominated_by = best.id
            verdicts.append(DominanceVerdict(candidate=candidate.id, dominated_by=dominated_by))
        return verdicts

    def recommend(self, candidates: list[Candidate]) -> Recommendation | None:
        """The candidate of highest score, the rule that produced it, and a
        dominance flag if the top candidate is itself dominated - FR-16.

        docs/scoring-and-explanation.md states the whole rule and then says
        "That is the entire rule." There is deliberately no tie-break policy,
        no minimum-score floor and no second-choice logic here: anything of
        that kind would be an unstated rule the department could not check.

        The top candidate is taken from ``rank()`` rather than from a fresh
        ``max()``, so the recommendation inherits rank()'s documented
        tie-break (criteria in weight order, then id) and cannot disagree with
        the order displayed beside it. A recommendation that named a candidate
        the list did not show first would be indefensible however correct its
        arithmetic.

        Returns None for an empty portfolio - there is nothing to recommend,
        which is different from recommending nothing in particular. An
        infeasible run reaches here with no candidates at all (see
        services/portfolio.py) and must not produce a recommendation.
        """
        if not candidates:
            return None

        top = self.rank(candidates)[0]
        dominated_by = next(
            (v.dominated_by for v in self.dominance(candidates) if v.candidate == top.id), None
        )
        return Recommendation(
            candidate=top.id,
            rule=RECOMMENDATION_RULE,
            score=self.scorer.score(top, self.weights),
            dominated_by=dominated_by,
        )
