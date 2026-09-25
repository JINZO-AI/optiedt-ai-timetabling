"""Values exchanged with the evaluator."""

from __future__ import annotations

from dataclasses import dataclass, field

from optiedt.problem.catalog import MAX_TIER, UNSCHEDULED
from optiedt.problem.solution import ObjectiveConfig, Placement

__all__ = ["Evaluation", "ObjectiveConfig", "Placement", "Violation", "empty_tiers"]


@dataclass(frozen=True, slots=True)
class Violation:
    code: str
    message: str
    sessions: tuple[int, ...]
    slots: tuple[int, ...] = ()
    rule_id: str | None = None
    subject: int | None = None
    """Index of the instructor, group, activity or room the violation is about, when there
    is one (per ``code``)."""


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
