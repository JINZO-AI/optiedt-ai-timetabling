"""H10 against the real solver: a locked session comes back where it was locked.

`tests/unit/test_solver_variables.py` asserts that the DOMAINS are narrowed.
That is necessary and not sufficient - a narrowed domain the solver never has
to respect would still pass it, and the whole point of H10 is what CP-SAT
returns. So this solves for real and reads the placement back.

⚠️ **Why this file exists at all.** H10 was registered and dormant from Phase 2
until 2026-08-06: `SolverInput` carried `locked_sessions: frozenset[SessionId]`,
a session id with no target, and `build_variables` raised rather than ignore it.
C-19 replaced the field with `frozenset[Placement]`. Until this test passed,
"the solver respects H1-H12" was true of eleven rules.

The locks below are taken from a solve of the SAME instance rather than
invented, which is what a `lock_session` recommendation does (it reads the
target out of the candidate it was proposed against - `recommendations/
translator.py`). Inventing a target risks writing a test that asserts H10
against a placement no timetable would ever contain.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from optiedt.domain.entities import Placement
from optiedt.instance.loader import load_instance
from optiedt.solver.engine import CpSatSolver
from optiedt.solver.interfaces import SolverInput

INSTANCE_PATH = Path(__file__).resolve().parents[3] / "data" / "instance"
SEED = 42

# A feasibility solve with every weight at zero - measured at 2.8-3.3 s wall
# and 0.13-0.21 deterministic units (docs/status.md). The budget is a hang
# backstop with orders of magnitude of headroom, never a tight bound, so a
# failure here is a modelling reason and not a slower machine.
DETERMINISTIC_BUDGET = 60.0
WALL_CLOCK_CEILING = 120.0


@pytest.fixture(scope="module")
def instance():
    return load_instance(INSTANCE_PATH)


def _solve(instance, locked: frozenset[Placement] = frozenset()):
    return CpSatSolver(wall_clock_ceiling_seconds=WALL_CLOCK_CEILING).solve(
        SolverInput(
            instance=instance,
            profile=None,  # type: ignore[arg-type]
            seed=SEED,
            deterministic_budget=DETERMINISTIC_BUDGET,
            locked_placements=locked,
        )
    )


@pytest.fixture(scope="module")
def baseline(instance):
    """One unlocked solve, whose placements are the locks the rest reuse."""
    output = _solve(instance)
    assert not output.infeasible
    return output


@pytest.mark.solver
def test_a_locked_session_keeps_its_slot_and_room(instance, baseline):
    locked = next(p for p in baseline.placements if p.session == "S0001")

    output = _solve(instance, frozenset({locked}))

    assert not output.infeasible
    returned = next(p for p in output.placements if p.session == "S0001")
    assert (returned.slot, returned.room) == (locked.slot, locked.room)


@pytest.mark.solver
def test_locking_does_not_cost_the_other_sessions_their_placement(instance, baseline):
    """All 218 are still placed. A lock removes choices; it must not remove
    solutions that do not depend on the locked session moving."""
    locked = next(p for p in baseline.placements if p.session == "S0001")

    output = _solve(instance, frozenset({locked}))

    assert len(output.placements) == len(instance.sessions) == 218


@pytest.mark.solver
def test_many_locks_at_once_are_all_honoured(instance, baseline):
    """Ten locks spanning several room types, including the cumulative ones.

    One lock could be honoured by luck - the solver might have returned that
    placement anyway. Ten across types cannot, and it exercises the fallback
    from the cumulative encoding to the per-room one, which is the path where
    a lock could silently stop binding (see the unit test of the same name).
    """
    locked = frozenset(sorted(baseline.placements, key=lambda p: p.session)[:10])

    output = _solve(instance, locked)

    assert not output.infeasible
    returned = {p.session: (p.slot, p.room) for p in output.placements}
    for lock in locked:
        assert returned[lock.session] == (lock.slot, lock.room), (
            f"{lock.session} was locked to slot {lock.slot} room {lock.room} "
            f"and came back at {returned[lock.session]}"
        )


@pytest.mark.solver
def test_locking_every_session_reproduces_the_whole_timetable(instance, baseline):
    """The limiting case, and the sharpest statement of what H10 means.

    Lock all 218 placements and the solver has exactly one solution left: the
    timetable it was given. If any lock were being dropped, this is where it
    shows - the returned timetable would differ somewhere and the comparison
    below names the session.
    """
    locked = frozenset(baseline.placements)

    output = _solve(instance, locked)

    assert not output.infeasible
    assert {(p.session, p.slot, p.room) for p in output.placements} == {
        (p.session, p.slot, p.room) for p in baseline.placements
    }
