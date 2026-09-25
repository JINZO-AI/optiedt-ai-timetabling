# ADR 0018 — Two solving modes: reproducible and fastest

**Status:** Accepted

## Context

With parallel workers and a wall-clock limit, CP-SAT's result depends on thread timing.
Institutions value being able to re-run a published timetable's computation; they also value
the best timetable in the least time.

## Decision

- **Reproducible mode** (default): deterministic time budget (`max_deterministic_time`),
  `interleave_search`, recorded seed and worker count. A wall-clock ceiling remains as a safety
  net; if it triggers, the run is marked non-reproducible.
- **Fastest mode:** wall-clock budget, racing portfolio; the run is marked non-reproducible.
- Every run records the snapshot hash, configuration, seed, OR-Tools and application versions.

## Consequences

- Wall-clock duration of a reproducible run varies with hardware; the interface shows an
  estimate derived from the worker's measured speed.
