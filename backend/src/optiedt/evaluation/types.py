"""Values exchanged with the evaluator."""

from __future__ import annotations

from dataclasses import dataclass, field

from optiedt.problem.catalog import MAX_TIER, UNSCHEDULED
from optiedt.problem.snapshot import SProfile


@dataclass(frozen=True, slots=True)
class Placement:
    slot: int
    """Start slot, ``day * n_periods + period``."""
    room: int | None


@dataclass(frozen=True, slots=True)
class Violation:
    code: str
    message: str
    sessions: tuple[int, ...]
    slots: tuple[int, ...] = ()
    rule_id: str | None = None


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


@dataclass
class Evaluation:
    complete: bool
    unscheduled: list[int]
    violations: list[Violation]
    objective_values: dict[str, int]
    rule_values: dict[str, int]
    tiers: list[int]
    contributors: dict[str, list[tuple[str, int]]] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return self.complete and not self.violations

    @property
    def unscheduled_periods(self) -> int:
        return self.objective_values.get(UNSCHEDULED, 0)


def empty_tiers() -> list[int]:
    return [0] * (MAX_TIER + 1)
