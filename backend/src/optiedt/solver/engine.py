"""Solver.solve() - stage 2 only. diagnose() (stage 3, Phase 5) is not built.

Bounded by max_deterministic_time, not max_time_in_seconds, per ADR-011:
parallel workers racing under a wall-clock limit are not reproducible, and a
fixed seed does not fix that. max_time_in_seconds is still set, as a hang
backstop only - reaching it is an anomaly, never the expected way a solve
ends. Measured 2026-07-30 (C-13, docs/open-questions.md): under
num_workers=0 (parallel), max_deterministic_time did not tightly bound the
search the way it does for one worker - a run configured for 60s
deterministic time consumed 247.98 deterministic-time units before the
wall-clock ceiling actually stopped it. Not yet fully calibrated; the
wall-clock ceiling is doing more of the real work than ADR-011 assumed.

num_workers, not the deprecated num_search_workers: confirmed against the
installed OR-Tools version's own field documentation before use, since the
two are independent proto fields and setting the wrong one would silently
solve single-threaded while looking configured for parallelism. 0 means "use
all cores," matching core.config.Settings.solver_workers's existing default.

No objective is posted here. Phase 2 has hard constraints only - there is
nothing yet to minimise, so every SolverOutput.cost from this engine is 0
until Phase 3 adds the soft criteria.
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from optiedt.domain.entities import Placement, RoomId, Session, SessionId
from optiedt.domain.enums import RoomType
from optiedt.domain.instance import Instance
from optiedt.solver.constraints import ALL_HARD_CONSTRAINTS
from optiedt.solver.interfaces import DiagnosisResult, SolverInput, SolverOutput
from optiedt.solver.variables import Variables, build_variables

_TERMINAL_STATUSES = (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE)


def _solved_room(session_id: SessionId, variables: Variables, solver: cp_model.CpSolver) -> RoomId:
    for room_id in variables.candidate_rooms[session_id]:
        if solver.value(variables.assign[(session_id, room_id)]):
            return room_id
    # H7 (exactly one candidate room assigned) guarantees this never happens;
    # raising rather than returning something wrong if it somehow did.
    raise RuntimeError(f"session {session_id}: no candidate room was assigned by the solver")


def _label_cumulative_rooms(
    instance: Instance, variables: Variables, solver: cp_model.CpSolver
) -> dict[SessionId, RoomId]:
    """Assigns a specific room to every session whose room type is fully
    interchangeable (variables.cumulative_room_types), given the type-level
    schedule CP-SAT already solved (C-13, docs/open-questions.md).

    This is the classical "left-edge" interval-graph colouring algorithm:
    process sessions in non-decreasing order of solved start slot (ties
    broken by session id, for reproducibility per ADR-011 - CP-SAT's own
    iteration order is not a stable tie-break), and always take the first
    free room, in a fixed canonical order, among that type's rooms.

    This is guaranteed to succeed and never needs more rooms than the
    type's peak simultaneous demand, which H3's AddCumulative
    (room_assignment.py) already bounded to the room count while solving:
    interval graphs are perfect graphs, so a colouring using exactly as
    many colours as the largest clique (here, the deepest simultaneous
    overlap) always exists, and processing by start time while greedily
    reusing the first available colour is a standard proof of that fact,
    not a heuristic. If this ever raises, it means the cumulative bound
    posted in H3 does not actually match this function's room grouping or
    demand - a real bug, not bad luck - which is exactly why it raises
    rather than silently reusing a busy room.
    """
    rooms_by_type: dict[RoomType, list[RoomId]] = {}
    for room in instance.rooms:
        rooms_by_type.setdefault(room.type, []).append(room.id)
    for room_ids in rooms_by_type.values():
        room_ids.sort()

    sessions_by_type: dict[RoomType, list[Session]] = {}
    for session in instance.sessions:
        if session.required_room_type in variables.cumulative_room_types:
            sessions_by_type.setdefault(session.required_room_type, []).append(session)

    labelled: dict[SessionId, RoomId] = {}
    for room_type, sessions in sessions_by_type.items():
        occupied_by_room: dict[RoomId, set[int]] = {r: set() for r in rooms_by_type[room_type]}
        ordered = sorted(sessions, key=lambda s: (solver.value(variables.start[s.id]), s.id))
        for session in ordered:
            start_slot = solver.value(variables.start[session.id])
            span = set(range(start_slot, start_slot + session.duration_periods))
            for room_id in rooms_by_type[room_type]:
                if occupied_by_room[room_id].isdisjoint(span):
                    labelled[session.id] = room_id
                    occupied_by_room[room_id] |= span
                    break
            else:
                raise RuntimeError(
                    f"session {session.id}: no free {room_type} room at slot(s) {span} - "
                    "this should be impossible given H3's AddCumulative bound; if it "
                    "happens, the cumulative capacity or demand does not actually match "
                    "this labeller's room grouping."
                )
    return labelled


@dataclass(frozen=True, slots=True)
class CpSatSolver:
    """The concrete Solver for the weekly model."""

    workers: int = 0
    wall_clock_ceiling_seconds: float = 900.0

    def solve(self, request: SolverInput) -> SolverOutput:
        model = cp_model.CpModel()
        variables = build_variables(model, request)
        for builder in ALL_HARD_CONSTRAINTS:
            builder.apply(model, variables, request.instance)

        solver = cp_model.CpSolver()
        solver.parameters.max_deterministic_time = request.deterministic_budget
        solver.parameters.max_time_in_seconds = self.wall_clock_ceiling_seconds
        solver.parameters.random_seed = request.seed
        solver.parameters.num_workers = self.workers

        status = solver.solve(model)
        if status not in _TERMINAL_STATUSES:
            raise RuntimeError(
                f"unexpected CP-SAT status {solver.status_name(status)}: neither a "
                "solution nor a proof of infeasibility within the time given. Raise "
                "the deterministic budget rather than treat this as a normal result."
            )

        infeasible = status == cp_model.INFEASIBLE
        placements: tuple[Placement, ...] = ()
        if not infeasible:
            labelled_rooms = _label_cumulative_rooms(request.instance, variables, solver)
            placements = tuple(
                Placement(
                    session=session.id,
                    slot=solver.value(variables.start[session.id]),
                    room=(
                        labelled_rooms[session.id]
                        if session.required_room_type in variables.cumulative_room_types
                        else _solved_room(session.id, variables, solver)
                    ),
                )
                for session in request.instance.sessions
            )

        return SolverOutput(
            placements=placements,
            cost=0,
            infeasible=infeasible,
            proven_optimal=status == cp_model.OPTIMAL,
            deterministic_time_used=solver.deterministic_time,
            wall_clock_seconds=solver.wall_time,
        )

    def diagnose(self, request: SolverInput) -> DiagnosisResult:
        raise NotImplementedError(
            "Stage 3 (assumption-literal diagnosis) is Phase 5, not built yet. "
            "See docs/status.md and C-6 in docs/open-questions.md."
        )
