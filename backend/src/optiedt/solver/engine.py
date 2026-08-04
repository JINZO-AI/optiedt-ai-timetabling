"""Solver.solve() - stage 2 - and diagnose() - stage 3, added Phase 5 M2.

Bounded by max_deterministic_time, not max_time_in_seconds, per ADR-011:
parallel workers racing under a wall-clock limit are not reproducible, and a
fixed seed does not fix that. max_time_in_seconds is still set, as a hang
backstop only - reaching it is an anomaly, never the expected way a solve
ends.

⚠️ This docstring claimed until 2026-08-03 that max_deterministic_time "did
not tightly bound the search" under num_workers=0, citing 60 requested against
247.98 consumed. **That was false and is corrected here.** The budget binds
EXACTLY, per worker: CpSolver.deterministic_time reports the SUM ACROSS
WORKERS, so a 16-core machine legitimately reports ~11x the budget and nothing
was overshooting. Measured 2026-07-30 - budget 5 reports 5.00 at one worker,
ratio 1.00 - and recorded in C-2 and ADR-011; tests/integration/
test_reproducibility.py pins the ratio so the misreading cannot return. The
wall-clock ceiling is NOT doing more of the real work than ADR-011 assumed.

num_workers, not the deprecated num_search_workers: confirmed against the
installed OR-Tools version's own field documentation before use, since the
two are independent proto fields and setting the wrong one would silently
solve single-threaded while looking configured for parallelism. 0 means "use
all cores," matching core.config.Settings.solver_workers's existing default.

An objective is posted only when ``request.profile`` carries a criterion with
usable weight (Phase 3). ``build_occupancy`` then runs first, so x[s,t0] and
y[s,t] exist for ``build_objective`` to read (solver/occupancy.py,
solver/objective.py).

Both are gated on ``has_active_criteria``, not on ``profile is not None``:
occupancy costs 10,048 variables and roughly 2.5x the solve time, so an
all-zero-weight profile has to skip it to be genuinely equivalent to the
Phase 2 feasibility solve rather than merely posting no objective while still
paying for the accounting. Callers passing ``profile=None`` (feasibility-only,
e.g. the Phase 2 tests) are unaffected - occupancy is not built and
``SolverOutput.cost`` stays 0, exactly as before.

``SolverOutput.cost`` is the CP-SAT objective value in scaled integer units
(see solver/objective.py's _WEIGHT_SCALE) and is informational only. It is NOT
the displayed score: the analysis layer recomputes every criterion
independently from the returned placements, and nothing ranks on this field.

⚠️ That separation is load-bearing, and 2026-07-31 it paid. Measured on the
ITC-2007 harness (optiedt/validation/itc2007): under ``interleave_search``,
``CpSolver.objective_value`` can be reported a few units ABOVE the objective
expression evaluated at the very solution the solver returns, on solves that
stop on the budget without proving optimality. With the parameter off the two
agree exactly on the same instances; it is marked Experimental upstream.

Nothing in this project is affected, because nothing reads this field to make a
decision - the score comes from analysis/criteria.py re-derived from the
placements, which is what docs/architecture.md's ban on analysis importing the
solver forces. **Do not start ranking, comparing or displaying ``cost``.** If a
future change needs a trustworthy objective figure, take it only from a solve
that reports ``proven_optimal``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from optiedt.domain.entities import DiagnosisResult, Placement, RoomId, Session, SessionId
from optiedt.domain.enums import RoomType
from optiedt.domain.instance import Instance
from optiedt.solver.constraints import ALL_HARD_CONSTRAINTS
from optiedt.solver.interfaces import SolverInput, SolverOutput
from optiedt.solver.objective import build_objective, has_active_criteria
from optiedt.solver.occupancy import build_occupancy
from optiedt.solver.variables import Variables, build_variables
from optiedt.solver.warm_start import build_warm_start

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


def _apply_warm_start(model: cp_model.CpModel, variables: Variables, request: SolverInput) -> None:
    """Hints CP-SAT with a hand-built greedy placement. CP-SAT is typically
    far faster at verifying a supplied candidate than at finding one from
    scratch, and a partial hint still gives the search a head start on the
    sessions it covers.

    On the reference instance the greedy now covers all 218 sessions in
    0.04s (measured 2026-07-30, after the C-13 repair). It previously
    plateaued around 192/218 - because at most 202 could be placed at all,
    the instance being infeasible, which is what that plateau was actually
    reporting. The hint is therefore not needed for feasibility here; it is
    kept because it costs almost nothing and should earn its place once the
    objective makes the search non-trivial.
    """
    warm_start = build_warm_start(request)
    session_by_id = {s.id: s for s in request.instance.sessions}
    for session_id in warm_start.covered:
        session = session_by_id[session_id]
        model.add_hint(variables.start[session_id], warm_start.start[session_id])
        if session.required_room_type in variables.cumulative_room_types:
            continue
        chosen_room = warm_start.room[session_id]
        for room_id in variables.candidate_rooms[session_id]:
            model.add_hint(variables.assign[(session_id, room_id)], int(room_id == chosen_room))


@dataclass(frozen=True, slots=True)
class CpSatSolver:
    """The concrete Solver for the weekly model."""

    workers: int = 0
    wall_clock_ceiling_seconds: float = 900.0
    use_warm_start: bool = True

    def solve(self, request: SolverInput) -> SolverOutput:
        model = cp_model.CpModel()
        variables = build_variables(model, request)
        for builder in ALL_HARD_CONSTRAINTS:
            builder.apply(model, variables, request.instance)

        # Gate on has_active_criteria(), NOT merely on profile is not None:
        # build_occupancy() adds 10,048 variables and costs the solve about
        # 2.5x (docs/constraint-model.md), so a profile whose weights are all
        # zero must skip it entirely to stay equivalent to the Phase 2
        # feasibility solve. Checking only build_objective()'s return value
        # would be too late - occupancy would already have been built.
        wants_objective = request.profile is not None and has_active_criteria(
            request.profile.weights
        )

        # ⚠️ The warm start is withheld when an objective is posted. Measured
        # 2026-07-30 (C-16): with the hint in place, all three weight profiles
        # returned the SAME timetable at total budgets 15, 45 and 90, scoring
        # an identical 78.076 every time - six times the budget and three
        # different objectives producing one candidate. The hint is a strong
        # attractor, and under an objective the search does not escape it, so
        # duplicate removal collapses the portfolio to a single candidate.
        # Withholding it yields 3 distinct candidates at budget 90.
        #
        # It is KEPT for feasibility-only solves, where there is no objective
        # to be pulled away from and the hint is pure acceleration - which is
        # the role docs/status.md always assigned it, and the re-evaluation
        # that file asked for "when the objective lands".
        if self.use_warm_start and not wants_objective:
            _apply_warm_start(model, variables, request)

        objective_posted = False
        if wants_objective:
            occupancy = build_occupancy(model, variables, request.instance)
            objective_posted = (
                build_objective(
                    model, variables, occupancy, request.instance, request.profile.weights
                )
                is not None
            )

        solver = cp_model.CpSolver()
        solver.parameters.max_deterministic_time = request.deterministic_budget
        solver.parameters.max_time_in_seconds = self.wall_clock_ceiling_seconds
        solver.parameters.random_seed = request.seed
        solver.parameters.num_workers = self.workers

        # ⚠️ REQUIRED for reproducibility. Without it the solve is NOT
        # deterministic at production worker counts, whatever the seed and
        # whatever the deterministic budget - measured 2026-07-30, three
        # identical requests produced three different timetables, all of them
        # proving optimality. The workers were not being cut short; they were
        # finding different optimal solutions and returning whichever reported
        # first.
        #
        # OR-Tools documents this field as: "If this is true, then we
        # interleave all our major search strategy and distribute the work
        # amongst num_workers. The search is deterministic (independently of
        # num_workers!)". Verified on the reference instance: deterministic in
        # every configuration tested, and roughly 2x faster end-to-end than
        # the racing search it replaces.
        #
        # Disabling worker information sharing (share_binary_clauses,
        # share_level_zero_bounds, share_objective_bounds) was also tried and
        # does NOT help - the race is in the scheduling, not the sharing.
        #
        # The field is marked "Experimental" upstream, which is why
        # tests/integration/test_reproducibility.py pins the behaviour against
        # the production settings rather than trusting the documentation.
        # See ADR-011 and C-16 in docs/open-questions.md.
        solver.parameters.interleave_search = True

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

        cost = round(solver.objective_value) if objective_posted and not infeasible else 0

        return SolverOutput(
            placements=placements,
            cost=cost,
            infeasible=infeasible,
            proven_optimal=status == cp_model.OPTIMAL,
            deterministic_time_used=solver.deterministic_time,
            wall_clock_seconds=solver.wall_time,
        )

    def diagnose(self, request: SolverInput) -> DiagnosisResult:
        """Stage 3 - which rules are responsible for an infeasibility (FR-8).

        Entered only after `solve` returns infeasible.

        **How it works: withdraw one rule at a time, and solve plainly.**
        Establish first that no timetable exists at all. Then, for each rule
        that may be withdrawn (H1, H3, H7, H12 - C-6), solve the model without
        it: if the model is STILL infeasible, that rule was not needed for the
        contradiction and is dropped for good. What survives is the answer.

        ⚠️ **This is not the mechanism docs/architecture.md originally
        specified, and the reason is measured (C-17).** That design declared
        every rule under an enforcement literal and read CP-SAT's unsat core
        back. It is implementable - OR-Tools 9.15 honours `only_enforce_if` on
        `no_overlap`, `cumulative` and `exactly_one` - and it does not work at
        this project's scale. An enforcement literal takes its constraint OUT
        OF PRESOLVE: it stops being a fact the propagators may reason with and
        becomes a conditional obligation. Measured on the reference instance
        with four computer laboratories withdrawn - an area contradiction of
        exactly the kind AddCumulative reasons about:

            plain solve, 1 worker           INFEASIBLE     0.0 s
            plain solve, 4 workers          INFEASIBLE     0.0 s
            under four assumption literals  UNKNOWN      240.0 s  (budget 120)

        Not a budget problem: four times the budget changed nothing. Every
        solve below is a PLAIN solve, so presolve keeps working, and the same
        instance is answered `('H3',)` in 1.6 s.

        Three properties, and only one of them is still imposed by CP-SAT:

        1. **No objective** - imposed. A feasibility question is being asked;
           `build_occupancy` and `build_objective` are not called at all here.
        2. **A single worker** - kept, but for a NEW reason. The old one was
           that assumptions admit no parallelism, and there are no assumptions
           now. `max_deterministic_time` is a PER-WORKER budget, so more
           workers do more total work and could flip an `UNKNOWN` into an
           `INFEASIBLE` between machines. A report that named different rules
           on different machines would be worse than none.
        3. **Sufficient, not minimal** - no longer forced. Every removal here
           is tested, so the surviving set is irreducible with respect to the
           four. `is_minimal` is set True ONLY when every removal was decided;
           a subset solve that returns `UNKNOWN` keeps its rule for want of
           evidence, and saying "minimal" then would be a claim nobody checked.

        ⚠️ "Minimal" means irreducible **with respect to the four withdrawable
        rules, with all the others enforced**. H4-H6 and H8-H10 restrict a
        variable's domain before the model exists and are always present, so
        they can be the real cause - in which case every rule is dropped and
        the set comes back empty, pointing at the pre-analysis report.

        The budget and the wall-clock ceiling are divided across the solves
        this makes, so the whole stage stays inside the bound the run was
        given - the same rule `services/portfolio.py` follows for profiles.
        """
        withdrawable = tuple(b.code for b in ALL_HARD_CONSTRAINTS if b.carries_assumption_literal)
        solves = 1 + len(withdrawable)
        budget = request.deterministic_budget / solves
        ceiling = self.wall_clock_ceiling_seconds / solves

        def status_without(omitted: frozenset[str]) -> cp_model.CpSolverStatus:
            model = cp_model.CpModel()
            variables = build_variables(model, request)
            for builder in ALL_HARD_CONSTRAINTS:
                if builder.code not in omitted:
                    builder.apply(model, variables, request.instance)
            solver = cp_model.CpSolver()
            solver.parameters.max_deterministic_time = budget
            solver.parameters.max_time_in_seconds = ceiling
            solver.parameters.random_seed = request.seed
            solver.parameters.num_workers = 1
            return solver.solve(model)

        try:
            baseline = status_without(frozenset())
        except ValueError as exc:
            # H4/H5 left a session with no room, or H6/H8/H9 with no start.
            # There is no model to diagnose: the domain was empty before the
            # search began, and withdrawing a posted constraint cannot widen a
            # domain.
            return DiagnosisResult(
                conflicting_codes=(),
                is_conclusive=True,
                detail=(
                    "No model could be built, so no rule can be withdrawn to explain the "
                    f"conflict: {exc} The pre-analysis report names the resource and the "
                    "quantity missing."
                ),
            )

        if baseline in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Reachable only if `solve` and `diagnose` were given different
            # instances, since H1-H12 are declared identically whatever the
            # weights. Reported rather than raised: the run already has a
            # verdict, and an exception here would replace it with a stack
            # trace.
            return DiagnosisResult(
                conflicting_codes=(),
                is_conclusive=True,
                detail=(
                    "The diagnosis run found a timetable satisfying all twelve hard "
                    "constraints, so there is no conflict to report. If stage 2 returned "
                    "INFEASIBLE, the two stages were given different data."
                ),
            )

        if baseline != cp_model.INFEASIBLE:
            return DiagnosisResult(
                conflicting_codes=(),
                is_conclusive=False,
                detail=(
                    "Inconclusive: the solver neither found a timetable nor proved that "
                    "none exists, within the budget. This is NOT evidence that the "
                    "instance is sound - an instance can genuinely have no solution while "
                    "the propagators cannot construct the proof, which is what cost three "
                    "sessions on C-13. Read the pre-analysis report, and raise the "
                    "deterministic budget."
                ),
            )

        dropped: set[str] = set()
        undecided: list[str] = []
        for code in withdrawable:
            status = status_without(frozenset(dropped | {code}))
            if status == cp_model.INFEASIBLE:
                dropped.add(code)  # the contradiction survives without it
            elif status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                undecided.append(code)  # kept for want of evidence, not proof

        kept = tuple(code for code in withdrawable if code not in dropped)

        if not kept:
            return DiagnosisResult(
                conflicting_codes=(),
                is_conclusive=True,
                detail=(
                    "No timetable exists, and no withdrawable rule explains it: the "
                    "instance is still infeasible with H1, H3, H7 and H12 all removed. "
                    "H4, H5, H6, H8, H9 and H10 restrict a variable's domain before the "
                    "search begins and cannot be withdrawn, so the conflict is in the "
                    "data - read the pre-analysis report."
                ),
            )

        if undecided:
            return DiagnosisResult(
                conflicting_codes=kept,
                is_minimal=False,
                is_conclusive=True,
                detail=(
                    "No timetable exists. The conflict is explained by: "
                    f"{', '.join(kept)}. The set is NOT known to be irreducible: removing "
                    f"{', '.join(undecided)} left the solver unable to decide within the "
                    "budget, so each was kept for want of evidence rather than because it "
                    "was shown to be needed. Raise the deterministic budget to narrow it."
                ),
            )

        return DiagnosisResult(
            conflicting_codes=kept,
            is_minimal=True,
            is_conclusive=True,
            detail=(
                "No timetable exists. The conflict is explained by: "
                f"{', '.join(kept)}. The set is irreducible: removing any one of them "
                "admits a timetable, and every other withdrawable rule was removed without "
                "lifting the infeasibility. Irreducible among the four withdrawable rules "
                "only - H4 to H6 and H8 to H10 restrict domains before the search begins "
                "and are always in force."
            ),
        )
