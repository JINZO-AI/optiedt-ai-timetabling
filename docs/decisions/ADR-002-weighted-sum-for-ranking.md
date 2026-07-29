# ADR-002 — Weighted sum for ranking, dominance as a complement

**Status:** Accepted
**Date:** 2026-07-23 (specification phase)

## Context

Choosing among candidates that all respect the rules is a different problem from producing them. It is
a compromise between criteria that cannot all improve at once — reducing students' idle hours often
increases teachers' days of presence.

The department must be able to **defend the order to a teacher who contests a placement**. That
requirement, more than any mathematical property, drove the choice.

There is also a tension worth naming, because the two project objectives appear to contradict each
other. The solver proves optimality *with respect to a given weight vector*. The weight vector expresses
what the department considers a good timetable — and **no faculty has ever written it down**. So the
application produces the proven optimum under several plausible weightings and asks a person to choose.
**Ranking exists because the objective is uncertain, not because the engine is weak.**

## Decision

**A weighted sum of normalised criteria for the order, with dominance retained as a complement.**

```
n_i(k) = 1 − ( v_i(k) − min_i ) / ( max_i − min_i )
score(k) = 100 × Σ ( w_i × n_i(k) )
score(A) − score(B) = 100 × Σ ( w_i × ( n_i(A) − n_i(B) ) )
```

## Consequences

**Linearity is the entire design, not a convenience.** Because the score is linear in the normalised
criteria, the difference between two scores decomposes **exactly** into a sum of per-criterion
contributions. The explanation shown to the user **is the calculation, read term by term** — not an
approximation, not a post-hoc rationalisation, not a separate explanatory method that would itself need
to be trusted.

- The department can recompute a score by hand from the sub-scores and weights recorded with the run.
- **Any change making the score non-linear destroys this.** A product term, a threshold or a max
  removes the reason the feature is defensible.
- It also constrains increment 2: a linear model is the only kind that preserves exact decomposition,
  which is why weight learning uses logistic regression rather than something larger.
- This aligns with reference practice — the curriculum-based competition evaluates timetables the same
  way.

**Dominance is surfaced, not used for ordering.** A candidate improved by another on every criterion is
signalled when it is the top-ranked one. The test is exact and needs no parameters, but it produces no
order, since most candidates win on one criterion and lose on another. It is shown because **a dominated
top candidate reveals that the weights are concealing a compromise rather than expressing one** — and
the person in charge must then decide knowing that.

## Alternatives considered

**Lexicographic order** — simple, produces an order, verifiable by hand. **Rejected**: it does not
describe how a department reasons. A small loss on the first criterion is never compensated by a large
gain on the second, which is not how anyone actually trades these off.

**Outranking methods** (pairwise comparison with indifference and veto thresholds) — richer. **Rejected**
on two grounds: the thresholds are harder to justify before a department than a weight, and the result
is not a number the user can verify.

**Ranking by a neural model** — **rejected**: requires a large set of examples that does not exist, and
its explanation would have to be constructed after the fact.

**Ranking by a language model** — **rejected for ranking**, retained for explanation. See ADR-006.

## References

Project Plan and Methodology §4.6, §2.5 · Cahier des Charges §7.4 · SRS §6.7
