"""The closed catalogue of recommendation actions.

A recommendation is NEVER a timetable edit. It is a change to one of three
inputs the solver already accepts. Accepting one launches a new run through the
same engine with exactly that one input changed — so H1..H12 hold in the new
candidate for the same reason they held in the one that produced the
recommendation.

The catalogue is a union type on purpose: adding a fourth variant is a type
error wherever ``RecommendationAction`` is exhaustively matched, not a
convention someone can quietly break.

See ADR-007 and docs/ai-integration.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from optiedt.domain.entities import (
    Candidate,
    ConstraintCode,
    RoomId,
    Run,
    SessionId,
    SlotIndex,
)


@dataclass(frozen=True, slots=True)
class WeightDelta:
    """Raise or lower the weight of one soft criterion for the next run.

    Replaces one weight of the profile that produced the candidate. The profile
    is renormalised to sum to 1 before scoring, as always.
    """

    kind: Literal["weight_delta"] = "weight_delta"
    criterion: ConstraintCode = ""
    new_weight: float = 0.0


@dataclass(frozen=True, slots=True)
class LockSession:
    """Fix one session to its current slot and room while the rest re-optimises.

    Applied exactly as H10: start[s] and room[s] are fixed to the values they
    hold in the candidate.
    """

    kind: Literal["lock_session"] = "lock_session"
    session: SessionId = ""


@dataclass(frozen=True, slots=True)
class ExcludeSlot:
    """Remove one option for one session before the next run.

    Withdraws one value from the domain of start[s] or room[s]. Exactly one of
    ``slot`` and ``room`` is set.
    """

    kind: Literal["exclude_slot"] = "exclude_slot"
    session: SessionId = ""
    slot: SlotIndex | None = None
    room: RoomId | None = None


type RecommendationAction = WeightDelta | LockSession | ExcludeSlot
"""The catalogue. Closed — do not extend without a new ADR.

A recommendation that cannot be expressed as one of these three is NOT offered,
rather than approximated. A suggestion phrased by the assistant that matches no
variant is displayed as a remark carrying no control to act on it.
"""


class RecommendationTranslator(Protocol):
    """Translates an accepted recommendation into a solver input.

    This module writes exactly three things: a weight, a lock, an exclusion.
    It NEVER writes a placement (SRS §7.5). That is why it is a package of its
    own rather than part of the analysis layer, which may write nothing at all.

    The result is fed to an ordinary call of the solving step, so the
    regenerated candidate is verified by the same tests as any other.
    """

    def translate(self, action: RecommendationAction, run: Run, candidate: Candidate) -> object:
        """Return a SolverInput with exactly that one action applied."""
        ...
