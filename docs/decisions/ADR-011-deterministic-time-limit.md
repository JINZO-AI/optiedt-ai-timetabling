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

**AMENDED 2026-07-30 — and `interleave_search = true`, without which none of this holds.**

A wall-clock ceiling is retained **as a hang backstop only**, not as the primary bound. Reaching it is
an anomaly to log, not a normal exit path.

The diagnosis run inherits the same treatment.

### The amendment, and why it was needed

This ADR originally stated the decision as deterministic time alone, and concluded that reproducibility
followed. **Measurement refuted that conclusion while confirming the mechanism.** Deterministic time
bounds the *amount of work*; it does not order the race between workers. Three identical requests
produced **three different timetables** — every one of them proving optimality, so the workers were not
being cut short. They were finding *different optimal solutions* and returning whichever reported
first.

`interleave_search` is the missing element. OR-Tools documents it as: *"we interleave all our major
search strategy and distribute the work amongst num_workers. **The search is deterministic
(independently of num_workers!)**"*. With it set, the reproducibility this ADR claimed is real —
verified on the reference instance, three profiles, paired runs agreeing on candidate ids, order,
placements, scores and sub-scores.

**The original decision therefore stands unchanged** — all workers, deterministic bound. What was
missing was one parameter it never named, and the claim was false in the implementation until that
parameter was set.

⚠️ **`interleave_search` is marked "Experimental" upstream.** The reproducibility guarantee is verified
by `tests/integration/test_reproducibility.py` at production settings rather than trusted from the
documentation, because an OR-Tools upgrade that regressed it would otherwise stay invisible until a
published timetable failed to reproduce. **Pin the OR-Tools version, and treat a failure in that file
as blocking.**

### One measured side effect, found 2026-07-31

**Under `interleave_search`, `CpSolver.objective_value` can disagree with the solution the solver
returns.** Measured on the ITC-2007 harness (`optiedt/validation/itc2007`), instances comp02, comp18 and
comp21: the reported objective sat **5 to 15 units above** the objective expression evaluated at the
very placements handed back, on solves that stopped on the budget **without proving optimality**. With
the parameter off, the two agree exactly on the same instances and budgets.

**Nothing in this project is affected, and the reason is architectural.** No score, ranking, comparison
or displayed figure reads `SolverOutput.cost`: `analysis/criteria.py` recomputes every criterion from
the returned placements, which is precisely what the ban on `analysis` importing `solver` forces
(`docs/architecture.md`). A solver reporting a number that does not match its own answer is exactly the
failure the layer separation was drawn to survive, and it survived it without a change.

Two guards were adjusted so they cannot become flaky for this reason:
`tests/integration/test_objective_matches_analysis.py` already required `proven_optimal` before
comparing — that requirement now carries this second justification in writing — and the ITC-2007
harness compares the **encoding** (each auxiliary's value against the recomputed component) rather than
the reported objective.

**Do not start ranking, comparing or displaying `SolverOutput.cost`.** If a future change needs a
trustworthy objective figure, take it only from a solve reporting `proven_optimal`.

Disabling worker information sharing (`share_binary_clauses`, `share_level_zero_bounds`,
`share_objective_bounds`) was also measured and does **not** help — the race is in the scheduling, not
in the sharing.

### A second change, outside this ADR

The warm start had to be **withheld when an objective is posted**. With the hint in place all three
weight profiles returned the same timetable at total budgets 15, 45 *and* 90, scoring an identical
78.076 every time — six times the budget and three different objectives yielding one candidate, because
the hint is an attractor the objective could not pull the search away from. Withholding it gives three
distinct candidates. The hint is kept for feasibility-only solves, where it is pure acceleration.
Implemented in `solver/engine.py`; this is the re-evaluation `docs/status.md` asked for "when the
objective lands".

## Consequences

Reproducibility holds, FR-19's acceptance test passes unchanged, and the search keeps its parallelism —
**all three now verified rather than asserted.** Measured on the reference instance:

| | before the amendment | after |
|---|---|---|
| Portfolio wall clock | 306 s | **147–150 s** |
| Distinct candidates | 3 | 3 |
| Reproducible | **no** | **yes** |
| Best score | 82.23 | 80.31 |

The configuration is roughly **twice as fast** and reproducible, at a cost of **~1.9 score points** —
the luck of a racing parallel search, given up deliberately. H1–H12 were re-derived from the raw CSVs
for every candidate and for the feasibility path; no hard constraint is affected. The feasibility-only
solve moved from ~3 s to ~4.4 s, still far inside its 60 s target.

**The 60-second and 5-minute figures become estimates, not wall-clock promises.** This narrows a hedge
the documents already carry rather than breaking a commitment — both state these are "objectives to be
measured during the second phase and not guarantees", because "the problem being of a class for which no
bound on the solving time can be announced in advance". The change is one of kind, not of honesty:
a deterministic budget is a *unit of work*, and its wall-clock cost varies by machine.

⚠️ **The deterministic-to-wall-clock ratio is machine-dependent and must be calibrated on the reference
instance during Phase 2**, then recorded in `docs/status.md`. **Until that calibration exists, the
user-facing time limit is an unvalidated guess.** A user setting "5 minutes" must get something close to
five minutes on the machine they are using.

> **DISCHARGED 2026-07-30** (late — it was owed in Phase 2). 1 deterministic unit per worker ≈ 4.8 s
> wall at one worker, ≈ 19 s at sixteen. The budget binds **exactly**, per worker: budget 5 reports
> 5.00 at `workers=1`, ratio 1.00. `CpSolver.deterministic_time` reports the **sum across workers**, so
> a 16-core machine legitimately reports ~54 for a 5-unit budget — an aggregate that was once recorded
> in `docs/status.md` as an "~11× overshoot" and is nothing of the kind. Full table in that file.

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
