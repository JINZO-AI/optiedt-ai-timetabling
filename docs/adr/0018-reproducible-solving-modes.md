# ADR 0018 — Two solving modes: fastest (default) and reproducible

**Status:** Accepted. Revised after measurement: the first version made reproducible mode
the default.

## Context

With parallel workers and a wall-clock limit, CP-SAT's result depends on thread timing.
Institutions value being able to re-run a computation and get the same timetable; they also
value the best timetable in the least time.

Every candidate timetable is stored immutably with its snapshot, settings and metrics, so an
audit never needs to recompute a result: reproducibility helps support and investigation, not
the record.

CP-SAT is deterministic with several workers only in interleaved search, where each batch of
tasks waits for its slowest task. Measured on a 195-session synthetic faculty (4 cores, one
objective tier with idle time, instructor days and penalised slots):

| Configuration | Objective reached | Wall time |
|---|---|---|
| Fastest, default portfolio | 74 | 20 s |
| Fastest, default portfolio | 45 | 80 s |
| Interleaved, default portfolio, 20 deterministic s | 353 | 49 s |
| Interleaved, without LP-heavy workers, batch size 4, 20 deterministic s | 54–56 | 74–83 s |
| Interleaved, without LP-heavy workers, batch size 4, 5 deterministic s | 149 | 23 s |

The LP-based workers spend their first task (about 16 deterministic seconds on this model)
solving the root relaxation, and in interleaved search every other worker waits for them.

## Decision

- **Fastest mode** (default): wall-clock budget, CP-SAT's full racing portfolio. The run
  records its seed but is marked non-reproducible.
- **Reproducible mode** (on request): interleaved search with a batch size of 4 and without
  the LP-heavy full-problem workers (`default_lp`, `fixed`, `max_lp`, `max_lp_sym`,
  `quick_restart`, `reduced_costs`, and the tree/probing searches). The budget is
  deterministic time, 0.3 deterministic seconds per requested second (about one wall-clock
  second each on a four-core machine), and the engine divides it between tiers by
  deterministic time spent, so the division itself does not depend on the machine. A
  wall-clock ceiling (three times the request) remains as a safety net; if it ends a search,
  the run is marked non-reproducible.
- Every run records the snapshot hash, settings, seed, worker count, OR-Tools and application
  versions.

## Consequences

- Interactive runs get the best timetable per minute of waiting.
- A reproducible run gives lower quality for the same wall time (about 150 instead of 74 in
  the measurement above) and proves optimality less often, because the LP bounds are gone.
  It is offered for support and investigation, with that trade-off stated in the interface.
- Wall-clock duration of a reproducible run varies with hardware; the interface shows an
  estimate derived from the worker's measured speed.
