"""The recommendation catalogue and its translation.

⚠️ **The Phase 6 closing audit found this package had ZERO test coverage**, and
that a document claimed otherwise: the dashboard said the catalogue and
translation "exist and are tested". No test imported `optiedt.recommendations`.
The claim survived because `recommend()` in `analysis/ranking.py` *is* tested
and carries a similar name.

These are the first tests it has. They pin the two things ADR-007 and invariant
3 actually promise:

- the catalogue is **closed** - three actions, and a translation that cannot
  silently produce a fourth kind of thing;
- a `lock_session` reads its target **out of the candidate**, so H10 locks a
  session to where it already is rather than to somewhere a caller chose.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from optiedt.domain.entities import Candidate, Placement, Run, SubScore
from optiedt.domain.enums import RunState
from optiedt.recommendations.catalogue import ExcludeSlot, LockSession, WeightDelta
from optiedt.recommendations.translator import (
    DefaultRecommendationTranslator,
    ExcludedOption,
    LockedPlacement,
    UnresolvedLockTargetError,
    WeightOverride,
)


@pytest.fixture
def run():
    return Run(
        id="r1",
        created_at=datetime(2026, 8, 6, tzinfo=UTC),
        seed=42,
        deterministic_budget=90.0,
        state=RunState.COMPLETED,
        model_version="weekly.h1-h12.s2-s10",
    )


@pytest.fixture
def candidate():
    return Candidate(
        id="c1",
        run="r1",
        profile_name="balanced",
        cost=100,
        score=80.0,
        placements=(
            Placement(session="S0001", slot=7, room="2"),
            Placement(session="S0002", slot=3, room="4"),
        ),
        sub_scores=(SubScore(criterion="S2", raw_value=5.0, normalised=0.9),),
    )


@pytest.fixture
def translator():
    return DefaultRecommendationTranslator()


# ── the three actions ──────────────────────────────────────────────────


def test_weight_delta_becomes_a_weight_override(translator, run, candidate):
    result = translator.translate(WeightDelta(criterion="S3", new_weight=0.30), run, candidate)
    assert result == WeightOverride(criterion="S3", new_weight=0.30)


def test_lock_session_reads_its_target_out_of_the_candidate(translator, run, candidate):
    """The point of the whole action: H10 fixes start[s] and room[s] to the
    values they ALREADY hold, so the target comes from the candidate the
    recommendation was proposed against and from nowhere else."""
    result = translator.translate(LockSession(session="S0001"), run, candidate)
    assert result == LockedPlacement(session="S0001", slot=7, room="2")


def test_lock_session_on_an_absent_session_refuses(translator, run, candidate):
    """Rather than inventing a target. There is no other source for it."""
    with pytest.raises(UnresolvedLockTargetError, match="has no placement in candidate"):
        translator.translate(LockSession(session="S9999"), run, candidate)


def test_exclude_slot_carries_a_slot(translator, run, candidate):
    result = translator.translate(ExcludeSlot(session="S0001", slot=7), run, candidate)
    assert result == ExcludedOption(session="S0001", slot=7, room=None)


def test_exclude_slot_carries_a_room(translator, run, candidate):
    result = translator.translate(ExcludeSlot(session="S0001", room="2"), run, candidate)
    assert result == ExcludedOption(session="S0001", slot=None, room="2")


# ── what the catalogue promises ────────────────────────────────────────


def test_translation_needs_nothing_from_the_run(translator, candidate):
    """`translate` takes a Run and uses none of it - the parameter exists
    because the Protocol declares it.

    Asserted rather than left to the `del run` line, because if translation
    ever DID depend on the run, the two would silently disagree about which
    run a chained recommendation belongs to."""
    other = Run(
        id="completely-different",
        created_at=datetime(2020, 1, 1, tzinfo=UTC),
        seed=999,
        deterministic_budget=1.0,
        state=RunState.FAILED,
        model_version="something-else",
    )
    action = LockSession(session="S0001")
    assert translator.translate(action, other, candidate) == LockedPlacement("S0001", 7, "2")


def test_every_action_carries_its_kind_discriminator():
    """The wire format and `RunOrigin.action_kind` both read this. A variant
    whose kind did not match its type would record the wrong provenance."""
    assert WeightDelta().kind == "weight_delta"
    assert LockSession().kind == "lock_session"
    assert ExcludeSlot().kind == "exclude_slot"


def test_a_translated_action_is_never_a_placement(translator, run, candidate):
    """Invariant 2, at this package's boundary.

    `LockedPlacement` names a placement and is NOT one: it is an instruction
    to the solver to reproduce one. Nothing here returns a `Placement`, which
    is the type the solver writes. If this ever fails, `recommendations` has
    started producing timetable content rather than solver input.
    """
    for action in (
        WeightDelta(criterion="S3", new_weight=0.3),
        LockSession(session="S0001"),
        ExcludeSlot(session="S0001", slot=7),
    ):
        assert not isinstance(translator.translate(action, run, candidate), Placement)
