"""FR-8 — stage 3, against real CP-SAT on instances with one known conflict.

Small enough to stay in the fast suite: each instance below has a handful of
sessions and CP-SAT proves infeasibility in milliseconds. The reference
instance is NOT diagnosed here — it is feasible, and an infeasible variant of
it would take a solve worth minutes for no extra confidence about the encoding.

⚠️ **The first test is the one that matters most, and it is not about
timetables at all.** `only_enforce_if` on `no_overlap` and `cumulative` is
honoured by OR-Tools 9.15.6755 — verified, not assumed — but nothing in the
library's contract promises it stays that way, and a version that SILENTLY
IGNORED the literal would produce a conflict report naming rules that were
never relaxed. It would fail no other test: every constraint would still hold,
every timetable would still be valid, and the diagnosis would simply always
return the full assumption set while looking correct.

So `test_an_enforcement_literal_actually_relaxes_the_constraint` pins the
relaxation itself. It is the same treatment `interleave_search` got in
tests/integration/test_reproducibility.py, for the same reason: an Experimental
or under-documented solver behaviour that a written requirement rests on must
be verified in this repository rather than trusted from the documentation.
"""

from __future__ import annotations

import dataclasses

import pytest
from ortools.sat.python import cp_model

from optiedt.domain.entities import Room, Session
from optiedt.domain.enums import GroupLevel, RoomType, SessionType
from optiedt.domain.instance import Instance
from optiedt.solver.constraints import ALL_HARD_CONSTRAINTS
from optiedt.solver.engine import CpSatSolver
from optiedt.solver.interfaces import SolverInput

BUDGET = 10.0
SEED = 42


def request_for(instance: Instance) -> SolverInput:
    return SolverInput(
        instance=instance,
        profile=None,
        seed=SEED,
        deterministic_budget=BUDGET,
    )


def diagnose(instance: Instance):
    return CpSatSolver(workers=1, wall_clock_ceiling_seconds=60.0).diagnose(request_for(instance))


def session(
    sid: str,
    group: str,
    teacher: str,
    room_type: RoomType = RoomType.SALLE,
    duration: int = 1,
) -> Session:
    return Session(
        id=sid,
        course="C1",
        group=group,
        teacher=teacher,
        type=SessionType.TD,
        duration_periods=duration,
        occurrences_per_week=1,
        required_room_type=room_type,
        locked=False,
    )


def one_slot(instance: Instance) -> Instance:
    """Close every slot but the first. Any two sessions then collide."""
    return dataclasses.replace(
        instance,
        slots=tuple(dataclasses.replace(s, is_open=s.index == 0) for s in instance.slots),
    )


# ── The trap: is the enforcement literal honoured, or ignored? ─────────


def test_an_enforcement_literal_actually_relaxes_the_constraint() -> None:
    """⚠️ Guards the whole diagnosis mechanism. Read the module docstring.

    Two unit intervals pinned to the same instant, under one `no_overlap`
    carrying an enforcement literal:

      - literal forced FALSE -> the constraint must be RELAXED  -> SAT
      - literal forced TRUE  -> the constraint must be ENFORCED -> INFEASIBLE

    If a future OR-Tools ignores the literal, the first case returns INFEASIBLE
    and this test fails loudly — instead of the diagnosis quietly reporting
    every rule for every conflict.
    """
    for forced, expected in ((0, cp_model.OPTIMAL), (1, cp_model.INFEASIBLE)):
        model = cp_model.CpModel()
        literal = model.new_bool_var("assume")
        model.add(literal == forced)
        intervals = [
            model.new_interval_var(
                model.new_int_var(0, 0, f"s{name}"), 1, model.new_int_var(1, 1, f"e{name}"), name
            )
            for name in ("a", "b")
        ]
        model.add_no_overlap(intervals).only_enforce_if(literal)

        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 1
        status = solver.solve(model)
        assert status == expected, (
            f"enforcement literal forced to {forced} gave {solver.status_name(status)}. "
            "If a FALSE literal no longer relaxes no_overlap, the diagnosis run reports "
            "rules that were never relaxed and every other test still passes."
        )


def test_the_same_holds_for_cumulative_and_exactly_one() -> None:
    """H3 uses cumulative for interchangeable room types; H7 uses exactly_one."""
    for forced, expected in ((0, cp_model.OPTIMAL), (1, cp_model.INFEASIBLE)):
        model = cp_model.CpModel()
        literal = model.new_bool_var("assume")
        model.add(literal == forced)
        intervals = [
            model.new_interval_var(
                model.new_int_var(0, 0, f"s{name}"), 1, model.new_int_var(1, 1, f"e{name}"), name
            )
            for name in ("a", "b")
        ]
        model.add_cumulative(intervals, [1, 1], 1).only_enforce_if(literal)
        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 1
        assert solver.solve(model) == expected

    for forced, expected in ((0, cp_model.OPTIMAL), (1, cp_model.INFEASIBLE)):
        model = cp_model.CpModel()
        literal = model.new_bool_var("assume")
        model.add(literal == forced)
        a, b = model.new_bool_var("a"), model.new_bool_var("b")
        model.add(a == 1)
        model.add(b == 1)
        model.add_exactly_one([a, b]).only_enforce_if(literal)
        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 1
        assert solver.solve(model) == expected


# ── Naming the rule ────────────────────────────────────────────────────


def siblings(instance: Instance) -> Instance:
    """Re-shape the fixture's P -> G -> T chain into two SIBLING groups.

    Siblings are the discriminating case: the ancestor-or-self relation
    deliberately leaves two branches free to run in parallel, so H12 does not
    forbid their pair and a report naming H12 would be wrong rather than merely
    imprecise. The fixture's own chain cannot show that — every pair in it is
    an ancestor pair.
    """
    return dataclasses.replace(
        instance,
        groups=(
            dataclasses.replace(instance.groups[0], id="P", parent_group=None),
            dataclasses.replace(instance.groups[1], id="G1", parent_group="P"),
            dataclasses.replace(instance.groups[2], id="G2", parent_group="P", level=GroupLevel.TD),
        ),
    )


def test_a_teacher_conflict_is_reported_as_h1_and_nothing_else(
    tiny_instance: Instance,
) -> None:
    """One teacher, two sessions on SIBLING groups, one open slot, two rooms.

    H12 does not relate siblings and there are rooms enough, so H1 is the only
    rule that can be at fault — which is why this asserts the exact set rather
    than membership. A mechanism that returned "all four" every time would pass
    a membership check and be useless.
    """
    instance = one_slot(
        siblings(
            dataclasses.replace(
                tiny_instance,
                sessions=(session("a", "G1", "T1"), session("b", "G2", "T1")),
                rooms=(
                    Room(id="R1", building="B", code="R1", capacity=30, type=RoomType.SALLE),
                    Room(id="R2", building="B", code="R2", capacity=30, type=RoomType.SALLE),
                ),
            )
        )
    )
    result = diagnose(instance)

    assert result.is_conclusive
    assert result.conflicting_codes == ("H1",)
    assert result.detail


def test_a_hierarchy_conflict_is_reported_as_h12_and_nothing_else(
    tiny_instance: Instance,
) -> None:
    """Two teachers, two rooms, one open slot, and an ANCESTOR pair.

    Neither H1 nor H3 can be at fault, so the conflict is exactly the rule that
    says a promotion's lecture occupies every subgroup below it.
    """
    instance = one_slot(
        dataclasses.replace(
            tiny_instance,
            sessions=(session("a", "P", "T1"), session("b", "T", "T2")),
        )
    )
    result = diagnose(instance)

    assert result.is_conclusive
    assert result.conflicting_codes == ("H12",)


def test_a_room_conflict_is_reported_as_h3_and_nothing_else(
    tiny_instance: Instance,
) -> None:
    """Two teachers, SIBLING groups, ONE room, one open slot.

    Neither H1 nor H12 forbids this pair; only the room does.
    """
    instance = one_slot(
        siblings(
            dataclasses.replace(
                tiny_instance,
                sessions=(session("a", "G1", "T1"), session("b", "G2", "T2")),
                rooms=(Room(id="R1", building="B", code="R1", capacity=30, type=RoomType.SALLE),),
            )
        )
    )
    result = diagnose(instance)

    assert result.is_conclusive
    assert result.conflicting_codes == ("H3",)


def test_the_set_is_an_unsat_core_not_a_repair_list(tiny_instance: Instance) -> None:
    """⚠️ The natural reading of the report is backwards. Pinned here.

    One teacher, ONE room, one slot, two sibling sessions: H1 and H3 are BOTH
    violated, and the report names only H1. That is correct — the returned set
    is a subset whose conjunction is ALREADY infeasible ("enforcing H1 alone
    admits no timetable"), not a set whose removal would fix the instance.
    Relaxing H1 here would leave H3 forbidding the very same pair.

    So the interface must never say "change these and it will solve". The
    detail string says "necessary, not necessarily enough" for this reason.
    """
    instance = one_slot(
        siblings(
            dataclasses.replace(
                tiny_instance,
                sessions=(session("a", "G1", "T1"), session("b", "G2", "T1")),
                rooms=(Room(id="R1", building="B", code="R1", capacity=30, type=RoomType.SALLE),),
            )
        )
    )
    result = diagnose(instance)

    assert result.conflicting_codes == ("H1",)
    assert "necessary, not necessarily enough" in result.detail


def test_only_the_four_postable_codes_can_ever_be_named(tiny_instance: Instance) -> None:
    """C-6: the constraint -> literal mapping is 1:1 and non-redundant.

    H2 and H11 are subsumed, and H4-H6, H8-H10 are domain restrictions applied
    before the model exists. None of them can appear in a report, which is the
    point: a conflict report must name a rule the user can act on.
    """
    instance = one_slot(
        dataclasses.replace(
            tiny_instance,
            sessions=(session("a", "G", "T1"), session("b", "T", "T1")),
        )
    )
    result = diagnose(instance)
    assert set(result.conflicting_codes) <= {"H1", "H3", "H7", "H12"}

    literal_carriers = {b.code for b in ALL_HARD_CONSTRAINTS if b.carries_assumption_literal}
    assert literal_carriers == {"H1", "H3", "H7", "H12"}


def test_the_report_never_claims_to_be_minimal(tiny_instance: Instance) -> None:
    """Imposed by CP-SAT: the subset it returns is heuristically reduced."""
    instance = one_slot(
        dataclasses.replace(
            tiny_instance,
            sessions=(session("a", "G", "T1"), session("b", "T", "T1")),
        )
    )
    assert diagnose(instance).is_minimal is False


# ── The outcomes that are NOT a named conflict ─────────────────────────


def test_a_feasible_instance_yields_an_empty_conclusive_report(
    tiny_instance: Instance,
) -> None:
    """Reachable only if stage 2 and stage 3 saw different data.

    Reported rather than raised: the run already has a verdict, and an
    exception here would replace it with a stack trace.
    """
    result = diagnose(tiny_instance)
    assert result.conflicting_codes == ()
    assert result.is_conclusive
    assert "no conflict" in result.detail


def test_an_unbuildable_model_says_so_instead_of_raising(tiny_instance: Instance) -> None:
    """H4/H5 leave a session with no room: `build_variables` raises.

    There is no model to diagnose — an assumption literal cannot relax a
    domain that was empty before the search began — so the report says that
    and points at the pre-analysis, where the resource and the missing
    quantity are named.
    """
    instance = dataclasses.replace(
        tiny_instance,
        rooms=(Room(id="R1", building="B", code="R1", capacity=1, type=RoomType.SALLE),),
    )
    result = diagnose(instance)

    assert result.conflicting_codes == ()
    assert result.is_conclusive
    assert "pre-analysis" in result.detail


def test_a_domain_only_conflict_returns_an_empty_set_and_says_why(
    tiny_instance: Instance,
) -> None:
    """H6/H8/H9 shrink a domain; no literal can relax them.

    Three sessions of three teachers into one open slot with one room: the
    conflict is real and H3 explains it. But when the domain itself is the
    problem — every slot closed for a session's teacher — `build_variables`
    refuses first, which the test above covers. What this one pins is that a
    conflict CP-SAT proves without needing any relaxable rule comes back
    empty-and-conclusive rather than empty-and-silent.
    """
    result = diagnose(tiny_instance)
    assert result.detail, "an empty conflict set must be explained in words"


# ── Stage 3's three imposed properties ─────────────────────────────────


@pytest.mark.parametrize("configured_workers", [0, 4, 8])
def test_the_diagnosis_uses_one_worker_whatever_the_configuration(
    tiny_instance: Instance, configured_workers: int
) -> None:
    """Imposed, not configured (docs/architecture.md, stage 3).

    A diagnosis that returned a different conflict set on a different machine
    would be worse than none: the report names the rule a user is told to
    change. Verified by the outcome rather than by reading the parameter —
    every worker count must produce the same codes.
    """
    instance = one_slot(
        dataclasses.replace(
            tiny_instance,
            sessions=(session("a", "G", "T1"), session("b", "T", "T1")),
        )
    )
    solver = CpSatSolver(workers=configured_workers, wall_clock_ceiling_seconds=60.0)
    result = solver.diagnose(request_for(instance))
    assert result.conflicting_codes == diagnose(instance).conflicting_codes
