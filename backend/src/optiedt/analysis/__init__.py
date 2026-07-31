"""Scoring, ranking, exact decomposition, dominance.

May not import the solver or the database. An error here produces a wrong ORDER,
never an invalid TIMETABLE - that is the whole point of the boundary.
"""

from __future__ import annotations

from optiedt.analysis.criteria import build_criteria
from optiedt.analysis.interfaces import (
    Bounds,
    Contribution,
    Criterion,
    Decomposition,
    DominanceVerdict,
    Ranker,
    Recommendation,
    Scorer,
)
from optiedt.analysis.ranking import RECOMMENDATION_RULE, DefaultRanker
from optiedt.analysis.scoring import DefaultScorer, evaluate_candidate, normalise, renormalised

__all__ = [
    "RECOMMENDATION_RULE",
    "Bounds",
    "Contribution",
    "Criterion",
    "Decomposition",
    "DefaultRanker",
    "DefaultScorer",
    "DominanceVerdict",
    "Ranker",
    "Recommendation",
    "Scorer",
    "build_criteria",
    "evaluate_candidate",
    "normalise",
    "renormalised",
]
