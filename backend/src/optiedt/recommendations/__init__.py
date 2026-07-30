"""The closed catalogue of three actions, and their translation to solver input.

Writes a weight, a lock or an exclusion. Never a placement.
"""

from __future__ import annotations

from optiedt.recommendations.catalogue import (
    ExcludeSlot,
    LockSession,
    RecommendationAction,
    RecommendationTranslator,
    WeightDelta,
)
from optiedt.recommendations.translator import (
    DefaultRecommendationTranslator,
    ExcludedOption,
    LockedPlacement,
    RunOverride,
    UnresolvedLockTargetError,
    WeightOverride,
)

__all__ = [
    "DefaultRecommendationTranslator",
    "ExcludeSlot",
    "ExcludedOption",
    "LockSession",
    "LockedPlacement",
    "RecommendationAction",
    "RecommendationTranslator",
    "RunOverride",
    "UnresolvedLockTargetError",
    "WeightDelta",
    "WeightOverride",
]
