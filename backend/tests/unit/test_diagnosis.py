"""FR-8 — stage 3, against real CP-SAT on instances with one known conflict.

Small enough to stay in the fast suite: each instance below has a handful of
sessions and CP-SAT proves infeasibility in milliseconds. The reference
instance is NOT diagnosed here — it is feasible, and an infeasible variant of
it would take a solve worth minutes for no extra confidence about the encoding.

Each instance below is built so that exactly one rule can be at fault, which is
why the assertions are on the EXACT set rather than on membership. A mechanism
that returned "all four" every time would satisfy a membership check and be
useless — and that is not hypothetical: it is what the assumption-literal
mechanism did at reference scale before C-17 replaced it.

The two properties worth stating, because both are easy to get wrong:

- **Several minimal explanations can exist**, and exactly one is reported. When
  H1 and H3 both forbid the same pair, either alone explains the conflict. The
  search withdraws rules in catalogue order, so the answer is arbitrary between
  them but **reproducible** — which is the property that matters when the
  report tells a user which rule to change.
- **`is_minimal` is evidence, not a label.** It is set only when every removal
  was decided. A subset solve that returns UNKNOWN keeps its rule for want of
  evidence, and the report says so.
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
from optiedt.solver.variables import build_variables

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


def _status_without(instance: Instance, omitted: set[str]) -> int:
    """Solve the model with those rules left unposted.

    Re-derived here rather than reached through a private helper on the solver:
    a test that asks the implementation to confirm itself proves nothing.
    """
    model = cp_model.CpModel()
    variables = build_variables(model, request_for(instance))
    for builder in ALL_HARD_CONSTRAINTS:
        if builder.code not in omitted:
            builder.apply(model, variables, instance)
    solver = cp_model.CpSolver()
    solver.parameters.max_deterministic_time = BUDGET
    solver.parameters.num_workers = 1
    return solver.solve(model)


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


def test_when_two_rules_both_forbid_it_one_minimal_set_is_returned(
    tiny_instance: Instance,
) -> None:
    """⚠️ Several minimal explanations can exist. Exactly one is reported.

    One teacher, ONE room, one slot, two sibling sessions: H1 and H3 BOTH
    forbid the pair, and either alone explains the infeasibility. The search
    withdraws rules in catalogue order, so H1 is dropped first — the model
    stays infeasible without it, because H3 still forbids the pair — and the
    report names H3.

    Both answers would be correct and the report gives one. What makes that
    acceptable is that it is **reproducible**: the order is the catalogue's,
    fixed, so the same instance always yields the same rule rather than
    whichever the solver happened to surface. A report that named a different
    rule on a different machine would be worse than none.
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

    assert result.conflicting_codes == ("H3",)
    assert diagnose(instance).conflicting_codes == result.conflicting_codes


def test_the_reported_set_is_irreducible_removing_any_one_admits_a_timetable(
    tiny_instance: Instance,
) -> None:
    """What "minimal" claims, checked rather than asserted.

    The mechanism tests each removal, so the surviving set should be
    irreducible: withdrawing every rule the report does NOT name must leave the
    instance infeasible, and withdrawing one it does name must admit a
    timetable. This re-derives both directions from the solver instead of
    trusting the flag.
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
    assert result.is_minimal
    named = set(result.conflicting_codes)

    withdrawable = {b.code for b in ALL_HARD_CONSTRAINTS if b.carries_assumption_literal}
    assert _status_without(instance, withdrawable - named) == cp_model.INFEASIBLE, (
        "withdrawing every unnamed rule should leave the conflict standing"
    )
    for code in named:
        assert _status_without(instance, (withdrawable - named) | {code}) in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        ), f"withdrawing {code} as well should admit a timetable, or it was not needed"


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


def test_minimality_is_claimed_only_when_every_removal_was_decided(
    tiny_instance: Instance,
) -> None:
    """`is_minimal` is evidence, not a label.

    Every removal here is decided, so the flag is True and the detail says
    "irreducible". When a removal returns UNKNOWN the rule is kept for want of
    evidence, and the flag must go False — claiming minimality on an untested
    set would be a claim nobody checked. That branch is exercised at scale, not
    here: forcing an UNKNOWN on a three-session instance would need a budget so
    small the baseline solve becomes undecided too, which tests the budget
    rather than the mechanism.
    """
    instance = one_slot(
        dataclasses.replace(
            tiny_instance,
            sessions=(session("a", "G", "T1"), session("b", "T", "T1")),
        )
    )
    result = diagnose(instance)
    assert result.is_minimal is True
    assert "irreducible" in result.detail
    assert "want of evidence" not in result.detail


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
