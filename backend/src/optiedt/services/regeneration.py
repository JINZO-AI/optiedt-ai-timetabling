"""Turning an accepted recommendation into a new run (FR-23).

This is the module `recommendations/translator.py` has been pointing at since
Phase 3. Its docstring records the gap precisely: `translate(action, run,
candidate)` receives a `Run` carrying no instance and no profile weights, and a
`Candidate` carrying a profile *name* rather than its weights, so **no layer
below `services` has the context a `SolverInput` needs**. `translate()` returns
a `RunOverride` - plain domain data - and this module is what merges it into a
run (C-20).

**Why here.** `services` is the only layer permitted to hold both the run store
and the solver; `services/portfolio.py` is the precedent and does the same job
for an ordinary run. Nothing in `recommendations/` changes, and nothing in it
learns what a `SolverInput` is.

**What a regeneration is, and is not.**

    accepted recommendation
        -> ONE input changed
        -> a NEW run through the SAME engine
        -> a new candidate, scored and ordered like any other

It is never an edit. H1-H12 are declared identically in the regenerated run, so
they hold in the new candidate **for the same reason they held in the first one**
(docs/ai-integration.md). Invariant 6 is untouched: the origin run and its
candidates are not written to at all, and the regenerated timetable is a new
candidate under a new run - which invariant 6 requires rather than merely
permits.

**Three rules this module exists to keep.**

1. **Exactly one input changes** (ADR-007). `weight_delta` touches the weight
   vector; `lock_session` and `exclude_slot` touch the overrides. Never both.
2. **Overrides COMPOSE** (C-20). A regenerated run carries its origin's
   overrides plus the new one. Without it, accepting a second recommendation
   silently discards the first, and a user watches a lock they set disappear
   with nothing on screen to explain it.
3. **A `weight_delta` reads against the run's OWN recorded vector**, never
   against the catalogue - which is rule 2 again in a different disguise, since
   reading the catalogue would discard any earlier delta.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from optiedt.domain.entities import (
    Candidate,
    CandidateId,
    ConstraintCode,
    Placement,
    Run,
    RunId,
    RunOrigin,
    RunOverrides,
)
from optiedt.domain.enums import RunState
from optiedt.recommendations.catalogue import (
    ExcludeSlot,
    LockSession,
    RecommendationAction,
    WeightDelta,
)
from optiedt.recommendations.translator import (
    DefaultRecommendationTranslator,
    ExcludedOption,
    LockedPlacement,
    WeightOverride,
)
from optiedt.services.runs import MODEL_VERSION, RunRecord


class RegenerationError(Exception):
    """The recommendation cannot be turned into a run, and why."""


def _candidate_of(record: RunRecord, candidate_id: CandidateId) -> Candidate:
    for candidate in record.candidates:
        if candidate.id == candidate_id:
            return candidate
    raise RegenerationError(
        f"candidate {candidate_id!r} is not part of run {record.run.id!r}; a "
        "recommendation is always proposed against a candidate of the run it "
        "regenerates, and the lock target is read out of that candidate."
    )


def _weights_with(
    weights: dict[ConstraintCode, float], override: WeightOverride
) -> dict[ConstraintCode, float]:
    """One entry replaced in the run's OWN vector - rule 3.

    Refuses a criterion the run does not price. A weight_delta naming S1, S8 or
    S9 (retired codes) or a hard constraint would otherwise silently ADD an
    entry, and the run would be scored under a vector no other run uses.
    """
    if override.criterion not in weights:
        raise RegenerationError(
            f"criterion {override.criterion!r} is not one this run prices "
            f"({', '.join(sorted(weights))}). A weight_delta replaces a weight; "
            "it does not introduce a criterion."
        )
    if override.new_weight < 0:
        raise RegenerationError(
            f"weight {override.new_weight} is negative. A negative weight would make "
            "a dominated candidate outscore its dominator, which the whole "
            "decomposition rests on being impossible (C-14)."
        )
    adjusted = dict(weights)
    adjusted[override.criterion] = override.new_weight
    return adjusted


def _detail(action: RecommendationAction) -> str:
    """Human-readable provenance. Recorded, never parsed back."""
    if isinstance(action, WeightDelta):
        return f"{action.criterion} weight set to {action.new_weight}"
    if isinstance(action, LockSession):
        return f"session {action.session} locked to its current slot and room"
    target = f"slot {action.slot}" if action.slot is not None else f"room {action.room}"
    return f"session {action.session} may no longer use {target}"


def regenerate(
    origin: RunRecord,
    candidate_id: CandidateId,
    action: RecommendationAction,
    new_run_id: RunId,
    translator: DefaultRecommendationTranslator | None = None,
) -> RunRecord:
    """Assemble the run an accepted recommendation produces.

    Returns a `PENDING` record for the caller to store and submit to the
    executor - the same path an ordinary run takes, deliberately, so a
    regenerated run cannot acquire a shortcut past pre-analysis or diagnosis.

    The origin run must have produced candidates. Regenerating from a run that
    failed or was found infeasible would be regenerating from nothing: there is
    no candidate to read a lock target out of, and no ranking that could have
    produced a recommendation.
    """
    if origin.run.state is not RunState.COMPLETED:
        raise RegenerationError(
            f"run {origin.run.id!r} is {origin.run.state.value}, not COMPLETED. A "
            "recommendation is proposed against a candidate, and a run that "
            "produced none has nothing to regenerate from."
        )

    candidate = _candidate_of(origin, candidate_id)
    override = (translator or DefaultRecommendationTranslator()).translate(
        action, origin.run, candidate
    )

    weights = dict(origin.weights)
    overrides = origin.overrides

    # Exactly one of these branches runs - rule 1. `RunOverride` is a closed
    # union, so a fourth kind is a type error rather than a silent fall-through.
    if isinstance(override, WeightOverride):
        weights = _weights_with(weights, override)
    elif isinstance(override, LockedPlacement):
        overrides = _composed_lock(overrides, override)
    else:
        overrides = _composed_exclusion(overrides, override)

    return RunRecord(
        run=Run(
            id=new_run_id,
            created_at=datetime.now(UTC),
            seed=origin.run.seed,
            deterministic_budget=origin.run.deterministic_budget,
            state=RunState.PENDING,
            model_version=MODEL_VERSION,
        ),
        weights=weights,
        origin=RunOrigin(
            run=origin.run.id,
            candidate=candidate_id,
            action_kind=action.kind,
            action_detail=_detail(action),
        ),
        overrides=overrides,
    )


def _composed_lock(existing: RunOverrides, lock: LockedPlacement) -> RunOverrides:
    """Rule 2, for a lock.

    A second lock on a session already locked elsewhere is refused HERE rather
    than left for `build_variables` to raise on. Both refuse, but only this one
    can say which recommendation contradicted which - the solver sees two
    Placements and no history.
    """
    placement = Placement(session=lock.session, slot=lock.slot, room=lock.room)
    for held in existing.locked_placements:
        if held.session == placement.session and held != placement:
            raise RegenerationError(
                f"session {placement.session} is already locked to slot {held.slot} "
                f"room {held.room} by an earlier accepted recommendation on this "
                f"chain. Locking it to slot {placement.slot} room {placement.room} "
                "would contradict that; regenerate from the run before it instead."
            )
    return replace(existing, locked_placements=existing.locked_placements | {placement})


def _composed_exclusion(existing: RunOverrides, excluded: ExcludedOption) -> RunOverrides:
    """Rule 2, for an exclusion. Exactly one of slot/room is set, mirroring
    `ExcludeSlot` itself."""
    if excluded.slot is not None:
        return replace(
            existing,
            excluded_slots=existing.excluded_slots | {(excluded.session, excluded.slot)},
        )
    if excluded.room is not None:
        return replace(
            existing,
            excluded_rooms=existing.excluded_rooms | {(excluded.session, excluded.room)},
        )
    raise RegenerationError(
        f"exclude_slot on session {excluded.session} names neither a slot nor a "
        "room, so it excludes nothing. One of the two is required."
    )


def action_from_wire(
    kind: str,
    criterion: str | None = None,
    new_weight: float | None = None,
    session: str | None = None,
    slot: int | None = None,
    room: str | None = None,
) -> RecommendationAction:
    """Build a catalogue action from an API payload, or refuse.

    ⚠️ **The catalogue is closed** (ADR-007), and this is where that is
    enforced against the outside world. A payload naming a fourth kind is
    rejected here rather than approximated onto the nearest of the three - a
    recommendation that cannot be expressed as one of the three is NOT offered.
    """
    if kind == "weight_delta":
        if criterion is None or new_weight is None:
            raise RegenerationError("weight_delta requires a criterion and a new weight")
        return WeightDelta(criterion=criterion, new_weight=new_weight)
    if kind == "lock_session":
        if session is None:
            raise RegenerationError("lock_session requires a session")
        return LockSession(session=session)
    if kind == "exclude_slot":
        if session is None:
            raise RegenerationError("exclude_slot requires a session")
        if (slot is None) == (room is None):
            raise RegenerationError(
                "exclude_slot requires exactly one of slot or room - naming both "
                "would be two exclusions, and naming neither excludes nothing"
            )
        return ExcludeSlot(session=session, slot=slot, room=room)
    raise RegenerationError(
        f"{kind!r} is not one of the three catalogue actions (weight_delta, "
        "lock_session, exclude_slot). The catalogue is closed: a recommendation "
        "that cannot be expressed as one of them is not offered (ADR-007)."
    )
