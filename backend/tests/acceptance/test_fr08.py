"""FR-8 — report the rules in conflict when no timetable exists.

    Acceptance criterion (docs/testing-strategy.md §4):
    "Generate on a deliberately infeasible instance → report naming the rules
    in conflict by code."

    And the criterion in docs/status.md:
    "An instance without a solution produces a report naming the rules in
    conflict."

⚠️ **This criterion is met on one shape of infeasibility and not on the other,
and that is the honest result rather than a gap in the tests.** Both shapes are
exercised here because writing only the first would let the suite report a
capability the product does not have:

- **The AREA case** - computer laboratories withdrawn, so demand exceeds
  rooms x periods. `AddCumulative` reasons about area directly, CP-SAT proves
  it, and the run reaches `DIAGNOSED` naming `('H3',)`. **Criterion met.**
- **The CONTIGUITY case** - the pre-C-13 room mix. The instance has no solution
  and CP-SAT cannot construct the proof, so stage 2 returns `UNKNOWN`, the
  engine refuses to pass that off as an answer, and the run lands in `FAILED`.
  **No conflict report is produced at all**, and the pre-analysis is what names
  the resource. **Criterion not met on this shape.**

`docs/requirements-traceability.md` already carries the instruction this file
obeys: *"Do not write the acceptance test as though stage 3 always produces
codes."*
"""

from __future__ import annotations

import pytest

from optiedt.api import deps
from tests.acceptance.conftest import (
    keeping_only_computer_laboratories,
    real_solver_factory,
    the_original_room_mix,
    wire_application,
)

pytestmark = [pytest.mark.acceptance, pytest.mark.solver]

#: The area case is proved at presolve, so the budget does not bind on it.
#: On the contiguity case NO budget suffices - see the note on that fixture.
DIAGNOSIS_BUDGET = 9.0


def _run_against(instance_builder) -> dict[str, object]:
    deps.get_instance.cache_clear()
    instance = instance_builder(deps.get_instance())
    with wire_application(real_solver_factory(), instance_provider=lambda: instance) as application:
        return application.launch(seed=42, deterministicBudget=DIAGNOSIS_BUDGET)


@pytest.fixture(scope="module")
def area_case() -> dict[str, object]:
    """Four computer laboratories kept of eight: 160 periods against 112."""
    return _run_against(lambda i: keeping_only_computer_laboratories(i, 4))


@pytest.fixture(scope="module")
def contiguity_case() -> dict[str, object]:
    """The pre-C-13 mix. Measured at 100.8 s before CP-SAT gives up.

    ⚠️ This test does NOT establish that CP-SAT can never prove this
    infeasibility - it runs at one budget, and a single budget cannot support a
    claim about every budget. What establishes it is the recorded measurement:
    480 s returning `UNKNOWN`, and the same shape re-measured under C-17. What
    this test does establish is the part that matters to a user: the run does
    not present a non-answer as a timetable, and the pre-analysis says what is
    wrong.
    """
    return _run_against(the_original_room_mix)


# ── the area case: the criterion, met ──────────────────────────────────


def test_an_infeasible_instance_reaches_diagnosed(area_case: dict[str, object]) -> None:
    """PENDING → PREANALYSIS → SOLVING → INFEASIBLE → DIAGNOSING → DIAGNOSED.

    Not `FAILED`, and not `COMPLETED` with an empty portfolio: "no timetable
    exists" is an answer, and the lifecycle has a state for it.
    """
    assert area_case["state"] == "DIAGNOSED", f"error={area_case['error']}"


def test_the_report_names_the_rules_in_conflict_by_code(
    area_case: dict[str, object],
) -> None:
    """The criterion's exact words. `('H3',)` on this instance, every time."""
    diagnosis = area_case["diagnosis"]

    assert diagnosis is not None
    assert diagnosis["conflictingCodes"] == ["H3"]


def test_the_named_rule_is_one_a_user_could_act_on(
    area_case: dict[str, object],
) -> None:
    """Only H1, H3, H7 and H12 may be named, and that is C-6's whole point.

    H2 and H11 are subsumed; H4-H6 and H8-H10 are domain restrictions applied
    when the variable is built, so there is nothing posted to withdraw. A
    report naming one of those would be naming a rule the user cannot change.
    """
    diagnosis = area_case["diagnosis"]

    assert set(diagnosis["conflictingCodes"]) <= {"H1", "H3", "H7", "H12"}


def test_the_report_claims_minimality_only_because_it_was_tested(
    area_case: dict[str, object],
) -> None:
    """`isMinimal` is evidence, not a label (C-17).

    Each rule is withdrawn and the model re-solved, so the surviving set is
    irreducible - but a withdrawal the solver could not decide keeps its rule
    for want of evidence, and then the flag must be false. Here every removal
    was decided.
    """
    diagnosis = area_case["diagnosis"]

    assert diagnosis["isConclusive"] is True
    assert diagnosis["isMinimal"] is True
    assert "irreducible" in diagnosis["detail"].lower()


def test_the_report_says_what_minimal_does_not_mean(
    area_case: dict[str, object],
) -> None:
    """Irreducible among the four WITHDRAWABLE rules, with all the others
    enforced - not the smallest explanation in any absolute sense."""
    assert "withdrawable" in area_case["diagnosis"]["detail"]


def test_the_pre_analysis_is_recorded_beside_the_conflict_report(
    area_case: dict[str, object],
) -> None:
    """Both, not either.

    The conflict report names a rule; the pre-analysis names the resource and
    the quantity. A user needs the second to know what to change, and stage 1
    runs whatever stage 2 later decides.
    """
    checks = area_case["preAnalysis"]
    coverage = next(c for c in checks if c["name"] == "SLOT_COVERAGE")

    assert coverage["passed"] is False
    assert coverage["resource"] == "Lab_Info"


# ── the contiguity case: the limit, stated ─────────────────────────────


def test_an_unprovable_infeasibility_does_not_produce_a_false_report(
    contiguity_case: dict[str, object],
) -> None:
    """⚠️ **The criterion is NOT met on this shape, and this test says so.**

    The instance has no solution. CP-SAT cannot construct the proof - the
    obstruction is contiguity, which its propagators do not express - so stage
    2 returns `UNKNOWN` and `solver/engine.py` RAISES rather than reporting it
    as a normal result. The run lands in `FAILED` with the reason recorded.

    That is the correct behaviour and the C-13 lesson working: an `UNKNOWN` is
    never quietly passed off as an answer. It is also, plainly, not a report
    naming the rules in conflict.
    """
    assert contiguity_case["state"] == "FAILED"
    assert contiguity_case["diagnosis"] is None
    assert "UNKNOWN" in str(contiguity_case["error"])


def test_the_run_says_why_rather_than_timing_out_silently(
    contiguity_case: dict[str, object],
) -> None:
    """ "Rather than a timeout" is the phrase the phase's purpose uses.

    The user gets a stated reason and an instruction, not a spinner that stops.
    """
    error = str(contiguity_case["error"])

    assert "neither a solution nor a proof" in error
    assert "budget" in error


def test_the_pre_analysis_names_the_resource_the_solver_could_not(
    contiguity_case: dict[str, object],
) -> None:
    """⚠️ **This is what carries the criterion's intent on this shape.**

    Stage 1 catches in milliseconds what stage 2 cannot prove in 100 seconds:
    computer laboratories short by 14 two-period windows, science laboratories
    by 2. The report is still recorded on a run that afterwards FAILED, which
    is exactly why `tasks/executor.py` saves it before solving.
    """
    coverage = next(c for c in contiguity_case["preAnalysis"] if c["name"] == "SLOT_COVERAGE")

    assert coverage["passed"] is False
    assert coverage["resource"] == "Lab_Info"
    assert coverage["missingQuantity"] == pytest.approx(14.0)
    assert "short by 14 2-period windows" in coverage["detail"]
