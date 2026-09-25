"""Value types shared by the solver and the evaluator: placements and tier configuration."""

from __future__ import annotations

from dataclasses import dataclass

from optiedt.problem.snapshot import SProfile


@dataclass(frozen=True, slots=True)
class Placement:
    slot: int
    """Start slot, ``day * n_periods + period``."""
    room: int | None


@dataclass(frozen=True, slots=True)
class ObjectiveConfig:
    """Tier and weight of each enabled built-in objective, and the stability reference."""

    objectives: dict[str, tuple[int, int]]
    reference: dict[int, Placement] | None = None

    @classmethod
    def from_profile(
        cls,
        profile: SProfile,
        reference: dict[int, Placement] | None = None,
        stability_tier: int = 1,
    ) -> ObjectiveConfig:
        objectives = {
            code: (setting.tier, setting.weight)
            for code, setting in profile.objectives.items()
            if setting.enabled
        }
        if reference is not None:
            objectives["stability"] = (stability_tier, 1)
        return cls(objectives=objectives, reference=reference)
