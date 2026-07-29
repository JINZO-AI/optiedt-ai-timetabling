"""Solver.solve() - stage 2 only. diagnose() (stage 3, Phase 5) is not built.

Bounded by max_deterministic_time, not max_time_in_seconds, per ADR-011:
parallel workers racing under a wall-clock limit are not reproducible, and a
fixed seed does not fix that. max_time_in_seconds is still set, as a hang
backstop only - reaching it is an anomaly, never the expected way a solve
ends.

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

from optiedt.domain.entities import Placement, RoomId, SessionId
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
            placements = tuple(
                Placement(
                    session=session.id,
                    slot=solver.value(variables.start[session.id]),
                    room=_solved_room(session.id, variables, solver),
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
