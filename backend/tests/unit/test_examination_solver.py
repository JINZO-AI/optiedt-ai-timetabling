"""The examination model's rules, each on an instance where it is the ONLY
thing standing between the solver and a violation.

⚠️ **This file exists because a mutation survived.** Deleting X4 from
`examination/solver.py` left `acceptance/test_fr20.py` entirely green. The
reason is instructive rather than embarrassing: the reference session has 55
slots for 32 examinations and SX1 actively pushes a promotion's examinations
apart, so the solver avoids supervisor collisions **whether or not X4 is
posted**. The acceptance test was therefore proving that one optimal solution
happened to satisfy X4, not that X4 is enforced — a test passing for the right
answer and the wrong reason, which is the third time this project has caught
that shape (Phase 11's holiday fixture, Phase 12's compatibility guard).

The technique here is the one `unit/test_diagnosis.py` uses: **instances
designed so exactly one rule can be at fault.** Each session below is small
enough that the constraint under test is load-bearing — remove it and the
solver has both the freedom and the incentive to violate it.

These are unit tests over the solver, not acceptance tests: they do not go
through the API, and they say so rather than claiming a standing they do not
have. `acceptance/test_fr20.py` is FR-20's evidence; this file is what makes
that evidence mean something.

⚠️ **One mutation is NOT detected here and is recorded rather than hidden.**
Lowering SX1's objective weight from 1000 to 1 leaves every test below green.
That is honest: the weight exists to keep SX1 strictly above room count *when
the two conflict*, and on sessions small enough for one rule to be isolated
they never do — every examination needs exactly one room wherever it sits, so
room cost is constant across arrangements. Constructing a conflict needs a
session where a spread arrangement forces an examination to split across two
rooms, which is several interacting rules at once and would stop being the
one-rule-at-a-time instrument this file is. The bound itself is arithmetic and
stated where the weight is set: at most 32 examinations x 20 rooms = 640
assignments, so 1000 cannot be outbid. Same treatment as FR-16's unfirable
dominance assertion — named in the file that would have caught it.
"""

from __future__ import annotations

from datetime import date

import pytest

from optiedt.domain.entities import Room
from optiedt.domain.enums import RoomType
from optiedt.domain.examination import Examination, ExamSession, ExamSlot
from optiedt.examination.solver import ExamSolver, spread_penalty


def room(identifier: str, capacity: int) -> Room:
    return Room(
        id=identifier,
        building="B",
        code=identifier,
        capacity=capacity,
        type=RoomType.SALLE,
        equipment=(),
    )


def slots(count: int, per_day: int = 1) -> tuple[ExamSlot, ...]:
    return tuple(
        ExamSlot(
            index=i,
            day_index=i // per_day,
            period_index=i % per_day,
            day=date(2026, 6, 8),
        )
        for i in range(count)
    )


def exam(
    identifier: str,
    *,
    promotion: str = "P",
    supervisor: str = "T",
    candidates: int = 1,
) -> Examination:
    return Examination(
        id=identifier,
        course=identifier,
        promotion=promotion,
        supervisor=supervisor,
        candidates=tuple(f"{identifier}-s{n}" for n in range(candidates)),
    )


SOLVER = ExamSolver(workers=1, wall_clock_ceiling_seconds=60.0)
"""One worker: these models are tiny and a fixed verdict matters more than
speed. Every solve below also fixes a seed and a deterministic budget, because
a test bounded by wall clock passes on one machine and fails on another."""


def solve(session: ExamSession, rooms: tuple[Room, ...]):
    return SOLVER.solve(session, rooms)


# ── X4 — the rule whose mutation survived ──────────────────────────────


def test_x4_alone_makes_one_supervisor_with_two_examinations_and_one_slot_infeasible() -> None:
    """ONE slot, TWO examinations, ONE supervisor, TWO free rooms.

    ⚠️ **Infeasibility rather than "they landed in different slots", and the
    difference is the whole lesson of this file.** A placement assertion here
    passed even with X4 deleted, because nothing pushed the solver towards the
    collision and it tie-broke apart on its own. Infeasibility cannot pass by
    luck: either X4 forbids the arrangement or a timetable exists.

    Everything else that could explain the refusal is removed: the two
    examinations are of **different promotions** (so X1 does not separate them
    and SX1 does not price them), they share **no student**, and there are
    **two rooms** for two one-candidate examinations. Only X4 is left.
    """
    session = ExamSession(
        examinations=(
            exam("A", promotion="P1", supervisor="T1"),
            exam("B", promotion="P2", supervisor="T1"),
        ),
        slots=slots(1, per_day=1),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 10)))

    assert timetable.infeasible, "X4 is not enforced: one supervisor sat two examinations at once"
    assert timetable.placements == ()


def test_two_supervisors_make_the_same_session_feasible() -> None:
    """The control for the test above, and it is not a formality.

    Without it, a solver that returned INFEASIBLE for some unrelated reason —
    a bad room model, an empty slot list — would make the X4 test pass while
    proving nothing. Change one supervisor and the identical session solves.
    """
    session = ExamSession(
        examinations=(
            exam("A", promotion="P1", supervisor="T1"),
            exam("B", promotion="P2", supervisor="T2"),
        ),
        slots=slots(1, per_day=1),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 10)))

    assert not timetable.infeasible
    assert len(timetable.placements) == 2


def test_x4_makes_a_session_infeasible_when_a_supervisor_has_more_exams_than_slots() -> None:
    """Three examinations, one supervisor, two slots. No arrangement exists.

    The sharpest statement available: X4 is not merely respected here, it is
    what makes the answer INFEASIBLE. A model that dropped it would return a
    timetable.
    """
    session = ExamSession(
        examinations=(
            exam("A", promotion="P1", supervisor="T1"),
            exam("B", promotion="P2", supervisor="T1"),
            exam("C", promotion="P3", supervisor="T1"),
        ),
        slots=slots(2, per_day=2),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 10), room("r3", 10)))

    assert timetable.infeasible
    assert timetable.placements == ()


# ── X1 — per individual student ────────────────────────────────────────


def test_x1_alone_makes_one_student_with_two_examinations_and_one_slot_infeasible() -> None:
    """One shared candidate, one slot, two rooms, two supervisors.

    ⚠️ **This is what makes X1 per-STUDENT rather than per-promotion**, and it
    is the case that distinguishes the two readings: the examinations are of
    different promotions, so a model reasoning on promotions alone would place
    them together — and would be wrong for exactly the reason SRS §6.8 gives,
    *"two students of the same group may present different optional courses"*.
    The only thing linking them is student `e1`.

    Infeasibility rather than a placement assertion, for the reason recorded
    at the head of this file.
    """
    session = ExamSession(
        examinations=(
            Examination(id="A", course="A", promotion="P1", supervisor="T1", candidates=("e1",)),
            Examination(id="B", course="B", promotion="P2", supervisor="T2", candidates=("e1",)),
        ),
        slots=slots(1, per_day=1),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 10)))

    assert timetable.infeasible, "X1 is not enforced per student"


def test_two_different_students_make_the_same_session_feasible() -> None:
    """The control: change the shared candidate and the session solves."""
    session = ExamSession(
        examinations=(
            Examination(id="A", course="A", promotion="P1", supervisor="T1", candidates=("e1",)),
            Examination(id="B", course="B", promotion="P2", supervisor="T2", candidates=("e2",)),
        ),
        slots=slots(1, per_day=1),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 10)))

    assert not timetable.infeasible
    assert len(timetable.placements) == 2


def test_x1_is_infeasible_when_one_student_has_more_examinations_than_slots() -> None:
    session = ExamSession(
        examinations=(
            Examination(id="A", course="A", promotion="P1", supervisor="T1", candidates=("e1",)),
            Examination(id="B", course="B", promotion="P2", supervisor="T2", candidates=("e1",)),
            Examination(id="C", course="C", promotion="P3", supervisor="T3", candidates=("e1",)),
        ),
        slots=slots(2, per_day=2),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 10), room("r3", 10)))

    assert timetable.infeasible


# ── X2 — the capacity SUM, which is R-6 ────────────────────────────────


def test_x2_an_examination_larger_than_any_room_is_covered_by_a_sum_of_rooms() -> None:
    """R-6 in its smallest form: 30 candidates, no room above 20.

    The only way to satisfy X2 is to assign two rooms — *"the assignment of the
    rooms becomes a sum of capacities and not the choice of a single room"*.
    """
    session = ExamSession(
        examinations=(exam("A", candidates=30),),
        slots=slots(2, per_day=2),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 20), room("r2", 20)))

    assert not timetable.infeasible
    placement = timetable.placements[0]
    assert len(placement.rooms) == 2
    assert sum(20 for _ in placement.rooms) >= 30


def test_x2_is_infeasible_when_every_room_together_cannot_seat_the_candidates() -> None:
    session = ExamSession(
        examinations=(exam("A", candidates=100),),
        slots=slots(2, per_day=2),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 20), room("r2", 20)))

    assert timetable.infeasible


def test_a_room_is_not_given_to_two_examinations_in_one_slot() -> None:
    """One room, one slot, two examinations that are otherwise free to share it.

    Different promotions, different supervisors, no shared student — X1 and X4
    both permit the collision, so only the per-room NoOverlap forbids it. The
    examination counterpart of H3.
    """
    session = ExamSession(
        examinations=(
            exam("A", promotion="P1", supervisor="T1", candidates=10),
            exam("B", promotion="P2", supervisor="T2", candidates=10),
        ),
        slots=slots(1, per_day=1),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("only", 10),))

    assert timetable.infeasible, "one room hosted two examinations in one slot"


# ── room parsimony — the mechanism, not a requirement ──────────────────


def test_no_more_rooms_are_taken_than_the_candidates_need() -> None:
    """The defect that made the first working model useless.

    X2 is a covering constraint, so without a cost the solver is free to take
    every room. It did: twenty rooms, 882 seats, for 120 candidates. This pins
    the fix — and it is why the objective carries a room term at all.
    """
    session = ExamSession(
        examinations=(exam("A", candidates=10),),
        slots=slots(2, per_day=2),
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 50), room("r3", 50)))

    assert len(timetable.placements[0].rooms) == 1


# ── SX1 — the soft criterion ───────────────────────────────────────────


def test_sx1_spreads_a_promotion_across_days_when_clustering_was_available() -> None:
    """TWO days of TWO periods, and two examinations of one promotion.

    ⚠️ **The choice is what makes this test bind, and its first version did
    not have one.** With two days of ONE period, X1 alone forces the two
    examinations onto different days and the penalty is 0 whether or not SX1
    is posted — the test passed with the objective deleted. Here four slots
    admit three shapes: both on day 0 (penalty 1), both on day 1 (penalty 1),
    or one on each (penalty 0). Room cost is identical in all three, because
    each examination needs exactly one room wherever it sits, so **nothing but
    SX1 can prefer the spread one.**
    """
    session = ExamSession(
        examinations=(
            exam("A", promotion="P1", supervisor="T1"),
            exam("B", promotion="P1", supervisor="T2"),
        ),
        slots=slots(4, per_day=2),  # two days, two periods each
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 10)))

    assert not timetable.infeasible
    assert timetable.spread_penalty == 0, (
        "SX1 is not being optimised: the two examinations of one promotion "
        "share a day when a spread arrangement of equal room cost existed"
    )
    days = {p.slot // 2 for p in timetable.placements}
    assert len(days) == 2


def test_sx1_is_reported_rather_than_enforced_when_the_session_is_too_short() -> None:
    """⚠️ SX1 is SOFT and must never make a session infeasible.

    Three examinations of one promotion into a single day of three periods:
    X1 still separates them, so a timetable exists, and the penalty is 2 —
    reported, not refused. A soft criterion that blocked a solve would be a
    hard constraint wearing the wrong label.
    """
    session = ExamSession(
        examinations=(
            exam("A", promotion="P1", supervisor="T1"),
            exam("B", promotion="P1", supervisor="T2"),
            exam("C", promotion="P1", supervisor="T3"),
        ),
        slots=slots(3, per_day=3),  # one day, three periods
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 10), room("r3", 10)))

    assert not timetable.infeasible
    assert len(timetable.placements) == 3
    assert timetable.spread_penalty == 2
    assert spread_penalty(timetable.placements, session) == 2


def test_the_reported_penalty_is_recomputed_from_the_placements() -> None:
    """ADR-011: the solver's own objective value is not what is reported."""
    session = ExamSession(
        examinations=(
            exam("A", promotion="P1", supervisor="T1"),
            exam("B", promotion="P1", supervisor="T2"),
        ),
        slots=slots(2, per_day=2),  # one day, two periods -> penalty 1
        seed=42,
        deterministic_budget=5.0,
    )

    timetable = solve(session, (room("r1", 10), room("r2", 10)))

    assert timetable.spread_penalty == spread_penalty(timetable.placements, session)


# ── determinism ────────────────────────────────────────────────────────


@pytest.mark.solver
def test_two_solves_of_one_session_agree() -> None:
    """C-16 and ADR-011 applied to the examination model: a deterministic
    budget bounds the work and `interleave_search` orders the race."""
    from optiedt.examination.derive import derive_examination_session
    from optiedt.instance.loader import load_instance, resolve_instance_path

    instance = load_instance(resolve_instance_path("../data/instance"))
    session = derive_examination_session(instance, seed=42, deterministic_budget=10.0)

    first = ExamSolver(workers=4).solve(session, instance.rooms)
    second = ExamSolver(workers=4).solve(session, instance.rooms)

    assert first.placements == second.placements
    assert first.spread_penalty == second.spread_penalty
