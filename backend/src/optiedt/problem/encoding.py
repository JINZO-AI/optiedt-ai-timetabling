"""Placements named by identifiers, as stored and exchanged, translated to and from the
index-based placements the solver and the evaluator use."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from optiedt.problem.model import Problem
from optiedt.problem.solution import Placement

EncodedPlacements = dict[str, list[Any]]
"""``{session_id: [day, period, room_id or None]}``."""


class Codec:
    """Translates between snapshot identifiers and problem indices."""

    def __init__(self, problem: Problem) -> None:
        self.p = problem
        self.session_index = {s.id: s.index for s in problem.sessions}

    def placements(self, encoded: Mapping[str, list[Any]] | None) -> dict[int, Placement]:
        """Decodes placements, skipping sessions the snapshot no longer has and forgetting
        rooms it no longer has."""
        result: dict[int, Placement] = {}
        for session_id, (day, period, room_id) in (encoded or {}).items():
            s = self.session_index.get(session_id)
            if s is None or not (0 <= day < self.p.n_days and 0 <= period < self.p.n_periods):
                continue
            room = self.p.room_index.get(room_id) if room_id is not None else None
            result[s] = Placement(self.p.slot(day, period), room)
        return result

    def sessions(self, session_ids: Iterable[str]) -> frozenset[int]:
        return frozenset(self.session_index[i] for i in session_ids if i in self.session_index)

    def encode(self, placements: Mapping[int, Placement]) -> EncodedPlacements:
        p = self.p
        return {
            p.sessions[s].id: [
                p.day_of(placement.slot),
                p.period_of(placement.slot),
                p.rooms[placement.room].id if placement.room is not None else None,
            ]
            for s, placement in sorted(placements.items())
        }

    def slot(self, slot: int) -> list[int]:
        return [self.p.day_of(slot), self.p.period_of(slot)]
