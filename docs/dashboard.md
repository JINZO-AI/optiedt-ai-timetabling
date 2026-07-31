# OptiEDT — Dashboard

**The handoff file. Read this second, after `CLAUDE.md`.** It carries the whole project state; every
other document is detail you fetch only when you need it.

**Last updated 2026-07-30**, during Phase 3 closure: portfolio orchestration and FR-16 landed, ADR-011's
overdue calibration discharged and the ADR amended, C-16 raised and resolved (`interleave_search`), C-15
deferred by decision. Only ITC-2007 validation remains.

---

## At a glance

| | |
|---|---|
| **Project** | OptiEDT — generates, ranks and explains weekly university timetables (Tunisian public faculty, LMD) |
| **Overall progress** | **~55 % of budgeted effort** (Phases 1–2 = 8 of 20 days, plus Phase 3). By *delivered product* it is lower — **3 of 9 acceptance criteria** met, 0 of 25 requirements finished, because the user-facing path is Phases 4–5. Both numbers are real; quote the measure with the number |
| **Current phase** | **Phase 3 — closure in progress, 5 of 6 checklist items done.** Criteria, scoring, ranking, decomposition, dominance, the objective, the recommendation translator, the **portfolio** and **FR-16** are implemented and tested; ADR-011's overdue calibration is discharged. **Remaining: ITC-2007 validation** (`docs/status.md`, "Next, in order") |
| **Current milestone** | Several candidates produced, ordered, and one difference decomposed — met **at the code level**; not yet reachable by a user (no run record, no endpoint) |
| **Current goal** | Close Phase 3 (ITC-2007 validation), then Phase 4: the web interface |
| **Next task** | Validation on the published ITC-2007 instances — the last Phase 3 closure item, and on the never-reduced list in `docs/status.md` |
| **Branch** | `main` — **5 commits ahead of `origin/main`, unpushed** |
| **Latest commit** | [`7d489c3`](https://github.com/JINZO-AI/optiedt-ai-timetabling/commit/7d489c3) — Phase 3 closure work. **Local only, not pushed**; `origin/main` is still at `0dc0078` |
| **Repository status** | **Ahead of `origin/main` by 5 local commits**, none pushed. Working tree clean |
| **Project health** | 🟢 **Green.** `scripts/run-checks.ps1` green, 95 tests pass. **C-16 resolved** — reproducibility and three distinct candidates now hold simultaneously at production settings, and the portfolio is ~2× faster than before. **3 of 9 acceptance criteria met**, up from 1 |

```
Increment 1   ███████████░░░░░░░░░  ~55 % of budgeted days

Phase 1  Needs, specification, instance verification   ████████████████████  ✅ done
Phase 2  Modelling H1–H12, first valid timetable       ████████████████████  ✅ done
Phase 3  Score, ranking, portfolio, recommendations    ██████████████████░░  🟡 closure 5 of 6 — only ITC-2007 validation remains
Phase 4  Web interface — grid, generation, comparison  ░░░░░░░░░░░░░░░░░░░░  ⬜ not started
Phase 5  Pre-analysis in-app, diagnosis, auth, runs    ░░░░░░░░░░░░░░░░░░░░  ⬜ not started
Phase 6  Tests, documentation, presentation            ░░░░░░░░░░░░░░░░░░░░  ⬜ not started
```

*Progress is measured in delivered phases against the 20-day increment-1 plan (Phase 1 = 3 d,
2 = 5 d, 3 = 3 d, 4 = 4 d, 5 = 2 d, 6 = 3 d). Phases 1–2 = 8 of 20 days budgeted, delivered in ~2.*

---

## Status by area

| Area | State |
|---|---|
| **Architecture** | 🟢 Stable. Four layers, boundaries enforced by `import-linter` — **7/7 contracts kept**. No layer edge has been weakened |
| **Solver** | 🟢 H1–H12 built and demonstrated correct. Reference instance solves in **2.8–3.3 s** (deterministic 0.13–0.21) across 7 seeds, all 218 sessions placed. C-7 fully closed — accounting (`x[s,t₀]`, `y[s,t]`) built on demand, auxiliaries measured at **5,249**. `solver/objective.py` (new) encodes S2–S10 as CP-SAT expressions; `engine.py` posts it — and builds occupancy at all — only when a criterion carries weight, so an all-zero profile is genuinely equivalent to a feasibility solve. **Deterministic budget calibrated 2026-07-30** — it binds exactly, per worker; 1 unit ≈ 4.8 s wall at one worker, ≈ 19 s at all sixteen. **`interleave_search = true` is set and is required for reproducibility** (C-16, ADR-011 amended); the warm start is withheld when an objective is posted, because it pinned all three profiles to one timetable |
| **Objective** | 🟡 Encoded for S2–S5, S7, S10 in full; **S6 only for non-cumulative room types** (Salle) — cumulative types (Amphi, Lab_Info, Lab_Sciences) have no per-room CP-SAT variable to optimise against, only a post-hoc labeller (C-13). `analysis/criteria.py` still scores S6 correctly for every room after the fact |
| **Analysis / scoring** | 🟢 Implemented and tested. `analysis/criteria.py` (7 criteria), `analysis/scoring.py` (`DefaultScorer`, `evaluate_candidate`), `analysis/ranking.py` (`DefaultRanker`: rank/decompose/dominance/**recommend** — FR-16). All four properties pass (`tests/property/test_scoring_properties.py`) |
| **Portfolio** | 🟢 `services/portfolio.py` — the only module importing both `solver` and `analysis`, which is what `services` is for. Defines the three profiles, divides the total budget between them, solves sequentially under one fixed seed, removes duplicate timetables and ranks the survivors under one weight vector. 16 unit tests pin the rules against a recording fake solver. Measured on the reference instance: **3 distinct candidates in 147–150 s**, reproducibly, total budget 90 (C-16) |
| **API · frontend · persistence** | ⬜ Scaffold only. Phases 4–5. The solver reads CSVs through `optiedt.instance`; PostgreSQL is not needed until runs must survive a restart |
| **Assistant** | ⬜ Scaffold only. Increment 1 (ADR-010), Phase 4+ |
| **Validation** | 🟢 `scripts/run-checks.ps1` green: 7/7 contracts · ruff · format · mypy strict on 39 files · tests · instance verification · frontend `tsc` |
| **Tests** | 🟢 **95 passing** (78 fast + 17 solver-marked). New this phase: `tests/integration/test_reproducibility.py` (FR-19/ADR-011 — reproducibility **at production settings**, and the per-worker budget binding), `tests/property/test_scoring_properties.py` (10 hypothesis properties), `tests/unit/test_criteria.py` (the seven formulas against a hand-computable instance), `tests/integration/test_objective_matches_analysis.py` (**the cross-layer guard** — CP-SAT's objective value must equal the analysis layer's recomputation on the same placements), `tests/unit/test_portfolio.py` (16 orchestration rules against a recording fake solver), `tests/unit/test_recommendation.py` (FR-16, including the proof that a dominated candidate can never be recommended) |
| **Documentation** | 🟢 Current as of this commit. Session history archived to `docs/history.md` |

---

## Open questions

**[`docs/open-questions.md`](open-questions.md) is the authority — this is a summary of it.** If the two
ever disagree, that file wins and this table is the bug. **Do not silently decide one.**

| # | Open question | Blocks | Owner |
|---|---|---|---|
| **C-5** | "At least three candidates" can fail when duplicates are removed | Phase 6 acceptance | Lead + supervisor |
| **C-9** | FR-6, FR-10, FR-17, FR-18 have no detailed specification | Phase 6 acceptance | Technical lead |
| **C-14** | Dominance uses the strict reading ("improves on **every** criterion"); S10's zero weight makes ties common. **And the "dominated *top* candidate" signal both documents require is provably unreachable** — a dominated candidate cannot outscore its dominator, so it can never rank first. Phase 4 would otherwise build a signal that can never fire | Phase 4 comparison screen | Technical lead |
| **C-15** | The objective weights raw violation counts of incomparable scale, so "teacher-favouring" favours only S5, not S3. **Deferred by decision 2026-07-30** — recorded, objective unchanged | FR-13's `✓`; Phase 4 comparison screen | Technical lead |

**Resolved, do not reopen without new evidence:** C-1, C-2, C-3, C-6, C-7, C-8, C-11, C-13, **C-4,
C-12, C-16** (2026-07-30). ADR-011 was amended rather than reversed: deterministic time bounds the
*work*, `interleave_search` orders the *race*, and both are required — see C-16.

⚠️ **C-5 is still open, but the behaviour it worries about does not occur.** At production settings
the portfolio returns **3 distinct candidates, 0 duplicates removed**, reproducibly. C-5 is a conflict
in the specification's *wording* ("duplicates removed" vs "at least three candidates"), which a
favourable measurement cannot settle — but the acceptance test would pass today.

---

## Known risks

| Risk | Effect | Handling |
|---|---|---|
| **~2.5 unbudgeted assistant days** | ≈12 % overrun on 20 days | Confirmed, not contingent. Release valve is scope-reduction step 1 |
| **91 % laboratory occupancy** (of two-period windows) | A modelling regression looks like an infeasible instance — **and an infeasible instance looks like a slow model** | Pre-analysis first, always. Read the *window* figure, not the period figure |
| **A check that is necessary but not sufficient** | Passes an infeasible instance, so the next failure is blamed on the model. Cost three sessions on C-13 | Both bounds now checked. **FR-12's port must carry both** |
| ⚠️ **`interleave_search` is marked "Experimental" upstream** | Reproducibility — a written acceptance criterion — now rests on one OR-Tools parameter whose guarantee could change between releases | **Pin the OR-Tools version.** `tests/integration/test_reproducibility.py` verifies it at production settings rather than trusting the docs; a failure there is blocking, not flaky |
| ~~**Deterministic-time calibration**~~ | ~~"the budget does not bind, ~11× over-run"~~ | **RESOLVED 2026-07-30 — the claim was false.** The budget binds *exactly*, per worker; `deterministic_time` reports the sum across workers and ~11 was the worker count on a 16-core machine. Calibrated figures in `docs/status.md`; correction in C-2 |
| **Raw-weight objective lets a large-scale criterion swamp a small one** | S5's raw value is ~100 (session count) while S3's is ~15 (idle periods). Inside teacher-favouring, S5 contributes 0.4×~80 ≈ 32 to the objective against S3's 0.3×~15 ≈ 4.5, so the profile is effectively S5-only. Measured: raising the budget improves S5 (101 → 72, better than balanced's 81) while S3 *degrades* (13 → 18) | The profile raises both weights exactly as documented, so this is not an implementation defect — it is a consequence of `minimise Σ(weight_i × violations_i)` using **raw** weights across criteria with incomparable scales. **"Teacher-favouring" does not currently favour teachers on S3.** Needs a decision (normalise the objective's weights, or set EMPHASIS per criterion); not resolved here |
| **S6 cannot be optimised for cumulative room types** | The CP-SAT objective only covers Salle (non-cumulative); Amphi/Lab_Info/Lab_Sciences rooms are chosen by a post-solve labeller the objective cannot see | Scored correctly after the fact regardless (`analysis/criteria.py`). Closing this needs `solver/variables.py` changes — out of scope this session |
| **`recommendations/translator.py` cannot build a full `SolverInput`** | `Run`/`Candidate` carry no instance reference, no base profile weights, no prior locks/exclusions | Returns a `RunOverride` (plain domain data) instead; a later layer (`services/`, Phase 4–5) must assemble the actual `SolverInput` |
| **Exam multi-room assignment** (R-6) | Breaks a shared `room[s]` abstraction | Keep it out of shared solver code from the start |

---

## Roadmap — remaining phases

### Phase 3 — Score, ranking, portfolio, recommendations · 🟡 **core algorithms done, integration remains**

**Purpose.** Turn one valid timetable into *several*, ordered, with the difference between any two
explained term by term. This is the half of the product that makes it defensible rather than merely
automatic.

**Completion criteria.**
- Three weight profiles produce candidates; each carries an overall score /100 and its sub-scores.
  ✅ **Met** — `services/portfolio.py` (new). On the reference instance it returns **3 distinct
  candidates, 0 duplicates removed**, each scored /100 with its seven sub-scores. ⚠️ It does so in
  **9.2 minutes against a < 5 min target**, and the profiles do not yet steer as their names promise —
  see the two risks below; the *mechanism* is complete, its *calibration* is not.
- The displayed contributions **sum exactly** to the score difference, to display precision. ✅ **Met**
  at the code level — `analysis/ranking.py`'s `decompose()`, verified by
  `tests/property/test_scoring_properties.py::test_decomposition_is_exact`.
- Dominance is detected and reported. ✅ **Met** — `DefaultRanker.dominance()`, property-tested.
- Two runs with the same data, weights and seed produce identical candidates in the same order.
  🟡 **Solver-side reproducibility is Phase 2's ADR-011 treatment, unchanged**; scoring/ranking are pure
  functions of the placements, so determinism follows once the solve itself is deterministic. Not
  independently re-measured with the objective posted this session — see the deterministic-time risk
  above.

**Dependencies.** ✅ **C-4** and **C-12** resolved 2026-07-30 — see `docs/open-questions.md` for the
formulas and reasoning. Phase 2 was otherwise a complete foundation.

**Status.** `analysis/criteria.py` (S2–S7, S10), `analysis/scoring.py`, `analysis/ranking.py`,
`solver/objective.py` (new), `recommendations/translator.py` (new) are implemented and tested — see
"Status by area" above for what each one does and does not yet cover (S6's cumulative-room-type gap,
the translator's inability to build a full `SolverInput`). **Not done:** portfolio orchestration (loop
over profiles, remove duplicates — needs C-5 decided first, see above), persistence of runs/candidates,
validation on the published ITC-2007 instances, H10's target-slot/room gap in `solver/variables.py`.

### Phase 4 — Web interface · ⬜ 4 days

**Purpose.** The complete path from a teacher declaring availability to a published timetable.
**Completion criteria.** Availability grid filled in under 5 minutes without training; generation
screen; side-by-side comparison with contributions; timetable views by teacher, group, room, lab.
**Dependencies.** Phase 3's algorithms exist to compare against; the portfolio orchestration and
persistence Phase 3 left undone will most likely be built as part of this phase's `services`/`db` work
rather than a separate pass. Also **C-12** — the grid needs a three-state cell if a real preferred-window
column (option (a), not yet built) is added.
**Status.** Not started. React + Vite scaffold only.

### Phase 5 — Pre-analysis in-app, diagnosis, auth, run record · ⬜ 2 days

**Purpose.** An infeasible instance must produce a report naming the rules in conflict, not a
timeout; every published timetable must trace back to its run, seed and weights.
**Completion criteria.** FR-12 reports structural risks through the API; the diagnosis run returns a
sufficient conflict set; a teacher account sees only its own data; runs are recorded.
**Dependencies.** Phase 3 for the run record; C-6 is already resolved (only H1, H3, H7, H12 carry an
assumption literal, so the conflict report can name an actionable rule).
⚠️ **FR-12 must port the contiguity bound as well as the period bound** — shipping the period bound
alone would put the C-13 blind spot inside the product.
**Status.** Not started. `preanalysis/` has the Protocol and the five check names, no bodies. The
working logic already exists in `data/verification/verify_instance.py`.

### Phase 6 — Tests, documentation, presentation · ⬜ 3 days

**Purpose.** Acceptance requirement by requirement; the project is accepted that way.
**Completion criteria.** The nine acceptance criteria in `docs/status.md` all ticked; documents complete.
**Dependencies.** All previous phases. **C-5** and **C-9** must be settled before the acceptance tests
are written, or they will fail for reasons that are not defects.
**Status.** Not started. One of nine acceptance criteria is met.

### Increment 2 — conditional on remaining time

Examination session (4 d) · weight adjustment from recorded comparisons (3 d). Natural-language
constraint entry is **not undertaken** — see `docs/ai-integration.md`.

---

## Phase 3 — what was built 2026-07-30, and what Phase 4 inherits

**What it set out to achieve.** A *portfolio*, not a timetable. Several valid timetables produced under
different weight profiles, ranked by an exact weighted sum, with the difference between any two
decomposed criterion by criterion.

**Why it exists.** The department will not adopt a timetable it cannot argue with. The score is linear
precisely so the explanation *is* the calculation read term by term, recomputable by hand from the
sub-scores and weights recorded with the run. That is the whole reason a weighted sum was chosen over
lexicographic ordering or a learned ranker (ADR-002).

**C-4 and C-12, resolved.** `docs/open-questions.md` carries the formulas for all seven criteria and the
reasoning for each choice (including the ones that were judgment calls, not derivations — S4's resource
and S6's target). S5 uses a labeled proxy (edge-of-day placement), not real preference data — recorded
as a deliberate, scope-driven stand-in for the real fix (a genuine preferred-window column), not a
definition of teacher preference.

**Built, this session.** `analysis/instance_view.py` (shared hierarchy/day-period lookups),
`analysis/criteria.py` (the seven `Criterion` implementations), `analysis/scoring.py` (`DefaultScorer`,
`evaluate_candidate`), `analysis/ranking.py` (`DefaultRanker` — rank/decompose/dominance),
`solver/objective.py` (new — the same seven formulas as CP-SAT expressions), `solver/engine.py` (wired
to call `build_occupancy` + the objective when `request.profile is not None`),
`recommendations/translator.py` (new), `tests/property/test_scoring_properties.py` (the four
properties, hypothesis-based).

**Portfolio orchestration, added 2026-07-30 (closure item 1).** `services/portfolio.py` builds the
three profiles from the catalogue, divides the total budget between them, solves sequentially under one
fixed seed, removes duplicate timetables and ranks the survivors under a single weight vector. An
earlier revision of this page claimed it was blocked on **C-5** and belonged to Phase 4–5. Both claims
were wrong: `docs/open-questions.md` — the authority — records C-5 as blocking *Phase 6 acceptance*,
and SRS Table 29 already specifies the implementation behaviour ("at most 3, duplicates removed"), so
nothing was blocked. `services` needs no database to run a portfolio.

**Not built, and why.** Validation on the published ITC-2007 instances (`docs/testing-strategy.md` §1)
has still not been run against the objective. H10's target-slot/room gap in `solver/variables.py` was
**not** closed — it needs `solver/variables.py` and `solver/interfaces.py` changes, and nothing before
Phase 5's run record can exercise it. `recommendations/translator.py` therefore returns a `RunOverride`
(plain domain data), not a `SolverInput` — see "Known risks" above for why the existing `Run`/`Candidate`
schema cannot support building one directly.

**S6 (room efficiency) is scored fully but optimised only partially.** `analysis/criteria.py` scores
every room correctly after the fact. `solver/objective.py` can only post a CP-SAT term for
non-cumulative room types (Salle) — cumulative types (Amphi, Lab_Info, Lab_Sciences, C-13) have no
per-room decision variable at all; a specific room is chosen by a deterministic post-solve labeller the
objective cannot see or influence. Closing this would mean changing `solver/variables.py`.

**Which documents are authoritative, still.**

| Question | Authority |
|---|---|
| The three formulas, bounds policy, the four required properties | [`docs/scoring-and-explanation.md`](scoring-and-explanation.md) |
| The seven `v_i`/bounds formulas actually chosen, and why | [`docs/open-questions.md`](open-questions.md), C-4 and C-12 |
| Criterion codes, names, default weights | `data/instance/constraint_catalogue.csv` — **not** the PDFs |
| Which variables the objective may read | [`docs/constraint-model.md`](constraint-model.md), C-7 section |
| Layer permissions | [`docs/architecture.md`](architecture.md) + `backend/.importlinter` |
| Recommendations and regeneration | [`docs/ai-integration.md`](ai-integration.md) |

**Constraints already implemented.** All twelve hard constraints. H1, H3, H7, H12 are real CP-SAT
postings and carry assumption literals; H4, H5, H6, H8, H9, H10 are domain restrictions applied at
variable construction; H2 is subsumed by H12 and H11 by H3, both registered as documented no-ops.
**H10 is registered but dormant, still** — `build_variables` refuses to run if any session is locked,
because there is no way yet to supply the target slot/room. The reference instance has no locked
sessions. This did **not** get filled this session (out of scope, see above); recommendation-driven
regeneration is what will first need it.

**Constraints remaining.** None for the weekly model. X1–X4 and SX1 are the examination model —
increment 2.

---

## Where to look for what

| You need | Read |
|---|---|
| Invariants, commands, conventions | `CLAUDE.md` |
| Detailed state, measurements, acceptance criteria | [`docs/status.md`](status.md) |
| What is undecided | [`docs/open-questions.md`](open-questions.md) |
| Why a past decision was taken | [`docs/decisions/`](decisions/) — 11 ADRs |
| What happened, session by session | [`docs/history.md`](history.md) — archive, read only for forensics |
| "Is FR-15 built?" | [`docs/requirements-traceability.md`](requirements-traceability.md) |
| Everything else | The table in `CLAUDE.md` |
