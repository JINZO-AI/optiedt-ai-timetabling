"""Contracts of the analysis layer.

This layer reads candidates as plain data and returns numbers. It may NOT
import the solver and may NOT write a placement — enforced by .importlinter.
That boundary is what makes an error here produce a wrong ORDER instead of an
invalid TIMETABLE.

See docs/scoring-and-explanation.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from optiedt.domain.entities import Candidate, ConstraintCode


@dataclass(frozen=True, slots=True)
class Bounds:
    """Normalisation bounds for one criterion.

    Derived from the INSTANCE, not from the candidates a run produced
    (ADR-009). Candidate-derived bounds would break the monotonicity property
    the specification requires, and would silently invalidate comparison across
    runs — which is exactly what FR-23 makes routine.

    Guard ``maximum == minimum``: it is not hypothetical. A criterion with no
    violations anywhere, or S10 at weight 0, will reach it. The convention is
    n_i = 1.
    """

    minimum: float
    maximum: float


class Criterion(Protocol):
    """One quality criterion — S2, S3, S4, S5, S6, S7 or S10.

    ``raw_value`` and ``bounds`` sit on the same object deliberately, so a
    criterion cannot be half-defined. Note that ``bounds`` takes the instance,
    not a list of candidates: the signature makes the rejected reading of
    ADR-009 inexpressible.

    ⚠️ NO criterion has a defined raw-value formula yet. This is C-4, the
    largest specification gap — see docs/open-questions.md. Do not implement a
    criterion without first recording its formula and its bound formula there.
    """

    @property
    def code(self) -> ConstraintCode: ...

    def raw_value(self, candidate: Candidate) -> float:
        """Violations, or the quantity penalised, for this criterion."""
        ...

    def bounds(self, instance: object) -> Bounds:
        """Instance-derived bounds. Stable across every run on that instance."""
        ...


@dataclass(frozen=True, slots=True)
class Contribution:
    """One criterion's part of the difference between two scores.

        contribution_i = 100 * w_i * ( n_i(A) - n_i(B) )

    The sum of the contributions equals the difference of the scores, exactly.
    This identity is the explanation feature: what the user sees IS the score
    calculation read term by term, not an approximation of it.
    """

    criterion: ConstraintCode
    weight: float
    normalised_a: float
    normalised_b: float
    value: float


@dataclass(frozen=True, slots=True)
class Decomposition:
    """The exact decomposition of a difference between two candidates.

    Invariant, verified by a property test:
        sum(c.value for c in contributions) == score_difference
    to display precision — which is what the acceptance criterion promises.
    """

    candidate_a: str
    candidate_b: str
    score_difference: float
    contributions: tuple[Contribution, ...]


@dataclass(frozen=True, slots=True)
class DominanceVerdict:
    """A candidate another matches on EVERY criterion and beats on AT LEAST
    ONE is dominated — the standard Pareto rule (C-14, resolved 2026-08-05).

    Surfaced WHEREVER it occurs in the portfolio. ⚠️ Not at the top rank: a
    dominated candidate cannot outscore its dominator, so that state is
    unreachable and an indicator on it would never fire. Exact, needs no
    parameters — but produces no order, so it complements the weighted sum and
    never replaces it.
    """

    candidate: str
    dominated_by: str | None


@dataclass(frozen=True, slots=True)
class Recommendation:
    """The candidate the system puts forward, and why — FR-16.

    docs/scoring-and-explanation.md states the whole rule: "The recommendation
    designates the candidate of highest score, and states the rule that
    produced it."

    ``rule`` is carried as text rather than left for the interface to invent,
    because the point of the rule is that it can be CHECKED: "recommended
    because it has the highest score under the weights in force" is a sentence
    the department can verify against the sub-scores recorded with the run. An
    interface that phrased it differently on each screen would lose that.

    ⚠️ ``dominated_by`` is PROVABLY always None and no display reads it. That
    document carried a third sentence - "A dominated top candidate is signalled
    alongside" - until C-14 was resolved on 2026-08-05; it described a state a
    linear weighted sum with non-negative weights forbids, so it was removed
    rather than left as a promise nothing could keep. The field stays because
    FR-16's statement names it and because a non-linear score or a negative
    weight would revive it, and it is pinned dead by
    test_a_dominated_candidate_is_never_recommended. What a user sees instead
    is the portfolio-wide verdict above.
    """

    candidate: str
    rule: str
    score: float
    dominated_by: str | None


class Scorer(Protocol):
    """Computes sub-scores and the overall score out of 100.

        n_i(k)   = 1 - ( v_i(k) - min_i ) / ( max_i - min_i )
        score(k) = 100 * sum( w_i * n_i(k) )

    Linearity is load-bearing. Any change making the score non-linear destroys
    the exact decomposition, which is the reason the explanation is defensible.
    """

    def score(self, candidate: Candidate, weights: dict[ConstraintCode, float]) -> float: ...


class Ranker(Protocol):
    """Orders candidates by decreasing score.

    Ties are separated by the criteria taken in order of their weights. The
    order must not depend on the order candidates are read in — a tested
    property, not an assumption.
    """

    def rank(self, candidates: list[Candidate]) -> list[Candidate]: ...

    def decompose(self, a: Candidate, b: Candidate) -> Decomposition: ...

    def dominance(self, candidates: list[Candidate]) -> list[DominanceVerdict]: ...

    def recommend(self, candidates: list[Candidate]) -> Recommendation | None: ...
