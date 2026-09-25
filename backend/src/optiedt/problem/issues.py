"""Findings reported before solving: data-quality checks and feasibility pre-checks."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Issue:
    severity: str
    """``error``: a complete timetable is impossible until it is fixed. ``warning``: risky."""
    code: str
    message: str
    entity_type: str | None = None
    entity_ids: tuple[str, ...] = field(default_factory=tuple)
    figures: dict[str, float] = field(default_factory=dict)
