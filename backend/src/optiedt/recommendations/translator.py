"""Concrete RecommendationTranslator: the one-input delta an accepted
recommendation produces for the next run.

Returns a ``RunOverride`` - plain domain-typed data - rather than an
``optiedt.solver.interfaces.SolverInput``, even though catalogue.py's module
docstring calls this package's job "translation to solver input" and
docs/architecture.md's module map lists ``recommendations`` as depending only
on ``domain`` and ``analysis``. Both readings run into the same wall: the
``RecommendationTranslator.translate(action, run, candidate)`` signature
receives a ``Run`` (id, seed, budget, state, model_version - no instance, no
profile weights) and a ``Candidate`` (placements, sub_scores, profile_name -
a NAME, not the weights dict) and nothing else. Neither carries the
``Instance`` a ``SolverInput`` needs, the base profile's weights to carry
forward, or any locks/exclusions accumulated by earlier recommendations on
the same run. A translator built strictly from this signature cannot
assemble a complete ``SolverInput`` - that assembly needs run/instance
context that only a higher layer (``services/``, Phase 4-5) has today. This
is a real gap in the existing interfaces, recorded alongside C-4/C-12 in
docs/open-questions.md, not a design choice specific to this module.

So ``translate()`` returns the delta as plain domain data and leaves final
``SolverInput`` assembly to that later layer - which is exactly what
catalogue.py's deliberately vague ``-> object`` return type leaves room for.

``lock_session`` in particular only becomes useful once solver/variables.py
gains a way to carry a locked session's TARGET slot/room (see that module's
own docstring on ``SolverInput.locked_sessions`` - it accepts only session
ids today, which is why it refuses to build if that set is non-empty). That
is out of scope here (solver/variables.py, solver/interfaces.py); this
module still translates lock_session correctly against the schema as it
stands, reading the target straight out of the candidate's own placement,
which is what H10 means by "fixes start[s] and room[s] to their current
value" (docs/ai-integration.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from optiedt.domain.entities import (
    Candidate,
    ConstraintCode,
    Placement,
    RoomId,
    Run,
    SessionId,
    SlotIndex,
)
from optiedt.recommendations.catalogue import (
    ExcludeSlot,
    LockSession,
    RecommendationAction,
    WeightDelta,
)


@dataclass(frozen=True, slots=True)
class WeightOverride:
    """``weight_delta``, packaged: replace one weight of the profile in force."""

    criterion: ConstraintCode
    new_weight: float


@dataclass(frozen=True, slots=True)
class LockedPlacement:
    """``lock_session``, packaged: the session's CURRENT slot and room, read
    from the candidate the recommendation was proposed against."""

    session: SessionId
    slot: SlotIndex
    room: RoomId


@dataclass(frozen=True, slots=True)
class ExcludedOption:
    """``exclude_slot``, packaged: one (session, slot) or (session, room)
    pair to withdraw from candidacy before the next run. Exactly one of
    ``slot``/``room`` is set, mirroring ``ExcludeSlot`` itself."""

    session: SessionId
    slot: SlotIndex | None
    room: RoomId | None


type RunOverride = WeightOverride | LockedPlacement | ExcludedOption
"""The one changed input a translated recommendation produces - closed, like
``RecommendationAction`` itself. A later layer merges this into a fresh
``SolverInput`` alongside the run's instance, seed, budget and any prior
overrides; this module has access to none of those."""


class UnresolvedLockTargetError(Exception):
    """Raised when ``lock_session`` names a session absent from the
    candidate it was proposed against - the translator has no other source
    for that session's current slot/room."""


@dataclass(frozen=True, slots=True)
class DefaultRecommendationTranslator:
    """Implements ``RecommendationTranslator`` (recommendations/catalogue.py)."""

    def translate(
        self, action: RecommendationAction, run: Run, candidate: Candidate
    ) -> RunOverride:
        del run  # Unused: nothing in Run is needed to translate any of the three actions.
        if isinstance(action, WeightDelta):
            return WeightOverride(criterion=action.criterion, new_weight=action.new_weight)
        if isinstance(action, LockSession):
            placement = _placement_for(action.session, candidate)
            return LockedPlacement(session=action.session, slot=placement.slot, room=placement.room)
        if isinstance(action, ExcludeSlot):
            return ExcludedOption(session=action.session, slot=action.slot, room=action.room)
        assert_never(action)


def _placement_for(session_id: SessionId, candidate: Candidate) -> Placement:
    for placement in candidate.placements:
        if placement.session == session_id:
            return placement
    raise UnresolvedLockTargetError(
        f"session {session_id!r} has no placement in candidate {candidate.id!r}; "
        "lock_session can only lock a session to the slot/room it already holds "
        "in the candidate the recommendation was proposed against."
    )
