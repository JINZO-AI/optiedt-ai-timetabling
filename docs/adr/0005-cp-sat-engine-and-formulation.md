# ADR 0005 — CP-SAT engine with a time-indexed formulation

**Status:** Accepted

## Context

The engine must place thousands of weekly sessions under hard rules, optimize several
objectives, prove infeasibility where possible, accept warm starts, report progress, and be
stoppable. See `docs/research/scheduling-landscape.md` §3.

## Decision

Google OR-Tools CP-SAT (9.15), with this formulation:

- **Time:** one boolean `x[s,t]` per session `s` and feasible start `t`. Start domains are
  pruned before modelling (open periods, day boundaries, non-joinable breaks, instructor,
  group and activity unavailability, fixed placements).
- **Resource conflicts** (instructors, student conflict atoms): for every clique and period,
  an at-most-one over the start literals covering that period.
- **Rooms:** one boolean `y[s,r]` per compatible room, with an optional interval per pair and
  `NoOverlap` per room; room unavailability enters as fixed blocking intervals.
- **Soft objectives** are linear over `x` and `y` plus compact auxiliary booleans (busy-before /
  busy-after chains for idle periods, day-used indicators).
- A constructive heuristic supplies a warm start; a problem-specific large neighbourhood
  search is added only for instance sizes where benchmarks show the monolithic model stalls.

## Alternatives considered

- Integer start variables with `NoOverlap` for every resource (the original approach): strong
  propagation, but soft objectives still need the per-period booleans, doubling the model.
- MIP with an open-source solver: markedly weaker on this problem class.
- Pure local search: no proofs; diagnosis would be guesswork.

## Consequences

- Model size grows with sessions × feasible starts and sessions × compatible rooms; the
  room-size ratio rule (no small group in a far larger room) also prunes the room domain.
- The formulation and its measurements are documented in `docs/design/optimization-model.md`
  and `docs/benchmarks/`.
