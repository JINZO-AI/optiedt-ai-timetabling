# Open questions and errata

Findings from a full reading of the three specification documents, before any code existed.

**How to use this file.** If your work touches an open item, resolve it *here* first — with the reason
— then implement. An assumption made in code and never written down is how this project acquires a
defect that surfaces three weeks later.

Nothing in this file is a criticism of the specification. Three documents written in layers over four
weeks will disagree in places; the failure mode is not that they disagree, it is that nobody notices.

| Status | Meaning |
|---|---|
| **RESOLVED** | Decided, recorded in an ADR. Do not reopen without reading it |
| **OPEN** | Not decided. Do not silently pick an answer |
| **ERRATUM** | A document is wrong; replacement wording given |

## Index — what is actually still open

**One.** Everything else on this page is resolved and kept for its reasoning. **C-15 was resolved on
2026-08-07** — on measurement, and by refuting its own recorded diagnosis.

| # | Still open | Blocks | Owner |
|---|---|---|---|
| **C-9** | FR-6, FR-10, FR-17, FR-18 have no detailed specification | ⚠️ **Not the Phase 6 acceptance suite** — see the correction in C-9's own section | Technical lead |
| ~~**C-15**~~ | ~~The objective weights raw violation counts of incomparable scale~~ — **RESOLVED 2026-08-07 on measurement.** The diagnosis was wrong: the objective formulation is sound and is unchanged. `teacher-favouring` now raises **S3 and S4** rather than S3 and S5, because S5 is an admitted proxy (C-12) and the most expensive criterion to optimise. A profile's promise is reworded to its **headline** criterion, the only reading the arithmetic can deliver | ~~FR-13~~ — unblocked | ~~Technical lead~~ |

Resolved: **C-1, C-2, C-3** (ADRs 010, 011, 009) · **C-6, C-7, C-13** (2026-07-30, implemented) ·
**C-17, C-18** (2026-08-04) · **C-5, C-14** (2026-08-05, project-owner decision) ·
**C-19, C-20, C-21** (2026-08-06, project-owner decision, before any Phase 7 code) ·
**C-8, C-11** · **C-4, C-12** · **C-16** (2026-07-30, implemented) · **C-15** (2026-08-07, on
measurement). The sections below keep their full reasoning; headings say which is which.

**Nineteen resolved plus one open is twenty, and the codes run C-1 to C-21 — there is no C-10, and that
is not a lost question.** The number was never assigned. Recorded here for the same reason the retired
soft-criterion codes S1/S8/S9 are recorded in the errata: a gap in a sequence invites someone to go
looking for what fell through it.

⚠️ C-4 and C-12 **were** one bug waiting to happen, before they were resolved together on 2026-07-30:
had S5 measured identically zero, the teacher-favouring profile would have differed from the others by
S3 alone, risking two candidates converging under duplicate removal and failing the three-candidate
acceptance test (C-5). **C-5 was resolved on 2026-08-05** — the specification's wording was clarified
and the implementation left alone; S5 no longer being identically zero is what makes the reference
instance's three distinct candidates hold rather than be hoped for.

---

## RESOLVED

### C-1 — The assistant's increment · RESOLVED → increment 1 · ADR-010

CdC §4.5 ("a committed part of the first increment"), CdC §7.4, CdC Table 2, the *Necessary* priority
of FR-22/23/24, PPM Table 6 (which lists increment 2 as exams + weights only), PPM §8.3 and PPM §10 all
place the assistant in **increment 1**. SRS §2.3 and SRS §1.2 place it in increment 2.

Eight statements against two. **Decision: increment 1.** The two SRS sentences are stale text from an
earlier draft — see the errata below.

**Carried forward:** PPM Table 8 allocates 3+5+3+4+2+3 = 20 days and names the assistant in **no
phase**. ~2.5 unbudgeted days ≈ 12% overrun. Tracked in `docs/status.md`. Release valve already decided
in PPM §8.3: the assistant's *report* is the first scope cut, explanations and answers kept.

### C-2 — Reproducibility vs parallel workers · RESOLVED → deterministic time · ADR-011

SRS §7.2 and acceptance test FR-19 require identical candidates for the same seed. PPM §4.5 runs the
optimisation with **all workers**. **CP-SAT under a wall-clock limit with parallel workers is not
reproducible** — workers race and a fixed seed does not fix it. As written, the requirement and the
acceptance test could not both hold.

**Decision: keep all workers, bound the solve by `max_deterministic_time`.**

Consequences, all documentation rather than code:
- The 60-second and 5-minute figures become **estimates, not wall-clock promises**. Both documents
  already hedge them as "objectives to be measured … not guarantees", so this narrows an existing hedge.
- A **wall-clock ceiling remains as a hang backstop**. Crossing it is an anomaly to log, not a normal exit.
- ⚠️ The deterministic-to-wall-clock ratio is **machine-dependent and must be calibrated on the
  reference instance in Phase 2**, then recorded in `docs/status.md`. Until then the user-facing limit
  is an unvalidated guess.
- The diagnosis run inherits the same treatment, which also gives it the budget it never had.

#### ⚠️ Calibrated 2026-07-30 — the mechanism works; the conclusion needed one more parameter. See C-16

The calibration this ADR demanded in Phase 2 was never done. It is done now, and it corrects one
recorded belief and refutes one of this ADR's own claims.

**Corrected: there is no "11× overshoot".** `docs/status.md` recorded that a 30-unit budget consumed
~325 units and concluded the budget "does not bind". It binds **exactly** — per worker. What
`CpSolver.deterministic_time` reports is the **sum across workers**, so on a 16-core machine a 5-unit
budget legitimately reports ~54. Measured, reference instance, budget 5:

| workers | reported | ratio | wall |
|---|---|---|---|
| 1 | **5.00** | **1.00** | 24.1 s |
| 2 | 8.79 | 1.76 | 17.2 s |
| 4 | 13.70 | 2.74 | 17.5 s |
| 8 | 30.26 | 6.05 | 57.2 s |
| 0 (=16) | 53.63 | 10.73 | 94.8 s |

At one worker the ratio is 1.00 to two decimals, and a whole-portfolio run at total budget 15 consumed
exactly 15.0. **`max_deterministic_time` was never failing.** The earlier reading mistook an aggregate
for an overrun — the same error shape as C-13: a plausible reading nobody tried to falsify.

**Refuted: "Reproducibility holds … and the search keeps its parallelism."** These cannot both be true.
Two identical portfolio runs on the reference instance, same seed, same weights, same budget:

| workers | wall | distinct candidates | identical across two runs |
|---|---|---|---|
| 1 | 78 s | 1 | **yes** |
| 1 | 255 s | 2 | **yes** |
| 4 | 61–76 s | 2 then 1 | **no** |
| 4 | 262 s | 3 | **no** |
| 0 (=16) | 306 s | 3 | **no** |

On the tiny instance *every* run proved optimality and still disagreed at 8+ workers: the solver is not
being cut short, it is finding **different optimal solutions** and returning whichever worker reported
first. Bounding deterministic time makes the *amount of work* deterministic; it does not order the
race. A fixed seed does not either.

Note also that 4 workers reproduced on the tiny instance and failed on the reference one — **a worker
count that looks deterministic on a small instance is not evidence about a real one.**

**What survives of ADR-011:** all of it. The deterministic budget is sound, measured and calibrated;
and the reproducibility claim is true once `interleave_search = true` is also set — a parameter the ADR
never named. Deterministic time bounds the *amount of work*; interleaving orders the *race*. Both are
needed and the ADR only had one. Resolved and implemented under **C-16**; ADR-011 is amended, not
reversed.

### C-3 — Normalisation bounds · RESOLVED → instance-derived · ADR-009

SRS §6.7 says bounds are "computed from the data of the run", ambiguous between the *instance* and the
*candidates produced*. The candidate-derived reading is excluded on three grounds:

1. **It breaks monotonicity**, which SRS §7.5 requires.
2. A run yielding two candidates degenerates to a 0 / 100 split.
3. **It silently invalidates cross-run comparison** — a regenerated candidate lives under a new run and
   would carry different bounds, so comparing it against the originals compares two scales. That is
   exactly what FR-23 exists to support.

**Decision: bounds derived from the instance, stable across every run on it.**

### C-8 — Who loads the department data · RESOLVED → the person in charge

CdC §3.1 puts data loading under the person in charge; CdC §4.3 and SRS §3.3 both say the administrator
does it; SRS Table 2 gives the person in charge read/write on **all** data and limits the administrator
to accounts and calendar.

**Decision: SRS Table 2 is authoritative.** The two flow sentences are imprecise prose.

**Related, unresolved but low-impact:** CdC Table 1 lists a fifth actor, **"Head of department"**
("examines the teaching loads and approves the timetable"), appearing in no other document with no
requirement, right, screen or acceptance test. **Treated as an out-of-system stakeholder.** Say
otherwise if the institution expects an approval step in the application.

---

## RAISED AFTER THE FIRST READING — two still open, fourteen since resolved

*Kept in discovery order rather than re-sorted, so cross-references from other documents and from
commit messages still land on the right section. **Every heading states its own status** — trust the
heading, and the index above, over the position on the page.*

### C-4 — The raw value of every soft criterion is undefined · **RESOLVED 2026-07-30 → seven formulas, recorded here**

S2–S10 had codes, names and weights but no measurement formula. `v_i(k)` feeds the score, the
contributions, monotonicity, dominance and the weight learning, so this was the single most
load-bearing undefined quantity in the specification.

**Shared building block (S2, S7, S10): leaf-group ancestor-or-self occupancy.** A "leaf group" is any
group that is no other group's `parent_group` (the 30 TP groups on the reference instance, computed
generically rather than assumed, so a future instance with a different depth still works). For a leaf
group `g`, the periods it occupies on a day are the union of periods occupied by sessions belonging to
`g` **or any ancestor of `g`** — the same relation H12 already uses, reimplemented independently inside
`analysis/` from `Group.parent_group` (plain domain data), because `analysis/` may not import the
solver (invariant 1). This is required for S2 specifically: a TP subgroup's students also sit through
their TD's and their promotion's sessions, so idle time computed only from the leaf's own sessions
would understate what the students actually experience, and computing it at every hierarchy level would
triple-count the same gap.

| Code | `v_i(k)` | `min_i` / `max_i` | Reasoning |
|---|---|---|---|
| **S2** Student idle time | Σ over leaf groups `g`, days `d`: `(last_occupied − first_occupied + 1) − occupied_count`, only on days with ≥1 occupied period, via ancestor-or-self | `min=0`. `max = Σ_g min(days_open, n(g)) × (P−1)`, `n(g)` = sessions in `g`'s ancestor-or-self chain, `P` = periods/day (5) | Direct match to `LimitIdleTimesConstraint` (the catalogue's own xhstt_ref), applied per leaf group rather than per hierarchy level |
| **S3** Teacher idle time | Same gap formula, per teacher, no hierarchy | `min=0`. `max = Σ_t min(days_open, n(t)) × (P−1)` | Same XHSTT constraint, teacher-side |
| **S4** Extra working day | Σ over teachers `t`: `max(0, days_used(t) − ⌈total_periods(t)/P⌉)` | `min=0`. `max = Σ_t (days_open − ⌈total_periods(t)/P⌉)` | `ClusterBusyTimesConstraint` does not name a resource. Chose *teacher* over *leaf group*: S3 already penalises gaps within a day a teacher is present, but not a teacher spread thinly across many low-load days — S4 fills exactly that gap. This is a judgment call, not a derivation; leaf group was a defensible alternative |
| **S5** Teacher preference | See C-12 | See C-12 | See C-12 |
| **S6** Room efficiency | Σ over rooms `r`: `\|utilisation(r,k) − target(type(r))\|`, `target(τ) = Σ(duration of sessions requiring τ) / (rooms of type τ × 28 open slots)`, `utilisation(r,k)` = `r`'s occupied periods in `k` / 28 | `min=0`. `max = Σ_r max(target(type(r)), 1 − target(type(r)))` | Resolves the catalogue's "dead half": H5 already forbids over-capacity, so "over-used" means *booked more intensively than its room type's average*, not literal over-capacity. Per-type target is required — Lab_Info runs near 91% occupancy, Salle near 29%, so a single global target would misclassify every lab as over-used |
| **S7** Subject spread | Σ over (leaf group `g`, course `c`, day `d`): `max(0, count(sessions of c reaching g on day d) − 1)`, via ancestor-or-self | `min=0`. `max = Σ_(g,c)` `(total sessions of c reaching g − 1)` | `occurrences_per_week=1` for every session in this instance, so ITC-2007's course-repetition reading of "spread" doesn't apply. Real signal exists anyway: a leaf group can see the same course's CM (via its promotion ancestor), TD (via its TD ancestor) and TP (directly) all on one day — exactly what `SpreadEventsConstraint` penalises |
| **S10** Lunch break (weight 0) | Σ over leaf groups `g`, days `d`: 1 if `g` occupies the lunch period that day, else 0. Lunch period derived from the data (the `period_index` whose slot straddles 12:00 — `P3`, 11:50–13:20, on this instance), not hardcoded | `min=0`. `max = (leaf groups) × days_open` | Weight 0 means it never affects the score, but it is still shown as a sub-score and still enters the dominance check ("every criterion", not "every weighted criterion") |

**Not literally the ITC-2007 definitions for S4 and S6**, despite the "can partly inherit" note below
being kept for its historical reasoning. ITC-2007's `MinimumWorkingDays` (S4's nearest analogue) is
defined per *course* with repeated weekly occurrences, which this instance's data model does not have.
ITC-2007's `RoomStability` (S6's nearest analogue) is about a course reusing rooms, not utilisation
rate — the catalogue's own wording ("under/over-utilised") was followed instead, since S6's `xhstt_ref`
is empty.

**Layering consequence, worth recording so the two implementations don't drift.** `docs/architecture.md`'s
module map states `solver` depends only on `domain`, not `analysis`, and that the decision layer "may
not read a score." So `solver/objective.py` cannot import `analysis`'s `Bounds`/`Criterion` to weight its
CP-SAT objective by normalisation range — it independently re-implements these same seven formulas as
CP-SAT linear expressions, weighted by the profile's **raw** weights, matching `constraint-model.md`'s
plain `minimise Σ(weight_i × violations_i)` (no normalisation there — that stays an `analysis/`-only
concept, computed after the fact for scoring and ranking). The same mathematical definition is
therefore written twice, once per layer, by construction of the layer boundary, not by oversight.

⚠️ **That duplication drew blood immediately, and the lesson is about units, not shape.** The first
implementation of S6 was structurally correct in both layers and still wrong: `analysis/criteria.py`
measured a sum of *fractions* (`occupied/28 − target`), `solver/objective.py` the same quantity in
*periods*, which is `open_slot_count` = 28 times larger. Nothing failed, nothing looked odd — the
solver simply priced S6 **28× above every other criterion** while the interface displayed the
fractional scale, so "weight 0.10 on S6" meant two different things on either side of the boundary.
Caught by review, not by a test. Fixed by scaling S6's objective weight by `1/(rooms_type ×
open_slots)` and multiplying the deviation through by `rooms_type` to keep the target integral (the
earlier `round()` turned a true target of 11.71 periods into 12, leaving a residual penalty even for a
perfectly balanced assignment). Measured effect on the reference instance under catalogue weights:
S2 19 → 2, S7 29 → 14, S6 1.77 → 1.53, overall score 83.6 → 85.5 — the distortion had been consuming
search effort that belonged to the criteria actually carrying weight.

**The guard that now exists:** `tests/integration/test_objective_matches_analysis.py` solves a tiny
instance with one criterion at weight 1.0 and asserts the CP-SAT objective value equals the analysis
layer's recomputation on the same placements. **Two implementations of one formula agreeing in shape is
not evidence they agree in scale.** S6 is not covered by that test — on any instance where a room type
is fully interchangeable it is cumulative-encoded and the objective posts no S6 term at all.

**Superseded, kept for its original reasoning:** S2, S4, S6 "can partly inherit from the ITC-2007
curriculum-based definitions" — true for S2, not for S4/S6 as explained above. S3, S5, S7, S10 remain
project-specific with no published definition, now given one above (S5 via C-12).

**Blocks:** Phase 3 scoring — now unblocked. **Owner:** technical lead, decided 2026-07-30.

### C-14 — Dominance uses the strict reading, and S10's zero weight makes that bite · **RESOLVED 2026-08-05 → Pareto, and the signal moves off the top candidate**

`docs/scoring-and-explanation.md` says "a candidate that another **improves on every criterion** is
dominated". `analysis/ranking.py` implements exactly that: strict `>` on every criterion. The textbook
Pareto rule is weaker — "at least as good on all, strictly better on at least one" — and the two differ
precisely when two candidates **tie** on a criterion.

That is not a hypothetical gap here. **S10 carries weight 0**, so nothing optimises for it, and ties on
it are ordinary rather than rare. Under the strict rule a candidate beaten on six criteria and merely
tied on S10 is reported as *not* dominated — which is the exact situation the dominance signal exists
to surface ("the weights are concealing a compromise rather than expressing one").

The implemented behaviour follows the written specification, is documented in `ranking.py`'s
`dominance()` docstring, and is pinned by
`tests/property/test_scoring_properties.py::test_a_candidate_tied_on_one_criterion_is_not_reported_dominated`
so nobody "fixes" the `>` to `>=` without meaning to. **Changing it is a specification decision, not a
keyboard one** — hence recorded rather than silently switched.

#### New evidence, 2026-07-30 (found while implementing FR-16): the "dominated top candidate" signal is unreachable

`docs/scoring-and-explanation.md` says the interface signals dominance "when it happens to the
top-ranked candidate", and FR-16 repeats it: "a dominated top candidate is signalled alongside".
**That state cannot occur.** If `B` dominates `A` then `n_i(B) > n_i(A)` for every criterion, so

```
score(B) − score(A) = 100 × Σ ( w_i × ( n_i(B) − n_i(A) ) )
```

is a sum of non-negative terms, and renormalised weights sum to 1 so at least one weight is positive.
Therefore `score(B) > score(A)` **strictly**, and `A` can never be top-ranked. Confirmed by search over
200,000 random dominated pairs and random weight vectors: zero counterexamples. It holds under the
Pareto reading too, because `TIE_BREAK_ORDER` covers all seven criteria, so a tie on score still
resolves in the dominator's favour.

Three things follow, none of which is a decision:

1. **`Recommendation.dominated_by` is dead code today** — provably, not incidentally. It is kept
   because the specification requires the signal and because resolving C-14, or any change that makes
   the score non-linear or admits a negative weight, would revive it. Pinned by
   `tests/property/test_scoring_properties.py::test_a_dominated_candidate_is_never_recommended` and by
   two unit tests, so it stays dead *visibly*.
2. **Dominance itself is not dead.** Only the *top-candidate* case is unreachable. A dominated
   runner-up is ordinary and the comparison screen can still report it.
3. **The stated rationale for surfacing it does not survive.** "If the highest-scoring candidate is
   dominated, the weights are concealing a compromise" describes a situation the arithmetic forbids.
   Whatever C-14 decides, that sentence in `docs/scoring-and-explanation.md` needs rewording — the
   useful signal is a dominated candidate *anywhere* in the portfolio, not at its head.

**Blocks:** nothing today; dominance is reported, not acted on. Decide before the comparison screen
(Phase 4) presents the signal to a user — and note that Phase 4 would otherwise implement a signal
that can never fire. **Owner:** technical lead, with the supervisor if the wording in the specification
is to change.

#### DEFERRED 2026-08-01 by decision of the technical lead — no dominance signal in Phase 4

**The question is not answered; the Phase 4 comparison screen simply does not present a dominance
signal at all.** `features/comparison/ComparisonScreen.tsx` shows the two candidates and the
decomposition, and nothing about dominance.

**Why deferring is not the same as ignoring.** The reason the signal was on Phase 4's list is that both
specification documents ask for it. Building it under the current reading would have shipped an
indicator that is *provably* always empty — worse than absent, because a control that never fires
teaches the user it means "no problem found" rather than "this cannot happen". Absence is the honest
state until the reading is settled.

**What is unaffected.** `GET /runs/{id}/dominance` and `DefaultRanker.dominance()` exist, are tested and
are correct under the strict reading; nothing was removed. `Recommendation.dominated_by` is still
computed and still provably `None`. Only the *display* is withheld.

**What this defers.** The choice between the strict and the Pareto reading, and the rewording of
`docs/scoring-and-explanation.md` §Dominance (lines about "when it happens to the top-ranked
candidate") and its Recommendation rule ("a dominated top candidate is signalled alongside"). Both
still describe a state the arithmetic forbids. **That wording is a delivered commitment, so changing it
needs the supervisor** — which is part of why it was not settled inside Phase 4.

**Now blocks:** FR-17's `✓`, and the Phase 6 acceptance work. Carry it there with C-5 and C-9.
**Owner:** technical lead, with the supervisor.

#### RESOLVED 2026-08-05 → Pareto, and the signal moves off the top candidate

**Two defects were recorded here, and the decisive fact is that they are independent.** Switching to
Pareto does **not** make the top-candidate clause reachable: `TIE_BREAK_ORDER` covers all seven
criteria, so a tie on score still resolves in the dominator's favour and a dominated candidate still
cannot rank first. Each had to be decided separately, and both were.

**(i) The reading — decision: the standard Pareto rule.** A candidate is dominated iff some other
candidate is **at least as good on every criterion and strictly better on at least one**.
`analysis/ranking.py` is changed from the strict `>`-on-everything rule to this one.

*Why.* The strict rule's failure mode is **silence exactly when the signal matters**. S10 carries
weight 0, nothing optimises for it, and ties on it are ordinary rather than rare — so a candidate
beaten on all six weighted criteria and merely tied on the seventh was reported *not dominated*. That
is the concealed compromise the feature exists to expose, and the rule that was implemented called it
fine. Second reason: "dominated" is a standard term in multi-objective optimisation, and a report using
it in a non-standard sense misleads any reader who knows what it normally means.

*The argument against, recorded because it is real:* the strict rule never over-reports, and under
Pareto a verdict can be triggered by a candidate that is merely *equal* on the one criterion carrying
no weight. That was weighed and rejected — a signal that cannot fire when it should is worse than one
that fires when the difference is small, because the first teaches the user it means "no problem
found".

**(ii) The unreachable clause — decision: signal a dominated candidate *anywhere* in the portfolio.**
The wording "the interface signals it when it happens to the top-ranked candidate" describes a state
the arithmetic forbids, so leaving it was the only option that was definitely wrong.
`docs/scoring-and-explanation.md` §Dominance and §Recommendation rule are reworded accordingly, and the
ERRATA table carries the replacement wording for the CdC and SRS sentences FR-16 and FR-17 derive from.

*Why not delete the signal instead.* `DefaultRanker.dominance()` and `GET /runs/{id}/dominance` are
exact, parameter-free, already built and already tested, and **ADR-002 adopted dominance deliberately
as a complement to the weighted sum**. Discarding a working complement because one clause about it was
impossible would be throwing away the feature to fix the sentence.

**What changes in the software:**

| | Before | After |
|---|---|---|
| `DefaultRanker.dominance()` | strict `>` on every criterion | `>=` on every criterion **and** `>` on at least one |
| `test_a_candidate_tied_on_one_criterion_is_not_reported_dominated` | pinned the strict reading | replaced by its Pareto counterpart — a tie on one criterion with a strict gain elsewhere **is** dominance |
| The comparison screen | no dominance signal at all (deferred 2026-08-01) | reports a dominated candidate wherever it appears in the portfolio |
| `Recommendation.dominated_by` | provably always `None` | **still provably always `None`** — see below |

⚠️ **`Recommendation.dominated_by` stays dead, and stays for a reason.** The proof that a dominated
candidate cannot rank first holds under Pareto too. The field is kept because FR-16's statement names
it and because any change making the score non-linear, or admitting a negative weight, would revive it;
`test_a_dominated_candidate_is_never_recommended` keeps it dead **visibly**. Do not read this
resolution as having made that field reachable — the signal that now fires is the portfolio-wide one,
which is a different thing.

**Blocked:** nothing. FR-17's `✓` is unblocked. **Resolved by:** project owner, 2026-08-05.

### C-15 — The objective weights raw violation counts of incomparable scale · **RESOLVED 2026-08-07 → teacher-favouring raises S3 and S4, and a profile's promise is reworded**

⚠️ **The heading above states the ORIGINAL diagnosis, and the resolution at the foot of this section
refutes it.** The problem was never the objective's formulation — it was *which criteria the profile
raised*. Read the resolution before acting on anything between here and there; the analysis in between
is kept because its measurements are real and its reasoning error is instructive, exactly as C-13's is.

`docs/constraint-model.md` specifies the objective as `minimise Σ ( weight_i × violations_i )`, in
**raw** units. The seven criteria do not share a scale: on the reference instance S5 measures ~100
(a count of sessions) while S3 measures ~15 (idle periods). A weight therefore does not mean the same
thing from one criterion to the next.

**The visible consequence.** The teacher-favouring profile raises S3 and S5 (0.15 → 0.30, 0.20 → 0.40,
`services/portfolio.py`). Inside the objective S5 then contributes ≈ 0.4 × 80 = 32 against S3's
≈ 0.3 × 15 = 4.5, so the profile behaves as an S5-only profile. Measured across budgets on the
reference instance: S5 improves 101 → 72 (beating balanced's 81) while S3 *degrades* 13 → 18.
**"Teacher-favouring" does not currently favour teachers on S3.**

This is not an implementation defect. `analysis/criteria.py` scores both criteria correctly,
`solver/objective.py` encodes both correctly, the profile raises both weights as documented, and the
cross-layer test (`tests/integration/test_objective_matches_analysis.py`) passes. Every part is right
and the composition still does not do what the profile's name promises.

Three ways this can go:

- **(a) Normalise the objective's weights** by each criterion's instance-derived bound range, so a
  weight means the same thing everywhere. Closest to what the profiles claim. Cost: the solver's
  objective and the displayed score become two different scales, which `solver/objective.py` currently
  documents as a deliberate separation — that reasoning would need revisiting, not merely editing.
- **(b) Per-criterion emphasis factors** instead of the flat `EMPHASIS = 2.0`. Cheap, keeps the raw
  objective, but the factors are arbitrary and need justifying one by one.
- **(c) Accept it and rename the profile.** If it is an S5-optimising profile, "teacher-favouring"
  oversells it and the comparison screen would mislead.

**DEFERRED 2026-07-30 by decision of the technical lead.** Recorded, not resolved; the objective is
unchanged, and Phase 3 was closed on 2026-07-31 against that current behaviour rather than waiting for
this. **Phase 3 was not blocked by it** — its completion criterion is that three profiles produce
scored candidates, which they do (3 distinct, 0 duplicates). What this still blocks is calling **FR-13**
finished, because the profiles do not yet differentiate for the documented reason.

**Blocks:** FR-13's eventual `✓`; the Phase 4 comparison screen, which would otherwise explain a
difference by a cause that is not the real one. **Owner:** technical lead.

#### RESOLVED 2026-08-07 → teacher-favouring raises S3 and S4, and a profile's promise is reworded

⚠️ **Everything above misdiagnoses the problem, and the three obvious fixes are all wrong.** Six
measurements were taken on the reference instance (seed 42) before anything was changed. They are
recorded in full because the dead ends are more useful than the conclusion.

**First, the symptom is worse than this section says.** C-15 records *"favours only S5, not S3"*. Measured
head-to-head at production settings — which the original evidence never did, it compared **one profile
across budgets** — teacher-favouring is the **worst of the three on every teacher criterion at once**,
and on the overall score:

| profile | S3 | S4 | S5 | score |
|---|---|---|---|---|
| balanced | 22 | 57 | 100 | 82.87 |
| student-favouring | 24 | 58 | 100 | 83.00 |
| **teacher-favouring** | **29** | **65** | **103** | **79.45** |

It wins only S10, which carries weight 0.

##### The four refuted hypotheses

**(1) Normalise the objective by each criterion's bound range** — the fix this section proposes first.
**Refuted analytically.** S3's instance-derived range is **752, the largest of the seven**; S5's is 218.
Dividing by the range therefore shrinks S3's coefficient *most*. Raw S3:S5 = 1 : 1.33; range-normalised
= **1 : 4.6**. It makes the imbalance **3.4× worse**. Measured ranges: S2 720 · S3 752 · S4 172 · S5 218
· S6 12.64 · S7 268 · S10 180.

**(2) Renormalise each profile's weights to sum to 1.** **Refuted empirically** — teacher-favouring
returned a **bit-identical** timetable (S3=29, S4=65, S5=103, score 79.45). It must: `minimise Σ(wᵢvᵢ)`
and `minimise Σ((wᵢ/T)vᵢ)` share an argmin, so scaling an objective cannot move its optimum. A theorem
the experiment re-derived the expensive way.

**(3) The per-profile budget is too small.** **Refuted.** Tripled to 90 per profile: teacher-favouring's
own timetable stayed **~16 objective units worse on its own objective** than a sibling profile's
(16.50 at budget 30, 15.65 at budget 90). Convergence is not the mechanism.

**(4) The S3/S5 objective terms are miscoded** — the C-4 S6 failure repeating. **Refuted.** Solving with
one criterion carrying all the weight: **S3-only reaches 0, proven optimal, using 14.45 of 90 budget
units**; S5-only reaches 48 against balanced's incidental 84. Both terms work.

##### The actual mechanism, and why the profile was indefensible

**S3 is cheap and S5 is expensive.** S3 alone is *proven optimal at zero* in 14 units; S5 alone consumes
the entire 90-unit budget and proves nothing. Teacher-favouring put its **largest single weight** (0.40,
leverage 0.40 × 218 = 87.2) on the expensive criterion, so the budget drained into S5 and every other
criterion drifted — **including S5 itself**, which ended at 103 against balanced's 100.

**And S5 is not teacher preference.** **C-12** records it as *"a labeled stand-in for real preference
data, not a definition of teacher preference"* — `teacher_availability.csv` has no preferred-window
column, so S5 counts sessions at the edge of the day. A *teacher-favouring* profile was therefore
spending 40 % of its weight on a proxy for data that does not exist, while under-weighting the two
criteria that measure teacher experience from real placements. **C-4 chose *teacher* as S4's resource
for exactly this purpose**: *"S3 already penalises gaps within a day a teacher is present, but not a
teacher spread thinly across many low-load days — S4 fills exactly that gap."* S3 and S4 together **are**
teacher welfare in this model; S5 is a placeholder.

##### The decision, in two parts

**(i) `teacher-favouring` raises S3 and S4**, not S3 and S5. This is a deliberate change to
`docs/constraint-model.md`'s profile definition, taken on the evidence above. Measured effect:

| | S3 | S4 | S5 | score |
|---|---|---|---|---|
| before (raises S3, S5) | 29 | 65 | 103 | 79.45 |
| **after (raises S3, S4)** | **0** | 69 | **95** | **81.10** |

S3 reaches **0 — the proven single-criterion optimum** — and teacher-favouring now holds the best S3
*and* the best S5 of the three profiles, having previously held neither.

**(ii) What a favouring profile PROMISES is reworded**, because the old implicit promise is
unachievable and that is what made this look like a defect:

> **A favouring profile produces the best value of its headline criterion among the three candidates.**
> It does **not** promise to win every criterion of its constituency.

⚠️ **No weighted-sum scalarisation can deliver the stronger promise, and that is provable here rather
than asserted:** S3-only drives S5 to 113; S5-only drives S4 to 73. The teacher criteria genuinely
conflict, so a profile that wins all of them does not exist at any weighting. Under the new profile
`balanced` still holds the best S4 (57 vs 69) and the best *normalised* teacher aggregate — because S4
has the smallest range of the three (172), so a unit of S4 moves that aggregate most. **That is
multi-objective reality, and it is now stated instead of read as a bug.**

##### What this does not change

`minimise Σ(weightᵢ × violationsᵢ)` is **untouched** — raw weights, exactly as
`docs/constraint-model.md` specifies. `solver/objective.py` is untouched, and its docstring's refusal to
normalise inside the solver is **vindicated**, not overruled. Scoring, ranking and the exact
decomposition are untouched: profiles steer the *search*, and `scoring_weights` prices every candidate
under one vector. No import contract moves.

**Blocked:** nothing. **FR-13's `✓` is unblocked.** **Resolved by:** lead engineer, 2026-08-07, on
measurement.

### C-18 — Nothing says where the first account comes from · **RESOLVED 2026-08-04 → a seed command** · ⚠️ **its scheduling clause superseded 2026-08-11**

SRS Table 2 gives the **administrator** account management, and C-8 already settled that Table 2 is
authoritative where the flow prose disagrees. But no requirement describes **registration**, no screen
collects it, and the instance carries no user data at all — `teachers.csv` has ids, departments, ranks
and weekly load, and nothing that identifies a person. So FR-11 can be built and still leave nobody
able to sign in.

This is a gap in the specification rather than a contradiction inside it, which is why it is recorded
here before the code rather than decided inside it.

**Decision: a seed command**, `python -m optiedt.services.seed`, creating one person in charge, one
administrator, one student and **one account per teacher in the instance**, each linked to its
`teacher_id`. Passwords are read from the environment or generated and printed once, never committed.

⚠️ **`services/`, not `db/`** — this entry said `optiedt.db.seed` when it was written, and that was
wrong: the command needs the instance loader and the store factory, and `db` depends on `domain`
alone. Writing it there would have added two upward imports to make a script's name prettier.

**Why not an admin-managed CRUD**, which is what Table 2 literally implies: it needs the first
administrator to exist anyway, so it does not answer this question — it moves it. The endpoint is
worth building when accounts are managed for real; it is not what makes the demonstration reachable,
and Phase 5 has two budgeted days for four requirements.

**What this costs, stated plainly.** Account management through the interface is **not delivered** by
Phase 5. FR-11 is "authenticate users and restrict access by role", and that is what M4 builds; the
administrator's account-management right from Table 2 stays unimplemented and belongs with FR-1's data
management. Do not read a green FR-11 as covering it.

✅ **DELIVERED 2026-08-11 by Phase 11 — and the sentence above about *where* it belongs was superseded
rather than fulfilled.** `api/routers/accounts.py` gives the administrator list, create and remove;
`acceptance/test_fr11.py` covers them end to end and **FR-11 is `✓`**.

⚠️ **The scheduling clause — "belongs with FR-1's data management" — was a remark made under Phase 5's
budget, not a scope ruling, and the repository disagreed with itself about it for a week.**
`docs/project-roadmap.md` put account management in Phase 11; this entry put it in Phase 12. **The
project owner opened Phase 11 naming FR-11 among its requirements**, which settles it. The reading that
supports that decision was already recorded in the roadmap's handoff: **SRS Table 2 pairs accounts with
the calendar under one actor**, and **C-8** had already settled that Table 2 wins where the flow prose
disagrees — so accounts belong beside the calendar screen, and FR-1 remains Phase 12's alone.

⚠️ **What has NOT changed: the seed command is still how the first accounts exist**, and it still
refuses to run on a populated system. A management screen cannot create the account that reaches it —
which is the very objection this entry raised against an admin-managed CRUD in 2026-08-04 ("it needs the
first administrator to exist anyway, so it does not answer this question — it moves it"). **Both are
needed, and both are present.**

⚠️ **The seed is a development and demonstration tool, not a deployment mechanism.** It creates
accounts with known roles on a machine that has no authentication until it runs. It must never be run
against an installation that has real users, and the command says so before it writes anything.

**Blocked:** nothing. **Owner:** technical lead, decided 2026-08-04.

### C-17 — Assumption literals defeat presolve · **RESOLVED 2026-08-04 → deletion-based subset search**

`docs/architecture.md` stage 3 specifies the mechanism: *"Constraints are declared under enforcement
literals passed as assumptions. The solver returns a subset explaining the infeasibility."* That is
what Phase 5 M2 built, and **it works** — 14 tests in `tests/unit/test_diagnosis.py` pin it against
real CP-SAT, naming exactly `('H1',)`, `('H12',)` or `('H3',)` on instances designed so only one rule
can be at fault.

**It does not work on this project's own instance**, and the reason is not budget.

#### The measurement

Same instance, same model, same infeasibility. Four computer laboratories withdrawn, so `Lab_Info`
demand is 160 periods against 4 rooms × 28 = 112 available — an **area** contradiction, exactly the
kind `AddCumulative` reasons about:

| | status | wall clock |
|---|---|---|
| Plain solve, 1 worker | **INFEASIBLE** | **0.0 s** |
| Plain solve, 4 workers | **INFEASIBLE** | **0.0 s** |
| **Under four assumption literals**, 1 worker, budget 120 | **UNKNOWN** | **240 s** (wall-clock ceiling) |

**Attaching an enforcement literal to `no_overlap` and `cumulative` removes them from presolve.** They
stop being facts the propagators may reason with and become conditional obligations, so the
contradiction CP-SAT found instantly is no longer visible to it. This is a property of the encoding,
not of the budget: a 4× budget increase changed nothing.

Both realistic infeasibilities behave this way — the area case above, and the original pre-C-13 room
mix (the contiguity case). In both, the run reaches `DIAGNOSED` carrying *"inconclusive"*, which is
honest and useless.

#### The alternative, also measured

**Deletion-based conflict search**: keep every constraint hard and solve *subsets*. Start with all
four assumable rules; for each in turn, solve without it, and drop it permanently if the model is
still infeasible. Every solve is a plain solve, so presolve keeps working.

| Instance | Result | Solves | Wall clock |
|---|---|---|---|
| Four laboratories withdrawn (area) | **`('H3',)`** — the actionable answer | 4 | **1.6 s** |
| The original pre-C-13 mix (contiguity) | `('H1','H3','H7','H12')` — nothing could be dropped | 4 | 92 s |

The second row is the honest outcome rather than a failure: **CP-SAT cannot prove that infeasibility
at all** — that is precisely what C-13 was — so every subset solve returns `UNKNOWN`, nothing can be
dropped, and no method resting on a CP-SAT proof can name the rule. **The pre-analysis catches it**,
and does so in milliseconds. An implementation must therefore distinguish "kept because removing it
stayed infeasible" from "kept because the subset solve was inconclusive", or the second row reads as a
confident four-rule verdict.

#### What this costs, and what it does not

Three things stated in `docs/architecture.md` as *"imposed by CP-SAT itself, not choices"* would change
under the alternative, and they were only ever imposed **by the assumption mechanism**:

- **A single worker.** Needed because solving under assumptions admits no parallelism. Subset solves
  are ordinary solves and can use every worker — though reproducibility then needs `interleave_search`
  (C-16), which is a live constraint, not a free choice.
- **The result is sufficient, not minimal.** A deletion search tests each removal, so the surviving set
  *is* minimal with respect to the four. `DiagnosisResult.is_minimal` could become true — but only when
  no subset solve was inconclusive.
- **No objective.** Unchanged; a feasibility subset solve posts none either.

**Unaffected:** C-6 (still exactly four relaxable rules, still 1:1 and non-redundant), the report's
shape, the API, and the screen. This is a change of *how the set is computed*, not of what it means.

#### Options

- **(a) Keep the assumption mechanism, record the limitation.** Matches the documented design exactly.
  Ships a diagnosis that is inconclusive on every infeasibility this project can actually produce.
- **(b) Replace it with deletion-based subset search.** Answers correctly and fast where a proof
  exists, degrades honestly where none does. Costs a change to `docs/architecture.md`'s stage 3 and to
  two of its three "imposed" properties.
- **(c) Both: try assumptions under a small budget, fall back to subset search.** Most faithful to the
  documented design and the most code; the fallback would fire every time on this instance, so the
  first half would be paying for nothing.

#### RESOLVED 2026-08-04 → (b), deletion-based subset search

**Decision: replace the assumption mechanism.** `Solver.diagnose` now establishes infeasibility with
one plain solve, then withdraws each assumable rule in turn and keeps the rule only when the model
without it stops being infeasible. Every solve is plain, so presolve keeps working.

**What the report gains.** `('H3',)` in 1.6 s on the area case, where assumptions gave 240 s of
`UNKNOWN`. And because each removal is *tested*, the surviving set is irreducible rather than merely
sufficient — `is_minimal` can now be true, and is set **only when every removal was decided**. A
subset solve that returns `UNKNOWN` keeps its rule for want of evidence, and the report says so rather
than presenting an untested set as minimal.

⚠️ **"Minimal" here means irreducible with respect to the four relaxable rules, with all the others
enforced.** It is not the smallest explanation in any absolute sense — H4–H6 and H8–H10 are always
present and can be the real cause, in which case *every* rule is dropped and the set comes back empty.

**What changed in the documented design**, all in `docs/architecture.md` stage 3:

- The mechanism itself: subset solves, not enforcement literals.
- **"A single worker"** — it was imposed because solving under assumptions admits no parallelism. That
  reason is gone. One worker is kept anyway, and the new reason is **reproducibility of the verdict**:
  `max_deterministic_time` is a per-worker budget, so more workers do more total work and could flip an
  `UNKNOWN` to an `INFEASIBLE` between machines. A conflict report that named different rules on
  different machines would be worse than none.
- **"Sufficient, not minimal"** — now sufficient *and* irreducible, when every removal was decided.

**Unchanged:** C-6 (still exactly four relaxable rules, still 1:1 and non-redundant), no objective, the
`DiagnosisResult` shape, the API and the screen. `ConstraintBuilder.apply` loses the literal parameter
it briefly carried — with no mechanism using it, it was dead weight, and the Phase 4 audit's lesson
about dead code applies.

⚠️ **`carries_assumption_literal` keeps its name and no longer describes a literal.** It selects which
constraints the deletion search may withdraw — the same four, for the same reason: they are the only
posted objects. The name is referenced by C-6's recorded resolution in four documents, so renaming it
mid-phase would cost more clarity than it buys. **Read it as "may be withdrawn individually".**

**Blocked:** nothing. **Resolved by:** technical lead, 2026-08-04, on measurement.

### C-16 — Reproducibility and portfolio diversity · **RESOLVED 2026-07-30 → both, via `interleave_search` and withholding the hint**

**The conflict was not real.** It was an engineering defect with an engineering fix, and the analysis
below — which concluded the two criteria were mutually exclusive — was wrong. It is kept in full
because the measurements are real and the reasoning error is instructive: **every configuration tested
had two variables changed at once**, worker count and search strategy, so the diversity collapse was
attributed to low parallelism when it was actually caused by the warm start.

#### The resolution

**Set `interleave_search = true` and withhold the warm start when an objective is posted.** Both are in
`solver/engine.py`; ADR-011 is amended accordingly.

- `interleave_search` is documented as making the search *"deterministic (independently of
  num_workers!)"*, and measurement confirms it — deterministic in every configuration tested, at full
  parallelism. ⚠️ **It has one measured side effect, found 2026-07-31**: `CpSolver.objective_value` can
  be reported above the objective at the solution actually returned, on solves that stop before proving
  optimality. It changes nothing here — no score or ranking reads that field — and **ADR-011 is the
  authority on it**, not this section.
- The warm start was pinning all three profiles to one timetable: identical score **78.076** at total
  budgets 15, 45 *and* 90, across three different objectives. Withholding it under an objective
  restores diversity.

**Verified against every Phase 3 criterion before adoption**, plus H1–H12 re-derived from the raw CSVs
for all three candidates and the feasibility path — 32 hard-constraint checks, all passing:

| | before | after |
|---|---|---|
| Portfolio wall clock | 306 s | **147–150 s** |
| Distinct candidates | 3 | **3** |
| Reproducible | ❌ | **✅** |
| Best score | 82.23 | 80.31 |

Twice as fast, reproducible, three candidates, at ~1.9 score points — the luck of a racing search,
given up deliberately. **No acceptance criterion needed to change.**

⚠️ `interleave_search` is marked **Experimental** upstream. `tests/integration/test_reproducibility.py`
verifies the behaviour at production settings rather than trusting the documentation; pin the OR-Tools
version and treat a failure there as blocking.

---

#### The superseded analysis, kept for its reasoning error

Two increment-1 acceptance criteria are in direct conflict at every setting measured on 2026-07-30
(evidence in C-2 above):

> - [ ] At least three candidates, each with its overall score and sub-scores
> - [ ] Two runs with the same data, weights and seed produce the same candidates in the same order

**Reproducibility requires one worker. Three distinct candidates require many.** No tested
configuration delivers both:

| workers | total budget | wall | candidates | reproducible | which criterion fails |
|---|---|---|---|---|---|
| 1 | 15 | 78 s | 1 | ✅ | three candidates |
| 1 | 45 | 255 s | 2 | ✅ | three candidates |
| 4 | 45 | 262 s | 3 | ❌ | reproducibility |
| 0 (=16) | 15 | 306 s | 3 | ❌ | reproducibility |

The trend at one worker is real — 15 units gave 1 candidate, 45 gave 2 — so a larger budget may reach
three while staying reproducible. That is **untested**, and it costs wall-clock: extrapolating, three
distinct candidates at one worker is roughly 6–9 minutes, past the *estimated* < 5 min figure (which
ADR-011 already demoted from a promise, so exceeding it is not itself a failure).

**Why one worker produces fewer candidates.** The warm start hands every profile the same greedy
solution. At a small per-worker budget the objective cannot move far from it, so all three profiles
return the same timetable and duplicate removal collapses them. Parallelism hides this by exploring
more, not by respecting the profiles better.

#### Options

- **(a) Fix the worker count at 1 for published runs.** Reproducibility by construction, not by
  measurement. Costs parallelism and needs a budget large enough to differentiate the profiles.
  ADR-011's "Workers (stage 2): all available" becomes "1", and the ADR's stated consequence
  ("the search keeps its parallelism") is withdrawn.
- **(b) Keep all workers and withdraw the reproducibility guarantee.** FR-19's acceptance test and
  SRS §7.2 would have to be restated — that is a delivered commitment, so it needs the supervisor.
- **(c) Two modes.** Exploratory runs parallel and unreproducible; a published run re-solved at one
  worker and recorded as the reproducible one. Honest and satisfies both criteria in the place each
  matters, at the cost of a second solve and a more complex run lifecycle.
- **(d) Remove the warm start for favouring profiles**, so they diverge without needing parallelism.
  Speculative — it attacks the cause of the collapse rather than the symptom, and is untested.

~~**Recommendation, not a decision: (c).**~~ **Superseded.** None of (a)–(d) was needed. Option (d)
— "remove the warm start for favouring profiles" — was dismissed above as "speculative"; it was in fact
half the answer, and the half nobody tested. The other half was a solver parameter none of these
options considered.

⚠️ **This interacts with C-5.** At one worker the reference instance produced **one** candidate, not
three — so C-5's "duplicates removed leaves fewer than three" stops being hypothetical and becomes the
observed behaviour. Whatever C-5 decides must hold at the worker count C-16 selects.

**Blocked:** nothing now. Both acceptance criteria are satisfied simultaneously at production
settings. **Resolved by:** technical lead, 2026-07-30, on measurement.

### C-5 — "At least three candidates" can fail when duplicates are removed · **RESOLVED 2026-08-05 → clarify the wording, keep the implementation**

SRS Table 29 says "at most 3, **duplicates removed**". CdC §11 requires "**at least three** candidates";
SRS §8.6 test FR-13 expects "**three distinct** candidates". PPM Table 10 anticipates the collision:
"candidates too similar … duplicates not presented twice".

If two profiles converge on the same timetable the system behaves **correctly** and the acceptance test
**fails**.

Options: (a) restate as "at least two distinct candidates, with profiles chosen so three distinct ones
are obtained on the reference instance"; (b) retain duplicates and flag them as identical.

**This was never a conflict between two behaviours. It is a conflict between a behaviour and a test.**
SRS Table 29 fixes what the software must *do*; CdC §11 and SRS §8.6 fix what the test must *see*. Only
one of the two can be adjusted without changing delivered software, and it is the wording.

#### RESOLVED 2026-08-05 → (a), in two clauses

**Decision, taken by the project owner:** keep duplicate removal exactly as SRS Table 29 specifies, keep
the requirement that the reference instance yields three distinct candidates, and clarify the
specification so the acceptance criterion is tied to **the verified reference instance** rather than to
a general guarantee the software cannot make.

The criterion therefore reads, in two clauses that do different jobs:

> **The general contract:** at most three candidates, duplicates removed.
> **The acceptance criterion:** three *distinct* candidates on the reference instance, at production
> settings (seed fixed, `interleave_search = true`, warm start withheld under an objective — C-16).

**Nothing in `services/portfolio.py` changes.** That is the point of the decision: the implementation
already obeys SRS Table 29, and the contradiction lived entirely in what two other documents promised
about it.

**Why not (b).** Retaining duplicates and flagging them would resolve one contradiction by creating
another — it contradicts SRS Table 29 directly — and it bends the product to fit the test rather than
the test to describe the product. It also makes the criterion trivially true (three are always
returned, so the test can never fail), and it changes a **Phase 3** module's contract with real
consequences downstream: two identical candidates carry identical scores, so `rank()`'s tie-break is
left choosing between clones and `recommend()` can name one of two indistinguishable timetables as "the
highest score under the weights in force".

**Why the acceptance test is not weakened to "at least two".** The measurement is **3 distinct, 0
removed, reproducibly** at production settings. Writing the test as `>= 2` would trade a criterion the
project meets for a weaker one nobody asked for — and it would hide a regression: if a future change
made two profiles converge, a `>= 2` test stays green while the product silently got worse. The test
asserts **exactly three distinct**.

⚠️ **What this costs, stated plainly: the acceptance test is explicitly instance-specific.** That is
already true of every acceptance test in this project, but under this decision it must be *written
down* — if the reference instance changes, the expectation of three has to be re-derived, not assumed.
The general contract (`≤ 3`, duplicates removed) is what holds on any instance, and the software
promises nothing more than that.

⚠️ **The failure mode is real, not hypothetical, and this decision does not abolish it.** C-16 records
the same instance returning **one** candidate at a single worker. Three distinct candidates is a
property of the reference instance *at production settings*, which is why both halves are named in the
criterion. A configuration change can still break it, and the acceptance test is what would catch that.

**Blocked:** nothing. **Resolved by:** project owner, 2026-08-05, on the recorded measurement.

### C-6 — Redundant constraints corrupt the diagnosis report · **RESOLVED 2026-07-30 → four literals only**

**H2 is subsumed by H12** (NoOverlap over the whole promotion→group→subgroup hierarchy already forbids
what H2 forbids). **H11 is implied by H3** once `room[s]` is assigned, and duplicates pre-analysis check
#2 in arithmetic form.

Harmless for feasibility. **Not harmless for the diagnosis run**, whose entire value is naming the rule
the user must change. Overlapping assumption literals let the solver return either, so the report can
name a rule the user cannot act on.

**Decision: only H1, H3, H7 and H12 carry `carries_assumption_literal = True`** — and the reason is
sharper than "avoid redundancy". Those four are the only constraints that are *posted objects at all*.
H2 and H11 are subsumed, so there is no posting to attach a literal to; H4, H5, H6, H8, H9 and H10 are
domain restrictions applied when the variable is constructed, so there is nothing posted either. The
mapping constraint → literal is therefore 1:1 and non-redundant by construction rather than by
convention. Implemented in `solver/constraints/`, not merely decided.

### C-7 — The `y[s][t]` channelling constraint · **RESOLVED 2026-07-30 → start-indicator encoding, built on demand**

`y[s][t]` is up to 6,104 booleans — the dominant term in model size. **104 of the 218 sessions span two
periods**, so `y[s][t]` must mean *occupies* `t`, not *starts at* `t`. The constraint linking
`start[s]`, `iv[s]` and `y[s][t]` across a 2-period duration **appears in none of the three documents**.

Related: SRS Table 27 attributes H7 to `y`, but with `start[s]` an integer over a pruned domain each
session already has exactly one start — `y`'s real purpose is soft-constraint accounting.

#### The decision

**Channel through start indicators, not through the interval.** For each session `s` with duration `d`
and pruned start domain `D(s)`:

```
x[s,t₀] ∈ {0,1}                        for every t₀ ∈ D(s)      "s starts at t₀"
exactly_one( x[s,t₀] : t₀ ∈ D(s) )                              s starts somewhere
start[s] == Σ t₀ · x[s,t₀]                                      channel to the integer
y[s,t]  == Σ { x[s,t₀] : t₀ ∈ D(s), t₀ ≤ t ≤ t₀+d−1 }           "s occupies t"
```

The last line **is** the answer to C-7, and it is uniform in `d` — a 1-period session's `y[s,t]` reduces
to `x[s,t]`, a 2-period session's is `x[s,t−1] + x[s,t]`. Because `exactly_one` makes at most one term
of any such sum true, the sum is always 0 or 1 and the equality is exact: no `≤`/`≥` pair, no big-M, no
reified disjunction.

**Why not reify against the interval** (`y[s,t] ⇒ start[s] ∈ [t−d+1, t]` and the negation, via
`only_enforce_if`)? It needs no `x`, but it costs two constraints per pair instead of one, and it
propagates strictly worse: nothing links the `y[s,·]` of one session to each other, so the solver can
sit with several `y` unfixed while `start[s]` is already decided. The `exactly_one` above is the
standard direct encoding of an integer variable, which CP-SAT's presolve recognises and exploits.

**`x` is not scaffolding — it is the natural variable for three of the seven criteria.** S5 (preferred
windows) and S7 (subject spread) are properties of *where a session starts*; S4 (extra working day) is
a property of which days are touched. Expressing those over `x` is direct; expressing them over `y`
means undoing the double-counting a 2-period session introduces.

**Only reachable pairs are materialised.** `y[s,t]` is created only for slots some valid start can
actually cover. Pairs no start can reach are constant 0 and are omitted rather than posted — this is
the pruning `docs/constraint-model.md` refers to when it calls 6,104 an upper bound and never an
estimate. Measured effective count is in `docs/status.md`.

**Built on demand, not on every solve.** `build_occupancy()` lives in `solver/occupancy.py` and is
called only when something needs the accounting. The Phase 2 feasibility solve does **not** call it, so
it does not pay for variables no constraint reads. This matters: that solve is measured at ~3 s and
must not regress for an objective that does not exist yet.

#### The auxiliary-variable question — **CLOSED 2026-07-30, measured**

The original finding observed that per-group-per-day first/last occupied period and reified gap
indicators were absent from the model-size table, so the stated size was an underestimate. It could not
be closed while no soft criterion had a formula. **C-4 now supplies them, so the count is measured
rather than estimated:**

| Weights | Objective auxiliaries added |
|---|---|
| Catalogue defaults (S2–S7 non-zero, S10 = 0) | **5,249** |
| S3 alone | 2,376 |
| S4 alone | 1,628 |
| S2 alone | 1,620 |
| S7 alone | 984 |
| S5 alone | 218 |
| S6 alone | 7 |
| S10 alone | 0 — reuses `y` directly, needs no new variable |
| All weights zero | **0** |

The catalogue total (5,249) is below the sum of the individual figures (6,833) because S3 and S4 share
one per-teacher-day occupancy layer, built once when either carries weight.

Two facts worth carrying beyond the numbers. **Auxiliaries are built only for criteria carrying
weight**, so a profile that switches a criterion off pays nothing for it. And **`build_occupancy` is
gated on the same condition** (`has_active_criteria`, `solver/engine.py`): an all-zero-weight profile
skips the 10,048 accounting variables entirely and is genuinely equivalent to the Phase 2 feasibility
solve, rather than merely posting no objective while still paying for the accounting — which is what
an earlier revision of this phase did.

The original planning estimates (~612 integers for first/last per group-day, ~1,530 booleans for a gap
indicator per group-day-period) are superseded. They were the right order of magnitude but assumed a
gap-indicator encoding; the implemented one derives idle from first/last and an occupancy count
instead.

**Resolved:** the channelling, and now the auxiliaries. **Nothing of C-7 remains open.**

### C-9 — Four requirements have no detailed specification · **NARROWED 2026-08-10 → two remain: FR-10 and FR-18**

⚠️ **Read the NARROWED subsection at the foot of this entry before acting on anything above it.** The
heading states the original scope; **FR-6 and FR-17 have since been shown to have supervisor-written
criteria** in SRS §6.7 and §8.4, located through SRS Table 36. FR-17 is `✓`. The analysis in between is
kept because it is what the project believed for five days and because its 2026-08-05 correction is
cited elsewhere — the same treatment C-13 and C-15 get.

**FR-6, FR-10, FR-17, FR-18** appear in the summary tables but have no input/processing/output row in
SRS §3.2. **FR-10 is missing entirely from the SRS Table 36 traceability matrix.**

Note: SRS Table 36 is nonetheless the only reliable place to reconstruct the FR numbering — the summary
tables in both CdC and SRS are damaged by cell-offset in the PDF layout, so codes and statements do not
line up when read literally.

⚠️ **Correction, 2026-08-05: this entry claimed to block "Phase 6 acceptance", and that claim does not
survive checking.** It was checked against the two documents that actually define the acceptance work,
rather than against the assertion:

- The **nine acceptance criteria** in [`docs/status.md`](status.md) name FR-6, FR-10, FR-17 and FR-18
  **nowhere**. Every one of the nine maps to FR-2, 3, 5, 8, 9, 11, 12, 13, 15 or 19.
- The **acceptance-test table** in [`docs/testing-strategy.md`](testing-strategy.md) §4 lists thirteen
  rows and **contains none of the four** either.

So the four requirements without a detailed specification are also the four with no acceptance test to
write, and C-9 blocks neither Phase 6's completion criteria nor its test suite. **What it still blocks
is calling FR-6, FR-10, FR-17 or FR-18 `✓`**, since a requirement cannot be verified against a
criterion nobody wrote.

This is the same shape as the error corrected in `docs/status.md`'s "Next, in order" item 3: **a
plausible blocker nobody tried to falsify.** It cost nothing here because it was caught before the
schedule was built on it.

⚠️ **One quarter of it moved on 2026-08-05 and C-9 is still open.** C-14's resolution reworded
`docs/scoring-and-explanation.md` §Dominance, which *is* the statement FR-17 is verified against, so
FR-17 now has a testable criterion and an acceptance test. That does **not** resolve C-9: the missing
input/processing/output rows in SRS §3.2 for FR-6, FR-10 and FR-18 are untouched, and FR-17's SRS row
is still absent — its criterion now comes from this project's own design document instead.

#### NARROWED 2026-08-10 → FR-17 leaves C-9 entirely; FR-6 leaves it too; **FR-10 and FR-18 remain**

> **Project decision — determined from repository evidence because supervisor clarification was
> unavailable.** The supervisor was asked and did not answer, and the project owner instructed that the
> question be settled from the material to hand. Nothing below is attributed to the supervisor that the
> supervisor did not write; every criterion adopted is **quoted** from a specification document in
> `docs/specifications/`, and the sentence saying which requirement it governs is quoted too.

**The premise of this entry was too strong, and one search falsified it.** C-9 says these four
requirements have no detailed specification. What is true is narrower: **they have no §3.2
input/processing/output row.** They were never checked against **SRS Table 36**, which this very entry
calls "the only reliable place to reconstruct the FR numbering" — and Table 36 carries a row for three
of the four, naming the SRS section that specifies each:

| FR | Table 36 → | "Element which implements it" | Does that section state testable behaviour? |
|---|---|---|---|
| **FR-6** | **§6.7** | "Order by decreasing score" | ✅ **Yes, verbatim** — see below |
| **FR-17** | **§6.7 and §8.4** | "Test of dominance" | ✅ **Yes, twice** — §6.7 states it and §8.4 Table 34 states how it is verified |
| **FR-18** | §4.1 and §5.1 | "Views by classroom and by laboratory" | ⚠️ **Partly** — §4.1 names the *filter*, never the *occupancy figure* |
| **FR-10** | **absent** | — | ⚠️ **Partly** — the CdC names both halves; nothing states what "done" is |

**FR-6 — leaves C-9. Criterion found, quoted, supervisor-written.** SRS §6.7:

> "The candidates are ordered by decreasing score. Equal scores are separated by the criteria taken in
> the order of their weights."

Two sentences, both testable, both falsifiable, and Table 36 points FR-6 at exactly this section. This
is *stronger* evidence than the §3.2 rows Phase 10 closed FR-4, FR-7, FR-14 and FR-16 against, because
Table 36 names the section explicitly. ⚠️ **FR-6 is unblocked, not finished** — `DefaultRanker.rank()`
implements both sentences and `GET /runs/{id}/candidates` returns that order, but **no acceptance file
exists**. It is ordinary scheduled work now, not a blocked requirement.

**FR-17 — leaves C-9 completely, and is `✓` as of 2026-08-10.** Two supervisor-written statements, and
**neither contains the "recommended candidate" clause** that made this look unspecifiable:

> **SRS §6.7:** "A candidate which another candidate improves on every criterion is signalled, because
> that situation shows that the weights conceal a compromise instead of expressing one, and the person
> in charge must then decide with full knowledge of it."
>
> **SRS §8.4, Table 34 — "Properties tested on the analysis layer":**
> *Detection of dominance* — "A candidate improved on every criterion is signalled."

⚠️ **This changes what C-14's decision (ii) was.** "Signal a dominated candidate anywhere in the
portfolio" is **not a project invention** — it is what the SRS's own detailed sections already say. The
"top-ranked candidate" clause exists only in the **summary** tables (SRS Table 3, CdC Table 3), and
this entry already records those as damaged by cell-offset with Table 36 the reliable source. C-14 (ii)
restored the specification's own detailed wording over a damaged summary row.

⚠️ **C-14's decision (i) — strict `>` → Pareto — remains a project-owner amendment, and it does not
weaken the tick.** §6.7 and §8.4 both say "improved on every criterion", which is the strict reading.
Pareto is **strictly wider**: anything the supervisor's literal wording requires to be signalled
(`>` on every criterion) is also `≥` on every criterion and `>` on at least one, so the implementation
satisfies §8.4 **literally**, and additionally catches the case the literal wording misses. **No
goalpost moved toward the implementation** — which is the exact opposite of FR-8, where the criterion
was narrowed to accommodate a limitation and promotion was therefore refused.

**FR-10 and FR-18 — C-9 continues to hold their ticks, and the reason has changed.** It is no longer
"nobody specified them". Both requirements are named in supervisor-written scope statements:

> **CdC §3, "For the students":** "Printing and export of the displayed view."
> **CdC, module list:** "Display module: views by teacher, by group, by classroom, by laboratory and by
> examination, **printing and export**."
> **SRS §4.1:** "Timetable view: weekly grid filtered by teacher, group, classroom or laboratory, **with
> printing of the displayed view**."
> **CdC §1, needs:** "Any authorised user to consult **the occupancy of a classroom or of a
> laboratory**."

What is missing is an **acceptance standard**, and for FR-18 something sharper: **no document anywhere
defines what the occupancy figure IS.** Occupied periods over open periods? Over the whole week? The
two-period-window figure? That is not a pedantic gap — **C-13 is the record of this project losing three
sessions to reading the period figure when the window figure was the one that bound**, and
`features/timetable/model.ts` already carries a warning that the figure it displays is the reassuring
one. Choosing the denominator here would be inventing the requirement, and it is the one place where
inventing it could actively mislead.

**The strongest project interpretation, adopted so the next session does not re-derive it:**

| FR | Criterion adopted — **project decision, from the quoted text above** | Testable? |
|---|---|---|
| **FR-10** | *A timetable view can be printed or exported, and what leaves the screen is **the displayed view**.* | ✅ Yes, and Phase 9's closing audit already produced this evidence by hand: rendered grid cells and exported rows compared as sets, 6 = 6, identical |
| **FR-18** | *An authorised user can consult, for **each** classroom and **each** laboratory, how heavily it is used on a given candidate.* | ⚠️ Partly — reachability and completeness are testable; **the quantity is not fixed**, and a test asserting one formula would invent the requirement |

⚠️ **Neither is ticked, and adopting a criterion is not the same as meeting one.** Both stay `WIP`, for
the ordinary reason: no acceptance file exists for either, and `OccupancyView.tsx` has **no test of any
kind**. A future `✓` must cite both the quoted source and this project-decision label, so the tick stays
reversible if the supervisor ever answers differently.

**Blocks after this narrowing:** the `✓` of **FR-10 and FR-18** — and, for FR-18, the *definition* of
its central figure, which is the part no repository evidence supplies. **No longer blocks:** FR-6 (a
criterion exists; an acceptance test does not) or FR-17 (closed). **Owner:** technical lead; the
supervisor is still the only source for FR-18's quantity and for a Table 35 row.

### C-11 — The generated instance · **RESOLVED — it exists and it verifies**

**This finding was wrong, and is corrected here rather than deleted.** The scaffold originally recorded
the instance as missing and instructed the next session to write a generator reproducing it. It was
supplied on 2026-07-29 and is now in `data/instance/` — 13 CSVs, 36 KB.

**Every documented figure was re-measured and matches.** Not approximately — exactly. Figures below are
**as of 2026-08-01**, re-run with `scripts/verify-instance.ps1`.

⚠️ **Two rows moved on 2026-07-30 and this table did not follow until 2026-08-01** — the room mix and
verification 2, the exact two the C-13 repair touched. The "Documented" column now carries the errata's
corrected figures (see ERRATA, CdC Tables 10 and 11), not the superseded PDF values. **A verification
table is the one place a stale number does the most damage**, because its whole purpose is to show the
documentation is checked rather than asserted; for a day it certified a room mix the instance no longer
had.

| Claim | Documented | Measured |
|---|---|---|
| Sessions CM / TD / TP | 32 / 82 / 104 | ✅ 32 / 82 / 104 |
| Durations 1-period / 2-period | 114 / 104 | ✅ 114 / 104 |
| Groups PROMO / TD / TP | 6 / 15 / 30 | ✅ 6 / 15 / 30 |
| Rooms Amphi / Salle / Lab_Info / Lab_Sciences | 2 / 7 / 8 / 3 (errata; total 20) | ✅ 2 / 7 / 8 / 3 |
| Teachers by rank | 7 / 11 / 13 / 13 | ✅ 7 / 11 / 13 / 13 |
| Students · courses · slots open | 425 · 32 · 28 of 30 | ✅ 425 · 32 · 28 of 30 |
| Holidays, of which lunar | 18, 10 | ✅ 18, 10 |
| Availability rows · teachers covered | 157 · 41 of 44 | ✅ 157 · 41, all `SYNTHETIC` |
| Catalogue hard / soft · weight sum | 12 / 7 · 0.90 | ✅ 12 / 7 · 0.90 |
| **Verification 1** sessions without a room | 0 | ✅ **0** |
| **Verification 2** periods, Amphi / Salle / Lab_Info / Lab_Sciences | 57% / 42% / **71%** / 57% (errata) | ✅ **57.1 / 41.8 / 71.4 / 57.1** |
| **Verification 2** two-period windows, Lab_Info / Lab_Sciences | **91%** / 73% — ⚠️ **the bound that binds** | ✅ **90.9 (80/88) / 72.7 (24/33)** |
| **Verification 3** over rank limit · heaviest | 0 · 12 periods (18 h) | ✅ **0 · 12 / 18** |
| **Verification 4** in difficulty · smallest margin | 0 · 11 free slots | ✅ **0 · 11** |
| **Verification 5** invalid refs · students matching | 0 · 425 | ✅ **0 · 425** |

The documentation's factual claims are therefore **verified, not merely asserted** — which is the
condition the whole "generated data is acceptable if verified" argument rests on (ADR-008).

**What remained of C-11 is now delivered.** ✅ **The generator landed 2026-08-05** (Phase 6 M5) — `data/generator/generate_instance.py`, passing `verify_instance.py` on every documented figure, and its output solves 218/218 in 5.1 s. ⚠️ It reproduces the documented **figures**, not the committed **rows**, and refuses to overwrite `data/instance/`; the reasoning is in `docs/status.md` item 10. The superseded text read: "the *generator* is still a stated deliverable (PPM §10) and does not exist."
That is a documentation and reproducibility task, **not a blocker** — the instance it would produce is
already here and checked. Re-run the checks any time with `scripts/verify-instance.ps1`.

⚠️ **It is now scheduled**, as item 9 of `docs/status.md`'s "Next, in order", latest sensible point
Phase 6. Until 2026-07-31 it was stated here, in `docs/data-and-instance.md` and in ADR-008, and
scheduled nowhere — an owed deliverable living inside a section headed **RESOLVED**, which is a good
way to lose one. **A section marked resolved may still carry work; say where that work is tracked.**

### C-12 — S5 carries weight 0.20 and has no input data · **RESOLVED 2026-07-30 → option (b), a labeled proxy**

`teacher_availability.csv` has a boolean `is_available`, and **all 157 rows are 0** — they are
unavailability declarations, exactly as documented. There is **no representation of a preferred
window** anywhere in the instance schema, even though `AvailabilityState.PREFERRED` already exists in
`domain/enums.py`, anticipating it.

Three ways this could go:

- **(a)** Add a third state (or a `preference` column) to `teacher_availability.csv` and have the
  generator produce some. Closest to the specification; changes the instance, so the documented row
  count of 157 must be restated. Requires touching `data/instance/` and `instance/loader.py`.
- **(b)** Define S5 against something already present. Keeps the instance untouched.
- **(c)** Accept that S5 measures 0 on this instance. **Cheapest and most dangerous** — see below.

**Decision: (b), with an edge-of-day formulation, not the "distance from unavailable block" reading
originally sketched.** Two things drove this:

1. **(a) is objectively the better long-term fix** — it is what "preferred window" actually means, and
   the domain model already anticipated it — **but it is out of scope for the pass that resolved this**,
   which was restricted to `analysis/`, `solver/objective.py`, `recommendations/`, `tests/property/`.
   Nothing in that scope may touch `data/instance/` or the loader. This is a scope-driven choice, not a
   merit-driven one, and (a) should be revisited whenever instance/loader work is back in scope (Phase 4
   already touches the availability grid).
2. **The obvious version of (b) — generalise a teacher's declared unavailability across the week (if
   unavailable at period-of-day `p` on any day, treat `p` as generally disliked) — was tested against
   the actual CSV and degenerates.** Unavailability is spread across almost every period index for most
   teachers: 14 of 41 teachers with any declared unavailability already cover all 5 period indices, so
   that reading would flag nearly every session those teachers give, regardless of where it is placed —
   no signal that varies with the candidate.

   The version adopted instead does vary with placement and needs no per-teacher data at all: **treat
   the first and last period of the day as generally undesirable** — a standard convention in
   university timetabling, independent of any one teacher's declarations — and count sessions placed
   there:

   ```
   v_S5(k) = |{ sessions s : one of s's occupied periods has period_index in {0, P-1} }|
   min_S5 = 0
   max_S5 = |instance.sessions|  (218 on the reference instance — loose but valid and instance-constant)
   ```

   **This is a labeled stand-in for real preference data, not a definition of teacher preference.** It
   is recorded as such here so nobody mistakes it for "the" meaning of S5 later. Replace it with (a)
   once a genuine preferred-window column exists.

⚠️ **Why (c) was rejected.** The three weight profiles are balanced, student-favouring (raises S2) and
**teacher-favouring (raises S3 *and* S5)**. Had S5 stayed identically zero, the teacher-favouring
profile would have differed from the others by S3 alone — weaker than intended, risking **two
candidates converging**, which is precisely the **C-5** failure mode (duplicates removed, fewer than
three distinct candidates, acceptance test fails) for a reason nobody would think to look for. The
adopted formula gives S5 genuine, candidate-dependent variation, which lowers that risk without
resolving C-5 itself — C-5 is a separate, still-open conflict in the specification's own wording.

**Blocks:** Phase 3 (scoring) — now unblocked. **Owner:** technical lead, decided 2026-07-30.

#### The availability grid's own decision · **RESOLVED 2026-08-01 → two states, (a) not revisited in Phase 4**

C-12 left one thing open for whoever built the grid: two states against the current schema, or three
once a real preferred-window column exists. **Decision: two states — available / unavailable.**

**The reason is that the schema has no third state to record.** `teacher_availability.csv` carries a
boolean and all 157 rows are unavailability declarations. A grid offering a *Preferred* cell would be
collecting an answer with nowhere to put it, and the honest alternatives are both worse than waiting:
drop the answer on save, or change the instance mid-phase.

**What this is not.** It is **not** a judgement that two states are right. C-12 records option (a) — a
genuine preferred-window column — as the objectively better long-term fix, rejected on scope rather
than merit, and that stands. This decision only says Phase 4 is not where the instance changes.

**What it costs, stated plainly.** S5 keeps its labelled proxy (edge-of-day placement) rather than
measuring real preference, so **"teacher preference" continues to mean something other than what a
teacher said** — and it carries weight 0.20, the second highest. That is recorded in C-12 above and is
unchanged by this decision.

**What it does not cost.** `AvailabilityState` already has three members and the API's
`AvailabilityCellIn` already accepts `PREFERRED`, deliberately, so adopting (a) later changes the
instance, the loader and the grid's cell component — **not the wire format**. Revisiting it is a data
decision, not an API migration.

**Revisit when:** instance and loader work is back in scope, or the supervisor asks for real preference
data. Nothing in Phase 4 or 5 depends on it. **Owner:** technical lead, decided 2026-08-01.

---

### C-13 — "Room-assignment symmetry makes H1–H12 hard to solve" · **RESOLVED — the diagnosis was wrong; the instance was infeasible**

**Resolution, 2026-07-30.** There was never a search-performance problem. The reference instance as
originally generated had **no solution at all**, and every `UNKNOWN` recorded below was CP-SAT failing
to *prove* an infeasibility whose proof its propagators cannot construct. The model — H1, H3, H7, H12
and the domain-pruned rest — was correct throughout.

**The argument, which needs no solver.** A two-period session needs its two periods consecutive and
inside one day: H8 forbids crossing a day boundary, H9 forbids closed slots. The week's open slots are
therefore not a flat pool of periods but six contiguous runs — five of length 5 (Mon–Fri) and one of
length 3 (Saturday, afternoon closed). A run of length `L` offers one room only `floor(L / 2)` disjoint
two-period windows, so **one room offers 5×2 + 1 = 11 two-period windows a week**, not 28 periods'
worth. Every laboratory session in this instance spans two periods:

| Room type | Two-period sessions | Rooms | Windows offered | Verdict |
|---|---|---|---|---|
| `Lab_Info` | 80 | 6 | 6 × 11 = **66** | short by **14** |
| `Lab_Sciences` | 24 | 2 | 2 × 11 = **22** | short by **2** |

Pigeonhole. No assignment exists, and none of H1, H12, teacher availability or room symmetry is
involved in the argument.

**Confirmed three ways, independently:**

1. Hand arithmetic, above.
2. CP-SAT asked to *maximise* the number of placeable sessions (optional intervals, cumulative bound
   only) returned exactly **66 of 80** and **22 of 24** — the arithmetic ceiling, reached from below.
3. The same feasibility question expressed as **counting** rather than as intervals — assign each
   two-period session to a day, cap each day at `rooms × Σ floor(L/2)` — returns `INFEASIBLE` in
   **0.088 s with zero conflicts**, at presolve. Written as intervals, the identical question runs for
   480 s and returns `UNKNOWN`.

**Why CP-SAT could not see it.** `AddCumulative` reasons about *area*: 160 period-units of demand
against 6 rooms × 28 open periods = 168 available, which fits. The obstruction is not area but
**structure** — a 5-period day cannot be tiled by 2-period sessions, so one period per room-day is
unusable and the true capacity is 132 period-units, i.e. the instance was **121 % subscribed, not
95.2 %**. No amount of budget, tuning, warm-starting or reformulation can find a solution that does
not exist, which is exactly why all three techniques below "failed" identically.

**Previous conclusions this disproves:**

- ❌ "Full interchangeability at near-full capacity is the textbook hard case, and that is what this
  is." The interchangeability was real but irrelevant. With capacity repaired and *nothing else
  changed* — same encoding, same symmetric fully-interchangeable rooms, same parameters — the model
  solves in **2.8–3.3 s** (deterministic time 0.13–0.21), reproducibly across seven seeds.
- ❌ "No constraint subset has ever reproduced an instant `INFEASIBLE`, which is evidence of hardness
  rather than a correctness bug." The inference was wrong in both directions: an instant `INFEASIBLE`
  is evidence of a *too-tight model*, but its absence is not evidence of a *correct instance*. The
  sub-0.1 s `INFEASIBLE` was there the whole time — it appears the moment the question is posed as
  counting instead of as intervals.
- ❌ "The greedy warm-start plateaus at 192/218 because the instance sits very close to its capacity
  limit." **At most 202 of 218 sessions can be placed at all** (218 − 14 − 2), so the greedy was within
  10 of an upper bound it could never have passed — it was reporting the infeasibility, not struggling
  with it. (202 is an upper bound; whether it is attainable was not tested, and does not matter to the
  argument.)
- ✅ Confirmed: pure time scheduling (H1 + H12, no rooms) is fast. Also confirmed: H1–H12 are
  correctly modelled — now positively, by solving and independently re-verifying every rule, rather
  than by the absence of a bad signal.

**The repair, applied 2026-07-30.** Three classrooms were re-typed as laboratories — `Salle` 10 → 7,
`Lab_Info` 6 → 8, `Lab_Sciences` 2 → 3 — which leaves the **total room count at 20** and the calendar,
the slot grid and the 32 / 82 / 104 session split untouched. `Salle` was 29.3 % occupied while the
laboratories were over-subscribed, so this corrects the actual error rather than adding capacity around
it. The instance stays tight where the project wants it tight: `Lab_Info` is at **90.9 % of its
two-period windows**, still the binding resource, now measured against a denominator that means
something.

**Consequence for the pre-analysis — this is the part worth carrying forward.** Verification 2 computed
`capacity = rooms × open_slots` and compared period totals. That bound is necessary but **not
sufficient**, and it passed a genuinely infeasible instance while reporting a comfortable "95.2 %". The
check whose entire stated purpose is to tell *"this instance has no solution"* apart from *"the model
has a bug"* returned the wrong answer, and three sessions of work went looking for a bug that did not
exist. `data/verification/verify_instance.py` now applies **both** bounds: the period-area bound as
before, and a contiguity bound per duration — `sessions of duration d ≤ rooms × Σ floor(L / d)` — which
fires on the original mix (short by 14 and by 2) and passes on the repaired one. **The in-application
port of the five checks (FR-12) must carry the contiguity bound too**; shipping the area bound alone
would reintroduce exactly this failure inside the product.

---

**The superseded analysis** - the original C-13 diagnosis, its measurement table and the three
techniques tried against it - is archived in [`docs/history.md`](history.md). It is wrong, and kept
only because the measurements are real and the reasoning error is instructive.


⚠️ **One leftover of the superseded analysis was itself wrong, and is corrected here.** This section
used to end by carrying forward, "on its own merits", the claim that `max_deterministic_time` did not
tightly bound parallel search — 60 requested against 247.98 consumed. **It binds exactly, per worker.**
`CpSolver.deterministic_time` reports the *sum across workers*, so a 16-core machine legitimately
reports ~11× the budget and nothing was overshooting. Measured 2026-07-30 and recorded in C-2 and
ADR-011; `tests/integration/test_reproducibility.py` pins the ratio so the misreading cannot return.

That the erroneous figure survived *twice* — once inside a wrong diagnosis, then again as the one piece
of it judged sound enough to keep — is the part worth remembering. Salvaging a measurement from a
refuted analysis is exactly when it is least likely to be re-derived.

---

### C-19 — How a locked session's target reaches the solver · **RESOLVED 2026-08-06 → `SolverInput` carries `Placement`s**

H10 is registered and **dormant**: `solver/variables.py` refuses to build if `SolverInput.locked_sessions`
is non-empty, because that field is a `frozenset[SessionId]` and a session id does not say *where* the
session is locked. `recommendations/translator.py` already reads the target correctly out of the
candidate (`LockedPlacement(session, slot, room)`); what is missing is a way to carry it downstream.
Recorded as item 9 of `docs/status.md`'s "Next, in order", and it is FR-23's prerequisite: `lock_session`
is one of the three catalogue actions, so regeneration cannot be built while one third of the catalogue
cannot reach the solver.

**Decision: replace `locked_sessions: frozenset[SessionId]` with `locked_placements: frozenset[Placement]`.**

**Why `Placement` rather than a new type.** A lock *is* a placement the solver must reproduce.
`domain.entities.Placement` is already `(session, slot, room)`, already `frozen=True, slots=True` and
therefore hashable, and already lives in `domain`, which `solver` may import. A new
`LockedSession(session, slot, room)` would be `Placement` under a second name, and two names for one
shape is how a mapping layer starts.

**Why replace rather than add a field.** `locked_sessions` has never been usable — every code path that
receives it non-empty raises. Keeping it beside a usable field means a caller can still pick the one
that cannot work, and the failure would arrive at solve time. Replacing it turns that mistake into a
type error at the call site.

**Why `recommendations.LockedPlacement` is not reused directly.** `solver` may not import
`recommendations` (`docs/architecture.md`'s module map gives the solver `domain` only). The two types
stay separate and `services/` maps one onto the other — that mapping is the layer boundary doing its
job, not duplication to remove. The same reasoning already produced two implementations of the seven
soft criteria (C-4).

**What it costs, stated plainly.** `SolverInput` is a **Phase 2 contract** and this changes it. Three
call sites move (`services/portfolio.py`, `solver/variables.py`, `solver/constraints/domain_pruned.py`),
and every one of them is on the path every ordinary run takes — so the change is verified by the whole
existing solver suite rather than only by new tests. H10 stops being dormant, which removes one of the
two reasons `docs/requirements-traceability.md` gives for FR-3 not being `✓`.

**Blocked:** nothing. FR-23's prerequisite is unblocked. **Resolved by:** project owner, 2026-08-06.

### C-20 — Where a regeneration assembles its run, and what links it to the original · **RESOLVED 2026-08-06 → `services/regeneration.py`, and the new run records its origin**

`recommendations/translator.py` returns a `RunOverride` — plain domain data — rather than a
`SolverInput`, and its module docstring records why: the `translate(action, run, candidate)` signature
receives a `Run` (no instance, no profile weights) and a `Candidate` (a profile *name*, not its weights),
so **no layer below `services` has the context a `SolverInput` needs.** That gap is recorded as a live
risk in `docs/status.md` and was left for "a later layer (`services/`, Phase 4–5)" that was never
written. FR-23 is where it comes due.

**Decision, in five clauses.**

**(i) The assembly lives in `services/regeneration.py`.** `services` is the only layer permitted to hold
both the run store and the solver — `services/portfolio.py` is the precedent and the module the
architecture document names for exactly this. Nothing in `recommendations/` changes.

**(ii) The instance is the one the application serves.** `Run` carries no instance reference, so a
regeneration reloads the single instance this deployment has. ⚠️ **This is correct only while there is
one instance, and that is a limit rather than an assumption**: the day a second exists, `Run` must gain
the reference and this clause must be reopened. Recorded here rather than discovered later.

**(iii) The new run records `origin_run` and the recommendation that produced it.** `RecommendationRecord`
already carries `resulting_candidate`; it is set once the regenerated run produces one. **Invariant 6 is
untouched** — nothing about the origin run or its candidates is edited, and the regenerated timetable is
a new candidate under a new run, which is what invariant 6 requires rather than something it merely
permits.

**(iv) Overrides compose.** A regenerated run carries the origin run's overrides *plus* the new one.
Without this, accepting a second recommendation silently discards the first, and a user who locked a
session would watch that lock disappear with nothing on screen to explain it. Cost, stated: the overrides
become part of the run record, so `RunRecord` gains a field and **both** store implementations plus
`tests/integration/test_store_contract.py` must carry it — that suite exists precisely because two
implementations of one contract drift.

**(v) A `weight_delta` replaces one entry of the run's own recorded vector, not of the catalogue.**
`RunRecord.weights` already records the weights in force and its docstring already states why one vector
must price every candidate. Reading the delta against the catalogue instead would silently discard any
earlier delta, which is clause (iv) again in a different disguise.

**Blocked:** nothing. **Resolved by:** project owner, 2026-08-06.

### C-21 — Whether any test may call a live language model · **RESOLVED 2026-08-06 → no, at any marker**

The assistant is an adapter around an external API. Nothing in the repository says whether the test
suite is ever allowed to reach one, and the answer governs how FR-22, FR-24 and FR-25 are verified.

**Decision: no test calls a live provider — not one, at any marker.** The adapter is exercised through a
scripted fake.

**Why.** Four reasons, and the first is the project's own standing rule: a language model's output is
**not fixed by a seed**, so such a test reports the machine and the day rather than the software — the
same objection ADR-011 makes to a wall-clock bound, and this project already treats an irreproducible
test as worse than none. It would need a secret, and `assistant_api_key` must never be committed
(`secret_key`'s published default is the standing lesson). It would fail with no network. And it would
cost money on every `run-checks.ps1`, which a person runs by hand, several times a phase.

**What replaces it, and why it is the better test.** The thing under test is the grounding check, and
that check is pure: `numbers(answer) ⊆ numbers(context)`. A fake adapter can be made to return a
**fabricated** figure on demand; a real model can only be *hoped* to fabricate one on the day the suite
runs. The failure mode the requirement exists to catch is therefore reachable by the fake and not
reliably reachable by the real thing.

⚠️ **What this does NOT establish, stated plainly:** that any particular provider works. It establishes
the application's behaviour *around* a provider — the context it sends, the check it applies, and what
it displays when the check fails. **Do not read a green suite as "the assistant was tested against a
language model."** A first live call is a deployment step, and it belongs in `docs/demonstration.md`,
not in `pytest`.

**One property worth naming, because it is a gift rather than a compromise.** `assistant_enabled`
defaults to **False**, so **degraded mode is the default configuration.** Invariant 5 — everything works
with the assistant switched off — is therefore exercised by every one of the suite's existing tests
rather than by one special test, and the FR-22/FR-25 acceptance criterion needs no provider, no key and
no network to verify.

**Blocked:** nothing. **Resolved by:** project owner, 2026-08-06.

### Recorded, not decided — FR-25 is Phase 7's release valve

Not a new question. `PPM §8.3` and `docs/status.md`'s "Order of scope reduction" already fix the first
cut: **the assistant's *report* is abandoned, explanations and answers kept.** ADR-010 makes the same
point from the other side, FR-25 being *Expected* where FR-22/23/24 are *Necessary*.

Written here so that if Phase 7 runs late the reduction is applied as the decision it already is, rather
than re-argued under pressure — which is the whole reason the order was decided in advance.

---

## Verification of the reference archives

**Confirmed the documented findings and sharpened two of them:**

- Kaggle's two invalid files are worse than "contains errors": **44% of timeslot rows have an end time
  at or before their start time**, and **83% of room+slot pairs are double-booked**. The archive's own
  note claims *"Clean CSVs"* — a direct vindication of verifying files rather than documentation.
- ⚠️ **New finding, not in the PDFs: `students.csv` carries names, emails, phone numbers and postal
  addresses** across 3,000 rows. This gives ADR-008's "rooms and enrolments only" a second
  justification beyond data quality, and it interacts with the data-minimisation requirement — no such
  field may ever reach the assistant's context payload.

### R-6 — The examination model breaks the `room[s]` schema

SRS §6.8 calls the examination model "the same construction with different variables". It is not: **an
examination may occupy several rooms at once**, so room assignment becomes a boolean matrix with a
capacity sum, not a single integer.

**Do not bake a single-room abstraction into shared solver code.** Increment 2, but the constraint on
the code structure applies now.

---

## ERRATA

Corrections to send in one pass rather than re-argue.

| Document | Current text | Should read |
|---|---|---|
| **SRS §2.3** | "Optional external service : interface towards a language model, **used only in the second increment** and deactivable by configuration." | "Optional external service: interface towards a language model, **part of the first increment**, deactivable by configuration." |
| **SRS §1.2** | "…and formulation of an explanation in ordinary language, **which constitute the second increment**." | "…**Generation of the timetable of an examination session and adjustment of the weights, which constitute the second increment.**" (the assistant is increment 1) |
| **CdC §4.5.1** | "…the weighted sum of **section 5.6**" | CdC §5 ends at 5.5. Should reference **SRS §6.7** / **PPM §4.6** |
| **CdC §4.1** | Lists both "AI assistant service" and "AI assistant module" | One entry. Same duplication in CdC §1.2, where "Assist in ordinary language" appears twice |
| **PPM §8.3** | Reduction order numbered **4–9** | **1–6.** "Item 4" currently has no referent |
| **CdC/SRS §4.5.2** | Grounding steps numbered **9–12** | **1–4** |
| **SRS Table 36** | FR-10 absent | Add: FR-10 → §4.1 → "Print or export a timetable view" |
| **CdC Table 10** (room mix) | Amphi 2 · Salle 10 · Lab_Info 6 · Lab_Sciences 2 | **Amphi 2 · Salle 7 · Lab_Info 8 · Lab_Sciences 3.** Total unchanged at 20. The original mix made the instance infeasible — see C-13 |
| **CdC Table 11** (verification 2) | "computer laboratories **95%**" | "computer laboratories **91% of two-period windows** (71% of periods)". The period figure is necessary but not sufficient and passed an instance with no solution — see C-13 |
| **FR-17's statement** (CdC Table 3 · SRS Table 36) | "Signal a **recommended** candidate that another dominates" | "Signal a candidate that another dominates, **wherever it appears in the portfolio**." A dominated candidate cannot outscore its dominator under a linear weighted sum with non-negative weights, so it can never be the recommended one — the stated state is unreachable. See C-14 |
| **FR-16's statement** (CdC Table 3 · SRS Table 36) | "…and **a dominated top candidate is signalled alongside**" | Delete the clause. It describes the same unreachable state; the portfolio-wide signal in FR-17 is what carries the information. See C-14 |
| **The definition of dominance** (CdC/SRS, wherever "improves on every criterion" appears) | "a candidate that another **improves on every** criterion is dominated" | "a candidate that another is **at least as good on every criterion and strictly better on at least one** is dominated" — the standard Pareto rule. The strict reading is silent precisely when a candidate is beaten on every weighted criterion and tied on the unweighted S10. See C-14 |

⚠️ **The last three rows name the requirement statements, not a verified section number.** FR-16's and
FR-17's wording is quoted from `docs/requirements-traceability.md`, which reconstructs it from SRS
Table 36 because the CdC and SRS summary tables are damaged by cell-offset (see C-9). **Locate the
sentences in the PDFs before sending these corrections**; the replacement wording is what matters and
is independent of where they sit.

### Not errors — recorded so they are not re-investigated

- **CdC Table 4 and Table 5 appear scrambled** when the PDF text is extracted: the code, statement and
  XHSTT-reference columns are offset by one row because of multi-line cells. Read with the offset
  corrected, they **agree exactly** with SRS Tables 27 and 28. There is no H-code or weight
  contradiction between the documents. The authority for both is `constraint_catalogue.csv`.
- **Soft codes skip S1, S8 and S9.** 12 hard + 7 soft = 19 matches the stated catalogue size, so the
  numbering is internally consistent. The gaps are unexplained — presumably criteria removed during
  revision. **S1, S8 and S9 are retired and must never be reused**, since codes are stable identifiers
  in the catalogue, the conflict report and `weight_delta` parameters.
- **X1–X4 and SX1 are not among the 19.** The catalogue covers the weekly model only.
- **The target semester is already past** (second semester 2025–2026; Ramadan window 18 Feb – 19 Mar
  2026). Correct for a demonstration instance. **Do not "fix" the dates.**
