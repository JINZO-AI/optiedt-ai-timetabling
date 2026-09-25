"""Differences between two timetables, matching an activity's occurrences as a multiset."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from optiedt.evaluation.types import Placement
from optiedt.problem.model import Problem


@dataclass(frozen=True, slots=True)
class Change:
    activity: int
    kind: str
    """``moved`` (time changed), ``room`` (same time, other room), ``scheduled`` (was unplaced),
    ``unscheduled`` (no longer placed)."""
    before: Placement | None
    after: Placement | None
    session: int | None
    """A session of the activity now at ``after`` (or last at ``before``)."""


def diff(
    problem: Problem, before: Mapping[int, Placement], after: Mapping[int, Placement]
) -> list[Change]:
    changes: list[Change] = []
    for activity in problem.activities:
        old = [(before[s], s) for s in activity.sessions if s in before]
        new = [(after[s], s) for s in activity.sessions if s in after]
        # Identical placements are not changes, whichever occurrence holds them.
        remaining_old = list(old)
        remaining_new = []
        for placement, session in new:
            match = next((i for i, (p, _) in enumerate(remaining_old) if p == placement), None)
            if match is None:
                remaining_new.append((placement, session))
            else:
                remaining_old.pop(match)
        # Same slot, different room.
        still_new = []
        for placement, session in remaining_new:
            match = next(
                (i for i, (p, _) in enumerate(remaining_old) if p.slot == placement.slot), None
            )
            if match is None:
                still_new.append((placement, session))
            else:
                previous, _ = remaining_old.pop(match)
                changes.append(Change(activity.index, "room", previous, placement, session))
        remaining_old.sort(key=lambda item: item[0].slot)
        still_new.sort(key=lambda item: item[0].slot)
        for (previous, _), (placement, session) in zip(remaining_old, still_new, strict=False):
            changes.append(Change(activity.index, "moved", previous, placement, session))
        for previous, session in remaining_old[len(still_new) :]:
            changes.append(Change(activity.index, "unscheduled", previous, None, session))
        for placement, session in still_new[len(remaining_old) :]:
            changes.append(Change(activity.index, "scheduled", None, placement, session))
    return changes
