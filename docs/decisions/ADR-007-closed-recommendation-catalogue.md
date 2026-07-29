# ADR-007 — Closed catalogue of three recommendation actions

**Status:** Accepted
**Date:** 2026-07-24 (specification phase)

## Context

The internship notes ask for a closed loop: the AI analyses a candidate, proposes an improvement, and —
if the person in charge accepts — the application rebuilds an improved timetable automatically.

**Read literally, that could mean the AI editing a timetable directly**, which would break the
separation the entire system rests on. So the loop is built the other way round.

## Decision

**A recommendation is never a timetable edit. It is a change to one of three inputs the solver already
accepts.**

| Action | Parameters | Effect on the next run |
|---|---|---|
| `weight_delta` | criterion code, new weight | Replaces one weight of the profile that produced the candidate |
| `lock_session` | session id | Fixes `start[s]` and `room[s]` to their current value, as H10 |
| `exclude_slot` | session id, slot id **or** room id | Withdraws one value from the domain of `start[s]` or `room[s]` |

Accepting one builds a new run with **exactly that one action applied**, and calls the same solving step
as the original generation. The new candidate is recorded under a new run, linked to the recommendation
and the original run, and scored and ordered like any other. Refusing sets the status to `rejected` and
creates no run.

## Consequences

**The guarantee carries over for the same reason it held the first time.** H1–H12 are declared
identically in the regenerated run, so they hold in the new candidate for the same reason they held in
the one that produced the recommendation. Nothing is edited by hand and nothing is edited by the AI.

**A recommendation can only change what the solver is asked to do, never what a solver call is allowed
to return.** That sentence is the whole safety argument.

- **The marginal engineering cost is small.** The portfolio mechanism already loops over several inputs
  to produce several candidates; a recommendation adds one more input to that loop.
- **Type the catalogue as a union** — `WeightDelta | LockSession | ExcludeSlot` — so that adding a fourth
  variant is a **type error** wherever the union is exhaustively matched, not a convention someone can
  quietly break.
- A suggestion phrased by the assistant is **matched against this catalogue before being offered**. One
  that matches no action type is displayed as a remark carrying no control to act on it.
- Regenerated candidates are verified by the same tests as any other candidate.

**The cost:** the catalogue is deliberately small, so genuinely useful improvements that do not fit
these three shapes cannot be offered. **A recommendation that cannot be expressed as one of the three is
not offered, rather than approximated.** Same discipline as ADR-006: the system proposes only what it
can carry out through the solver.

## Alternatives considered

**Let the AI propose an arbitrary change, validated afterwards** — **rejected**: "validated afterwards"
means re-solving anyway, so the freedom buys nothing while opening the possibility of a change nobody
can express as a solver input.

**Let the AI edit the timetable and re-check the hard constraints** — **rejected**: re-checking is a
weaker guarantee than construction. It also makes the candidate mutable, which contradicts the
requirement that a candidate's sub-scores always describe its actual content.

**A larger catalogue** (swap two sessions, move a session, free a room) — **not retained** for increment
1. Each new action must be expressible as a solver input and testable; the three above cover the
improvements the analysis layer can actually justify from the criteria.

## References

Project Plan and Methodology §4.9 · Cahier des Charges §4.4 · SRS §6.10, §7.5
