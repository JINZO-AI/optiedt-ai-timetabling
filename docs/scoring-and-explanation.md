# Scoring, ranking and explanation

The analysis layer. It reads candidates as plain data and returns numbers.

It is kept deliberately separate from the constraint model because the two have **different
guarantees**. The solver's output is correct by construction; this layer's output is a judgement whose
errors cost a worse ranking, never an unusable timetable. Merging the two documents would blur exactly
the boundary the system is built on.

---

## The three formulas

**Normalisation** — each criterion is brought into `[0, 1]`, with **1 meaning the best situation**:

```
n_i(k) = 1 − ( v_i(k) − min_i ) / ( max_i − min_i )
```

**Score** — the weighted sum, expressed out of 100:

```
score(k) = 100 × Σ ( w_i × n_i(k) )
```

**Decomposition** — because the score is *linear* in the normalised criteria, the difference between
two scores decomposes **exactly**:

```
score(A) − score(B) = 100 × Σ ( w_i × ( n_i(A) − n_i(B) ) )
```

The term for criterion `i` is its **contribution** to the difference.

## Why linearity is the whole design

That third line is the entire explanation feature. The contribution shown to the user **is the
calculation, read term by term** — not an approximation of it, not a post-hoc rationalisation, not a
separate explanatory method that must itself be trusted.

This is why the weighted sum was chosen over lexicographic ordering, outranking methods and neural
ranking (ADR-002). A ranking produced by any of those would need an explanation constructed *after the
fact*, which the department could not verify. Here the department can recompute a score by hand from
the sub-scores and weights recorded with the run.

**Any change that makes the score non-linear destroys this property.** If you are about to add a
product term, a threshold, or a max, stop: you are removing the reason the feature is defensible.

---

## Bounds — instance-derived, and why it matters

**`min_i` and `max_i` are derived from the instance, not from the candidates a run produced.** They are
stable for every run on that instance, and recorded with the run so a score can be recomputed later
exactly as displayed. (ADR-009.)

The candidate-derived alternative is tempting because it spreads scores nicely across 0–100. It is
excluded for three reasons:

1. **It breaks monotonicity**, which SRS §7.5 *requires*. Improving one candidate shifts the bounds and
   moves every other candidate's normalised values.
2. **A run yielding two candidates degenerates** to a 0 / 100 split.
3. **It silently invalidates cross-run comparison.** A regenerated candidate is recorded under a *new*
   run. Under candidate-derived bounds it would carry different bounds, so comparing it against the
   originals compares two scores on two different scales — precisely the comparison FR-23 exists to
   support, failing precisely where it matters most.

The cost is real and accepted: a bound formula must be defined per criterion, and a loose theoretical
maximum can compress the score range. That is a **tuning** problem, not a correctness problem.

⚠️ Guard `max_i == min_i`. It is not hypothetical — a criterion with no violations anywhere in the
instance, or S10 at weight 0, will hit it. Decide the convention (`n_i = 1`) and apply it uniformly.

---

## Ordering

Candidates are ordered by **decreasing score**. Ties are broken by the criteria taken in order of their
weights.

The order must not depend on the order in which candidates are read — this is a tested property, not an
assumption.

**One weight vector prices every candidate of a run, regardless of which profile produced its
placements.** The three weight profiles (balanced, student-favouring, teacher-favouring) exist to steer
the *solver* toward diverse candidates — that is the entire reason for varying the objective rather
than the seed (see `docs/constraint-model.md`, "Weight profiles and the portfolio"). They are not, by
themselves, a valid basis for scoring the resulting candidates: the exactness identity above only holds
when the same `w_i` prices both `A` and `B`, and two candidates solved under two different profiles
would need two different `w_i`. So the run's **weights in force** — one reference vector — score and
rank every candidate it produced, whatever profile's objective placed it; the profile is retained on the
candidate only as provenance of how it was obtained, never as its own scoring weight. Implemented as
`analysis.ranking.DefaultRanker(weights=...)`, constructed once per run with that one vector.

---

## Dominance

A candidate that another is **at least as good on every criterion and strictly better on at least one**
is **dominated**, and the interface signals it **wherever it appears in the portfolio**.

That is the standard Pareto rule. This test is exact and needs no parameters, but it does not produce an
order — most candidates win on one criterion and lose on another. It is a *complement* to the weighted
sum, never a replacement.

Why it is surfaced: a dominated candidate is one the portfolio contains for no reason another does not
serve better, and saying so lets the person in charge see that the ranking is arbitrating a real
trade-off rather than concealing one.

⚠️ **The signal is never attached to the top-ranked candidate, and that is arithmetic rather than a
design preference.** If `B` dominates `A` then every term of

```
score(B) − score(A) = 100 × Σ ( w_i × ( n_i(B) − n_i(A) ) )
```

is non-negative, so `score(B) ≥ score(A)`; and where the sum is exactly zero — the strict gain falling
on a zero-weight criterion — the tie-break covers all seven criteria and still resolves in `B`'s favour.
**`A` can never rank first.** An indicator built on that state would be permanently silent, and a
control that never fires teaches its reader that it means "no problem found".

⚠️ **Both statements above changed on 2026-08-05 (C-14), and the previous wording is recorded rather
than erased.** This section said "a candidate that another **improves on every** criterion" — strict `>`
everywhere — "and the interface signals it when it happens to the top-ranked candidate". The strict
reading was silent exactly where the signal matters: S10 carries weight 0, nothing optimises for it, so
a candidate beaten on all six *weighted* criteria and merely tied on S10 was reported as not dominated.
The top-candidate clause described a state the arithmetic forbids. The two defects were independent and
were fixed independently — adopting Pareto does **not** make the top-candidate case reachable.

---

## The four properties

Verified by **property-based tests on randomly generated candidates**, because a property holds for
every input while an example holds for one.

| Property | Statement |
|---|---|
| **Exactness of decomposition** | The sum of the contributions equals the difference of the two scores |
| **Invariance of order** | The order does not depend on the order candidates are read in |
| **Monotonicity** | Reducing violations of one criterion never lowers the score |
| **Detection of dominance** | A candidate another matches on every criterion and beats on at least one is signalled |

Exactness follows from linearity, and its failure means an arithmetic bug. Monotonicity follows from
weight non-negativity, and it is tested because **the weight fitting of increment 2 could break it**.

Watch floating point on exactness — assert to display precision, which is what the acceptance criterion
actually promises ("to the precision of the display"), rather than to exact equality.

---

## Requirements this layer must satisfy

These apply to the components that score, order, explain and adjust weights, and to no other layer.

- **Separation** — may not add, move or remove a session, nor modify a recorded candidate.
- **Exactness** — every figure displayed is recomputable from the sub-scores, bounds and weights
  recorded with the run.
- **Determinism** — the same inputs give the same order and contributions, in any read order.
- **Monotonicity** — reducing violations of one criterion never lowers the score.
- **Human control** — a weight adjustment applies only after explicit validation, and the weights in
  force are displayed with the run that used them.

---

## Recommendation rule

The recommendation designates the **candidate of highest score**, and states the rule that produced it.

That is the entire rule. It is stated plainly so the interface can show it — "recommended because it
has the highest score under the weights in force" is a sentence the department can check.

⚠️ **A third sentence was removed here on 2026-08-05 (C-14): "A dominated top candidate is signalled
alongside."** It described a state the arithmetic forbids — see §Dominance above — so it was a promise
that could never be kept rather than a feature that was never built. `Recommendation.dominated_by`
still exists, is still computed and is still provably `None`; it is kept because FR-16's statement
names it and because a non-linear score or a negative weight would revive it, and it is pinned dead by
`test_a_dominated_candidate_is_never_recommended`. **The signal a user actually sees is the
portfolio-wide one**, which is a different thing.

---

## Weight adjustment — increment 2, optional

Each recorded comparison provides two candidates and the one retained. The vector of differences
between their normalised criteria is formed, and a **logistic regression without constant term** is
fitted on those vectors:

```
P( A retained rather than B ) = logistic( Σ w_i × ( n_i(A) − n_i(B) ) )
```

The fitted coefficients are the weights. Three restrictions, each answering an objection:

- **Non-negative weights** — otherwise a coefficient could go negative on a small sample and the
  application would reward a defect.
- **Weights renormalised to sum 1** — a positive multiple of the weights gives the same order, so this
  fixes the score's scale without changing any ranking.
- **Regularised towards the weights in force** — with few examples the fit must not drift far from the
  catalogue, which stays the reference while the evidence is thin.

A larger model was considered and set aside: ~7 criteria and a few tens of comparisons support a linear
model at most — and a linear model is **the only kind that preserves the exact decomposition**, which
is the property the whole explanation rests on.

### The adoption criterion

Evaluated by **leave-one-out**: predict each comparison with weights fitted on the others, and compare
the accuracy against the weights in force on the same comparisons.

**Adjusted weights are adopted only if their accuracy exceeds that of the weights in force** and the
comparison count reaches a threshold fixed *before* the experiment. Otherwise the weights in force are
kept and the result is recorded as **not established**.

This criterion is stated in advance and **can be failed** — which is the condition for the conclusion
to mean anything. Do not weaken it after seeing the data.

### Where the data comes from

No collection of accepted-or-refused timetables exists for a Tunisian faculty, and it cannot be
reconstructed after the fact: published timetables carry no trace of the alternatives set aside.

So the weights start at catalogue values, and **the application is, from its first use, the instrument
that produces the data increment 2 needs**. Every comparison recorded on the comparison screen is one
training example.
