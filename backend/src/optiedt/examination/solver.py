"""The CP-SAT model of the examination session — SRS §6.8.

Five rules, and every one of them is the specification's own:

**X1** - "A student never has two examinations in the same slot"
    `add_all_different` over the start variables of each student's examinations.

**X2** - "Capacity of the rooms covering the number of candidates"
    `sum(capacity(r) * assign[e][r]) >= candidates(e)` - a SUM, which is what
    SRS 6.8 says room assignment becomes.

**X3** - "Examination placed inside the period and outside the holidays"
    The domain of `start[e]`: only slots that satisfy it are built at all.

**X4** - "No supervisor assigned to two examinations in the same slot"
    `add_all_different` over each supervisor's examinations.

**SX1** *(soft)* - "Examinations of the same group spread over the session"
    A penalty per promotion per day beyond the first.

⚠️ **Nothing here comes from ITC-2007.** Track 1 has never been opened by this
project (ADR-008), and a benchmark's constraints are not this product's
requirements. If Track 1 is ever used it belongs in `optiedt.validation`, which
the eighth import contract keeps out of shipped code.

⚠️ **This module does not import `optiedt.solver` and must not.** The two models
share the domain and nothing else. An examination occupies one or more rooms
and is indexed over the examination period; the weekly model places one room
per session over a week. A shared variable schema would force one of them into
a shape that does not fit it — which is exactly what R-6 warns against.

**Reproducibility is configured the same way as the weekly engine**, and for the
same reasons: a deterministic budget rather than wall-clock (ADR-011), and
`interleave_search = True`, without which a parallel search is not reproducible
even under a fixed seed (C-16). The wall-clock ceiling is a hang backstop only.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass

from ortools.sat.python import cp_model

from optiedt.domain.entities import Room
from optiedt.domain.examination import (
    ExaminationId,
    ExamPlacement,
    ExamSession,
    ExamTimetable,
)


@dataclass(frozen=True, slots=True)
class ExamSolver:
    """Solves one examination session. No portfolio, no ranking — FR-20 asks
    for *a* timetable, and PPM's completion criterion is singular."""

    workers: int = 8
    wall_clock_ceiling_seconds: float = 600.0

    def solve(self, session: ExamSession, rooms: tuple[Room, ...]) -> ExamTimetable:
        model = cp_model.CpModel()
        exams = session.examinations
        slots = session.slots
        n_slots = len(slots)

        # ── start[e] : which slot. X3 lives in this domain (see module doc) ──
        start = {e.id: model.new_int_var(0, n_slots - 1, f"start_{e.id}") for e in exams}

        # ── assign[e][r] : R-6, an examination may occupy SEVERAL rooms ──────
        assign: dict[tuple[ExaminationId, str], cp_model.IntVar] = {}
        for e in exams:
            for r in rooms:
                assign[(e.id, r.id)] = model.new_bool_var(f"assign_{e.id}_{r.id}")

        # ── X2 : the assigned capacity covers the candidates ────────────────
        # A SUM of capacities, not the choice of a single room (SRS §6.8).
        for e in exams:
            model.add(sum(r.capacity * assign[(e.id, r.id)] for r in rooms) >= e.candidate_count)
            # At least one room, so an examination is never placed nowhere. Not
            # a separate rule: it follows from X2 whenever candidates > 0, and
            # is stated so a zero-candidate examination could not slip through.
            model.add(sum(assign[(e.id, r.id)] for r in rooms) >= 1)

        # ── A room hosts at most one examination per slot ────────────────────
        # The examination counterpart of H3. Optional intervals of one slot,
        # NoOverlap per room: a room is only occupied when it is assigned.
        for r in rooms:
            intervals = [
                model.new_optional_interval_var(
                    start[e.id],
                    1,
                    model.new_int_var(1, n_slots, f"end_{e.id}_{r.id}"),
                    assign[(e.id, r.id)],
                    f"iv_{e.id}_{r.id}",
                )
                for e in exams
            ]
            model.add_no_overlap(intervals)

        # ── X1 : per INDIVIDUAL student (SRS §6.8) ──────────────────────────
        # Computed per student as specified, then deduplicated: students who
        # sit exactly the same examinations produce the same constraint, and
        # posting 425 copies of it would be the same model built more slowly.
        # ⚠️ The deduplication is an optimisation, not a change of reading —
        # the sets are built from individuals, so an instance where two
        # students of one group sit different courses still yields two sets.
        sitting: dict[str, set[ExaminationId]] = defaultdict(set)
        for e in exams:
            for student in e.candidates:
                sitting[student].add(e.id)
        for exam_set in {frozenset(s) for s in sitting.values() if len(s) > 1}:
            model.add_all_different([start[eid] for eid in sorted(exam_set)])

        # ── X4 : a supervisor is not in two examinations at once ────────────
        by_supervisor: dict[str, list[ExaminationId]] = defaultdict(list)
        for e in exams:
            by_supervisor[e.supervisor].append(e.id)
        for supervised in by_supervisor.values():
            if len(supervised) > 1:
                model.add_all_different([start[eid] for eid in sorted(supervised)])

        # ── SX1 (soft) : spread a promotion's examinations over the session ──
        # "Penalty on the proximity of two examinations of the same group".
        # Read as: more than one examination of a promotion on one day is what
        # proximity means here. Same shape as the weekly S7 (subject spread),
        # deliberately — a formula the department can recompute by hand.
        day_of_slot = [s.day_index for s in slots]
        distinct_days = sorted({d for d in day_of_slot})
        day_var = {
            e.id: model.new_int_var_from_domain(
                cp_model.Domain.from_values(distinct_days), f"day_{e.id}"
            )
            for e in exams
        }
        for e in exams:
            model.add_element(start[e.id], day_of_slot, day_var[e.id])

        by_promotion: dict[str, list[ExaminationId]] = defaultdict(list)
        for e in exams:
            by_promotion[e.promotion].append(e.id)

        penalties = []
        for promotion, exam_ids in by_promotion.items():
            for day in distinct_days:
                on_day = []
                for eid in exam_ids:
                    flag = model.new_bool_var(f"on_{eid}_{day}")
                    model.add(day_var[eid] == day).only_enforce_if(flag)
                    model.add(day_var[eid] != day).only_enforce_if(flag.negated())
                    on_day.append(flag)
                excess = model.new_int_var(0, len(exam_ids), f"excess_{promotion}_{day}")
                model.add(excess >= sum(on_day) - 1)
                penalties.append(excess)

        # ── Room parsimony : a MECHANISM, not a requirement ──────────────────
        # ⚠️ Found by running the model, and worth keeping the reason. X2 is a
        # COVERING constraint — "sum of the capacities ≥ candidates" — and a
        # covering constraint with no cost attached is free to take everything.
        # The first solve assigned all twenty rooms (882 seats) to a
        # 120-candidate examination: X2 satisfied, and the result useless.
        # Worse than untidy — a room hosts one examination per slot, so an
        # examination holding every room blocks every other examination in that
        # slot and serialises the whole session.
        #
        # This is not a constraint invented beyond SRS §6.8. It is what makes
        # §6.8's own output readable: SRS Table 19 promises "one slot and ONE OR
        # MORE rooms", a phrase that means nothing if the answer is always "all
        # of them", and SRS §5.5's examination view is "the calendar of the
        # session by group and by room".
        #
        # Weighted so SX1 strictly dominates: at most 32 examinations x 20 rooms
        # = 640 assignments, so a weight of 1000 on the spread penalty can never
        # be outbid by room count. Lexicographic in effect, one objective in form.
        room_count = sum(assign.values())
        if penalties:
            model.minimize(1000 * sum(penalties) + room_count)
        else:
            model.minimize(room_count)

        # ── solve ────────────────────────────────────────────────────────────
        solver = cp_model.CpSolver()
        solver.parameters.max_deterministic_time = session.deterministic_budget
        solver.parameters.max_time_in_seconds = self.wall_clock_ceiling_seconds
        solver.parameters.random_seed = session.seed
        solver.parameters.num_workers = self.workers
        # C-16: without this a parallel search is not reproducible even under a
        # fixed seed — workers race and whichever reports first wins.
        solver.parameters.interleave_search = True

        began = time.monotonic()
        status = solver.Solve(model)
        elapsed = time.monotonic() - began

        if status == cp_model.INFEASIBLE:
            return ExamTimetable(
                placements=(),
                spread_penalty=0,
                infeasible=True,
                deterministic_time_used=solver.deterministic_time,
                wall_clock_seconds=elapsed,
            )
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # UNKNOWN. Raised rather than returned as an empty timetable, for
            # the reason C-13 records: a non-answer presented as an answer is
            # how an infeasible instance gets mistaken for a slow model.
            raise ExamSolveFailedError(
                "the examination solve returned neither a timetable nor a proof "
                f"of infeasibility within the budget given ({solver.status_name(status)})"
            )

        placements = tuple(
            ExamPlacement(
                examination=e.id,
                slot=solver.value(start[e.id]),
                rooms=tuple(
                    sorted(
                        (r.id for r in rooms if solver.value(assign[(e.id, r.id)])),
                        key=lambda rid: (len(rid), rid),
                    )
                ),
            )
            for e in exams
        )
        return ExamTimetable(
            placements=placements,
            # Recomputed from the placements, never read from the solver's
            # objective — ADR-011 records that the reported value can sit above
            # the objective at the solution actually returned.
            spread_penalty=spread_penalty(placements, session),
            proven_optimal=status == cp_model.OPTIMAL,
            deterministic_time_used=solver.deterministic_time,
            wall_clock_seconds=elapsed,
        )


class ExamSolveFailedError(Exception):
    """The solve produced neither a timetable nor a proof of infeasibility."""


def spread_penalty(placements: tuple[ExamPlacement, ...], session: ExamSession) -> int:
    """SX1, measured on a finished timetable.

    Public because the acceptance test recomputes it independently of the
    solver, the way the analysis layer recomputes the weekly score from the
    placements rather than trusting CP-SAT's objective.
    """
    day_of_slot = {s.index: s.day_index for s in session.slots}
    promotion_of = {e.id: e.promotion for e in session.examinations}
    counts: dict[tuple[str, int], int] = defaultdict(int)
    for placement in placements:
        counts[(promotion_of[placement.examination], day_of_slot[placement.slot])] += 1
    return sum(max(0, n - 1) for n in counts.values())


__all__ = ["ExamSolveFailedError", "ExamSolver", "spread_penalty"]
