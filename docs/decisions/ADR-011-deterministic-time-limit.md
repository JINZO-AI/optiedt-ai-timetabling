# ADR-011 — Solve under `max_deterministic_time`, not wall clock

**Status:** Accepted
**Date:** 2026-07-29

## Context

Two stated requirements could not both be satisfied by the configuration the documents describe.

**Reproducibility is required, and is an acceptance test:**

- SRS §7.2 and CdC §6: "for the same data, the same weights and the same random seed, two executions
  give the same result."
- SRS §8.6, acceptance test for FR-19: repeat a run with the same seed and weights → **"Identical
  candidates in the same order."**

**Parallelism is also specified:** PPM §4.5 states the optimisation run "uses all the workers."

**CP-SAT under a wall-clock limit with multiple workers is not reproducible.** Workers race; which one
reaches a solution first depends on machine load and scheduling. **A fixed seed does not fix this** —
the seed controls each worker's search, not the race between them. As written, the non-functional
requirement and its own acceptance test contradict each other.

## Decision

**Keep all workers. Bound the solve by `max_deterministic_time` rather than `max_time_in_seconds`.**

A wall-clock ceiling is retained **as a hang backstop only**, not as the primary bound. Reaching it is
an anomaly to log, not a normal exit path.

The diagnosis run inherits the same treatment.

## Consequences

Reproducibility holds, FR-19's acceptance test passes unchanged, and the search keeps its parallelism.
All the costs are documentation rather than code.

**The 60-second and 5-minute figures become estimates, not wall-clock promises.** This narrows a hedge
the documents already carry rather than breaking a commitment — both state these are "objectives to be
measured during the second phase and not guarantees", because "the problem being of a class for which no
bound on the solving time can be announced in advance". The change is one of kind, not of honesty:
a deterministic budget is a *unit of work*, and its wall-clock cost varies by machine.

⚠️ **The deterministic-to-wall-clock ratio is machine-dependent and must be calibrated on the reference
instance during Phase 2**, then recorded in `docs/status.md`. **Until that calibration exists, the
user-facing time limit is an unvalidated guess.** A user setting "5 minutes" must get something close to
five minutes on the machine they are using.

**The diagnosis run finally gets a budget.** PPM said its limit was "separate" but never stated one,
leaving an unbounded wait on the worst-case path — the user pays for the optimisation run reaching
`INFEASIBLE` *plus* a single-worker, objective-free diagnosis. A deterministic bound closes that.

**Consequences for tests.** Every test invoking the solver must fix the seed **and** use a deterministic
bound. A test bounded by wall clock passes on one machine and fails on another, and the failure looks
like a solver bug rather than a test defect.

**The interface must not promise wall-clock precision.** Show the budget as an estimate, and show
elapsed time separately.

## Alternatives considered

**`num_workers = 1`** — reproducible under a wall-clock limit, and the diagnosis run already requires it.
**Rejected**: noticeably slower search, which puts the 60-second first-timetable target at real risk on
an instance already at 95% laboratory occupancy. Trading a large amount of search capability for a
property obtainable another way.

**Keep wall-clock parallelism, weaken the requirement to "same objective value / same score"** —
**rejected**: FR-19's acceptance test would need rewriting, "two executions give the same result" would
stop being literally true, and two runs could present *different timetables* with equal scores, which
the person in charge would reasonably read as a defect.

**Run reproducibly only when explicitly requested** — **rejected**: makes reproducibility a mode rather
than a property. Every published timetable must trace back to the run, seed and weights that produced
it; that traceability is worth little if replaying those inputs need not reproduce the timetable.

## References

SRS §7.2, §8.6 · CdC §6 · PPM §4.5 · `docs/open-questions.md` C-2 · OR-Tools CP-SAT parameters
