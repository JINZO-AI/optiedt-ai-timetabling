"""H3 and H7 - two room-assignment encodings, chosen per room type.

Most room types use the optional-interval pattern: room[s] is not a plain
integer variable, because H3's partition key (which room a session lands
in) is something the solver decides, not a fixed session attribute the way
teacher_id is for H1. The construction gives each session one boolean
assign[s, r] per candidate room (solver/variables.py), with an optional
interval present only when that boolean is true. H3 becomes a NoOverlap per
room over those optional intervals; H7 becomes "exactly one of the
candidate booleans is true" per session. A session's actual room, once
solved, is read off of whichever assign[s, r] came back 1 - see
solver/engine.py.

Room types in variables.cumulative_room_types use a different encoding
instead (C-13, resolved 2026-07-30 - see docs/open-questions.md). These are
room types where every requiring session has every room of that type as a
candidate - full interchangeability - and on the reference instance two
such types (Lab_Info, Lab_Sciences) sit at 95.2% / 85.7% occupancy, which
made the per-room encoding an intractable symmetric search for CP-SAT
(measured: UNKNOWN after 480s of tuned search). For these types, H3 posts
one AddCumulative over the sessions' unconditional intervals (demand 1
each, capacity = room count) instead of a NoOverlap per room, and H7 posts
nothing at all for them - "exactly one room" is guaranteed afterward by a
deterministic greedy labeller in solver/engine.py, not by a posted
constraint. This is still H3 and H7's job by their catalogue definition
(H3: a room hosts at most one session at a time; H7: each session is placed
in exactly one room) - only the mechanism differs, and the correctness
argument for why it's still guaranteed lives in engine.py, next to the
labeller itself.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ortools.sat.python import cp_model

    from optiedt.domain.entities import ConstraintCode, RoomId
    from optiedt.domain.enums import RoomType
    from optiedt.domain.instance import Instance
    from optiedt.solver.variables import Variables


@dataclass(frozen=True, slots=True)
class H3:
    """A room hosts at most one session per slot.

    NoOverlap per room for ordinary room types, over the optional intervals
    of every session that could land there; AddCumulative per room TYPE for
    fully-interchangeable types (module docstring)."""

    @property
    def code(self) -> ConstraintCode:
        return "H3"

    @property
    def carries_assumption_literal(self) -> bool:
        return True

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        rooms_per_type: dict[RoomType, int] = defaultdict(int)
        for room in instance.rooms:
            rooms_per_type[room.type] += 1

        by_room: dict[RoomId, list[cp_model.IntervalVar]] = defaultdict(list)
        cumulative_intervals: dict[RoomType, list[cp_model.IntervalVar]] = defaultdict(list)
        for session in instance.sessions:
            if session.required_room_type in variables.cumulative_room_types:
                cumulative_intervals[session.required_room_type].append(
                    variables.interval[session.id]
                )
                continue
            for room_id in variables.candidate_rooms[session.id]:
                by_room[room_id].append(variables.room_interval[(session.id, room_id)])

        for intervals in by_room.values():
            model.add_no_overlap(intervals)

        for room_type, intervals in cumulative_intervals.items():
            model.add_cumulative(intervals, [1] * len(intervals), rooms_per_type[room_type])


@dataclass(frozen=True, slots=True)
class H7:
    """Each session is placed exactly once.

    Exactly-one over the candidate-room assignment booleans, for ordinary
    room types. Fully-interchangeable types (variables.cumulative_room_types)
    get no posting here at all - the guarantee is structural, delivered by
    the post-hoc greedy labeller in solver/engine.py, not by a constraint."""

    @property
    def code(self) -> ConstraintCode:
        return "H7"

    @property
    def carries_assumption_literal(self) -> bool:
        return True

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        for session in instance.sessions:
            if session.required_room_type in variables.cumulative_room_types:
                continue
            candidates = variables.candidate_rooms[session.id]
            model.add_exactly_one(variables.assign[(session.id, r)] for r in candidates)
