"""H3 and H7 — the optional-interval room-assignment pattern.

room[s] is not a plain integer variable here, because H3's partition key
(which room a session lands in) is something the solver decides, not a
fixed attribute the way teacher_id is for H1. The standard construction
instead gives each session one boolean assign[s, r] per candidate room
(solver/variables.py), with an optional interval present only when that
boolean is true. H3 becomes a NoOverlap per room over those optional
intervals; H7 becomes "exactly one of the candidate booleans is true" per
session. A session's actual room, once solved, is read off of whichever
assign[s, r] came back 1 - see solver/engine.py.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ortools.sat.python import cp_model

    from optiedt.domain.entities import ConstraintCode, RoomId
    from optiedt.domain.instance import Instance
    from optiedt.solver.variables import Variables


@dataclass(frozen=True, slots=True)
class H3:
    """A room hosts at most one session per slot: NoOverlap per room, over
    the optional intervals of every session that could land there."""

    @property
    def code(self) -> ConstraintCode:
        return "H3"

    @property
    def carries_assumption_literal(self) -> bool:
        return True

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        by_room: dict[RoomId, list[cp_model.IntervalVar]] = defaultdict(list)
        for session in instance.sessions:
            for room_id in variables.candidate_rooms[session.id]:
                by_room[room_id].append(variables.room_interval[(session.id, room_id)])
        for intervals in by_room.values():
            model.add_no_overlap(intervals)


@dataclass(frozen=True, slots=True)
class H7:
    """Each session is placed exactly once: exactly one candidate-room
    assignment boolean is true, per session."""

    @property
    def code(self) -> ConstraintCode:
        return "H7"

    @property
    def carries_assumption_literal(self) -> bool:
        return True

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        for session in instance.sessions:
            candidates = variables.candidate_rooms[session.id]
            model.add_exactly_one(variables.assign[(session.id, r)] for r in candidates)
