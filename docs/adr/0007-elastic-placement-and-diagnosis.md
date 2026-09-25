# ADR 0007 — Elastic placement and relaxation-based infeasibility diagnosis

**Status:** Accepted

## Context

A scheduler needs a useful answer when a complete timetable does not exist: which sessions
cannot be placed, why, and what minimal change would fix it. CP-SAT can extract cores under
assumption literals, but enforcement literals on scheduling globals disable presolve
reasoning (measured by the original project: a 0.0 s infeasibility proof became `UNKNOWN`
after 240 s).

## Decision

1. **Elastic placement.** Every session has a presence literal. The number of unscheduled
   sessions (weighted by duration) is objective tier 0. All other hard constraints stay hard.
   A run therefore always has an incumbent and ends with either a complete timetable or the
   best partial one, which is stored as an *incomplete* candidate that cannot be approved.
2. **Analytic pre-checks** before solving (empty domains, instructor and group load versus
   available periods, room-class supply versus demand, fixed-placement collisions) report
   named resources and quantities.
3. **Explanations per unscheduled session:** for each feasible start and room, the blocking
   reasons (instructor busy with X, group busy with Y, room occupied, capacity) computed by
   the independent evaluator.
4. **Relaxation suggestions:** on request, a relaxation model makes selected hard requirements
   elastic with costs (instructor unavailability, room type, capacity, fixed placements,
   hard rules) and minimizes total relaxation, returning a minimal-cost set of changes that
   admits a complete timetable.

## Consequences

- An infeasible instance never produces an empty "failed" result.
- A partial timetable is clearly marked and blocked from approval and publication.
- Relaxation suggestions are heuristic minimal-cost changes, not unique explanations; the
  interface says so.
