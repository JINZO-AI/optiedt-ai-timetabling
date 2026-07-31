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

**Three.** Everything else on this page is resolved and kept for its reasoning.

| # | Still open | Blocks | Owner |
|---|---|---|---|
| **C-5** | "At least three candidates" can fail when duplicates are removed | Phase 6 acceptance | Lead + supervisor |
| **C-9** | FR-6, FR-10, FR-17, FR-18 have no detailed specification | Phase 6 acceptance | Technical lead |
| **C-14** | Dominance uses the strict reading; S10's zero weight makes ties common. **Also: the "dominated *top* candidate" signal both documents require is provably unreachable** | Phase 4 comparison screen | Technical lead |

Resolved: **C-1, C-2, C-3** (ADRs 010, 011, 009) · **C-6, C-7, C-13** (2026-07-30, implemented) ·
**C-8, C-11** · **C-4, C-12** (2026-07-30, implemented). The sections below keep their full reasoning;
headings say which is which.

⚠️ C-4 and C-12 **were** one bug waiting to happen, before they were resolved together on 2026-07-30:
had S5 measured identically zero, the teacher-favouring profile would have differed from the others by
S3 alone, risking two candidates converging under duplicate removal and failing the three-candidate
acceptance test (C-5). **C-5 itself remains open** — S5 no longer being identically zero lowers the
chance of hitting it on the reference instance, but does not resolve the specification's own conflict
between "duplicates removed" and "at least three candidates".

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

## RAISED AFTER THE FIRST READING — four still open, four since resolved

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

### C-14 — Dominance uses the strict reading, and S10's zero weight makes that bite · **NEW, OPEN (low urgency)**

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

### C-5 — "At least three candidates" can fail when duplicates are removed

SRS Table 29 says "at most 3, **duplicates removed**". CdC §11 requires "**at least three** candidates";
SRS §8.6 test FR-13 expects "**three distinct** candidates". PPM Table 10 anticipates the collision:
"candidates too similar … duplicates not presented twice".

If two profiles converge on the same timetable the system behaves **correctly** and the acceptance test
**fails**.

Options: (a) restate as "at least two distinct candidates, with profiles chosen so three distinct ones
are obtained on the reference instance"; (b) retain duplicates and flag them as identical.

**Blocks:** Phase 6 acceptance tests. **Owner:** technical lead, with the supervisor — it changes a
delivered acceptance criterion.

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

### C-9 — Four requirements have no detailed specification

**FR-6, FR-10, FR-17, FR-18** appear in the summary tables but have no input/processing/output row in
SRS §3.2. **FR-10 is missing entirely from the SRS Table 36 traceability matrix.**

Note: SRS Table 36 is nonetheless the only reliable place to reconstruct the FR numbering — the summary
tables in both CdC and SRS are damaged by cell-offset in the PDF layout, so codes and statements do not
line up when read literally.

**Blocks:** Phase 6 acceptance. **Owner:** technical lead.

### C-11 — The generated instance · **RESOLVED — it exists and it verifies**

**This finding was wrong, and is corrected here rather than deleted.** The scaffold originally recorded
the instance as missing and instructed the next session to write a generator reproducing it. It was
supplied on 2026-07-29 and is now in `data/instance/` — 13 CSVs, 36 KB.

**Every documented figure was re-measured and matches.** Not approximately — exactly:

| Claim | Documented | Measured |
|---|---|---|
| Sessions CM / TD / TP | 32 / 82 / 104 | ✅ 32 / 82 / 104 |
| Durations 1-period / 2-period | 114 / 104 | ✅ 114 / 104 |
| Groups PROMO / TD / TP | 6 / 15 / 30 | ✅ 6 / 15 / 30 |
| Rooms Amphi / Salle / Lab_Info / Lab_Sciences | 2 / 10 / 6 / 2 | ✅ 2 / 10 / 6 / 2 |
| Teachers by rank | 7 / 11 / 13 / 13 | ✅ 7 / 11 / 13 / 13 |
| Students · courses · slots open | 425 · 32 · 28 of 30 | ✅ 425 · 32 · 28 of 30 |
| Holidays, of which lunar | 18, 10 | ✅ 18, 10 |
| Availability rows · teachers covered | 157 · 41 of 44 | ✅ 157 · 41, all `SYNTHETIC` |
| Catalogue hard / soft · weight sum | 12 / 7 · 0.90 | ✅ 12 / 7 · 0.90 |
| **Verification 1** sessions without a room | 0 | ✅ **0** |
| **Verification 2** Amphi / Salle / Lab_Info / Lab_Sciences | 57% / 29% / **95%** / 86% | ✅ **57.1 / 29.3 / 95.2 / 85.7** |
| **Verification 3** over rank limit · heaviest | 0 · 12 periods (18 h) | ✅ **0 · 12 / 18** |
| **Verification 4** in difficulty · smallest margin | 0 · 11 free slots | ✅ **0 · 11** |
| **Verification 5** invalid refs · students matching | 0 · 425 | ✅ **0 · 425** |

The documentation's factual claims are therefore **verified, not merely asserted** — which is the
condition the whole "generated data is acceptable if verified" argument rests on (ADR-008).

**What remains of C-11:** the *generator* is still a stated deliverable (PPM §10) and does not exist.
That is now a documentation and reproducibility task, **not a blocker** — the instance it would produce
is already here and checked. Re-run the checks any time with
`scripts/verify-instance.ps1`.

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

**Blocks:** Phase 3 (scoring) — now unblocked. The availability grid in Phase 4 still needs its own
decision when (a) is revisited. **Owner:** technical lead, decided 2026-07-30.

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


**Still open from the superseded analysis, on its own merits:** the deterministic-time calibration in
the last paragraph above. `max_deterministic_time` did not tightly bound parallel search, and that
observation stands independently of C-13 — it was measured on runs that happened to be searching an
infeasible model, but nothing about the finding depends on that. The repaired instance now solves in
~0.2 deterministic units, far below any configured budget, so the question is no longer urgent; it
becomes urgent again when the objective goes in and solves get long enough to reach a budget.

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
