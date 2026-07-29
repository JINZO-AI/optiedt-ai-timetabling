# ADR-009 — Normalisation bounds derived from the instance

**Status:** Accepted
**Date:** 2026-07-29

## Context

Each criterion is brought into `[0, 1]` against bounds:

```
n_i(k) = 1 − ( v_i(k) − min_i ) / ( max_i − min_i )
```

SRS §6.7 says the bounds are "computed from the data of the run and recorded with it". **That phrase is
ambiguous** between two readings: bounds derived from the *instance*, or from the *candidates the run
produced*.

The ambiguity is load-bearing. It determines whether scores from two runs can be compared at all — and
FR-23 makes that comparison the routine action, since accepting a recommendation produces a new
candidate under a **new run**.

## Decision

**Bounds are derived from the instance, and are stable for every run on that instance.**

They are still recorded with the run, so a score can be recomputed later exactly as displayed — but
identically across runs rather than differently.

## Consequences

**The candidate-derived reading is excluded on three grounds, the first of which is decisive:**

1. **It breaks monotonicity, which SRS §7.5 *requires*.** Improving one candidate shifts the bounds and
   thereby moves every other candidate's normalised values. A stated required property would silently
   fail — and it is one of the four properties tested on the analysis layer.
2. **A run yielding two candidates degenerates** to a 0 / 100 split, since on each criterion the better
   candidate takes `n_i = 1` and the worse `n_i = 0`. The score stops carrying information.
3. **It silently invalidates cross-run comparison.** A regenerated candidate lives under a new run and
   would carry different bounds, so comparing it against the originals compares two scores computed on
   two different scales. The exactness guarantee would fail **precisely at the comparison the feature
   exists to support**, and fail invisibly — the numbers would still add up within each run.

**What this costs, accepted:**

- **A bound formula must be defined for each criterion**, alongside its raw value. A loose theoretical
  maximum compresses the score range — all candidates landing between 94 and 96 makes the comparison
  screen less useful. **That is a tuning problem, not a correctness problem**, and it is visible and
  fixable; the candidate-derived failure mode is neither.
- The formula work merges into C-4: defining `v_i` and defining `min_i`/`max_i` are **one task per
  criterion, not two**.

**Enforced by the interface.** The `Criterion` Protocol exposes `raw_value(candidate)` and
`bounds(instance)` on the same object, deliberately, so a criterion cannot be half-defined. Note the
signatures: `bounds` takes the **instance**, not a candidate list — the type makes the wrong reading
inexpressible.

⚠️ **Guard `max_i == min_i`.** Not hypothetical: a criterion with no violations anywhere, or S10 at
weight 0, will reach it. Fix the convention (`n_i = 1`) and apply it uniformly.

## Alternatives considered

**Bounds from the candidates of the run** — **rejected**, three reasons above.

**Bounds from the candidates, with cross-run comparison re-normalised on the fly** — **rejected**: it
would make a displayed score depend on what it is being compared against, so the number shown next to a
candidate would change with context. That defeats the property the whole design rests on — that a
department can recompute a score by hand.

## References

SRS §6.7, §7.5 · `docs/open-questions.md` C-3 · `docs/scoring-and-explanation.md`
