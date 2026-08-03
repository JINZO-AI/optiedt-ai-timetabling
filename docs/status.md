# Status

**Increment 1 of 2 · Phases 1–3 complete. Phase 4 (the web interface) is next and has not started.**
**C-4, C-12 and C-16 resolved; C-15 deferred by decision. Four questions remain open, none blocking Phase 4.**
**Last updated 2026-07-31.**

Keep this file current. A stale status file is worse than none, because the next session trusts it.

> **Read [`docs/dashboard.md`](dashboard.md) first.** It carries the project state, the roadmap and the
> brief for whichever phase is current — **Phase 4** — in one page. This file is the detail behind it:
> blockers, measurements, phases, acceptance criteria. Session-by-session history is archived in
> [`docs/history.md`](history.md).

---

## Where the project is

| | |
|---|---|
| **Current phase** | **Phase 4 — the web interface. In progress, M5 of 6 complete.** Generation, the four timetable views and the comparison screen all run end to end against the real solver. Milestone table in [`docs/dashboard.md`](dashboard.md) |
| **Last completed phase** | **Phase 3, closed 2026-07-31.** Delivered the seven criteria, the scorer, the ranker (decomposition, dominance, FR-16's recommendation), the CP-SAT objective, the recommendation translator, the portfolio, and validation on the 21 published ITC-2007 instances. C-4, C-7, C-12, C-13 and C-16 all resolved along the way |
| **Next step** | ⚠️ **Blocked.** **C-12(a)** must be settled before M6's availability grid (the last Phase 4 milestone) and **C-14** before M5's dominance signal (the only unbuilt part of the comparison screen). Both are the technical lead's |
| **Days used** | ~3 of 20 across Phases 1–3, which were budgeted 3 + 5 + 3 = 11 |
| **Repo** | https://github.com/JINZO-AI/optiedt-ai-timetabling · `main` · latest **pushed** commit `bfe805a`, 2026-08-01; anything after it is local. ⚠️ **No local-commit count is recorded here** — this line has been wrong three times (`0dc0078`, a parent, until 2026-07-31; `acf9aa0` with "9 commits" after eight were pushed; then "1 commit", which the correcting commit itself made 2). **A count cannot live in a file that commits change.** Re-derive: `git rev-parse origin/main`, `git rev-list --count origin/main..HEAD` |
| **Blocked on** | Nothing. **C-5** blocks the FR-13 acceptance test and **C-9** the Phase 6 acceptance tests, both in Phase 6; **C-14** blocks the Phase 4 comparison screen's dominance signal; **C-15** blocks FR-13's `✓`. None blocks starting Phase 4 |

---

## Blockers, precisely

*C-6, C-7, C-13, C-4, C-12 and C-16 are all resolved and recorded in `docs/open-questions.md`, which is
the authority. What follows is only what is still open.*

**Nothing blocks Phase 4.** Of the four open questions, one lands inside Phase 4 (C-14, before the
comparison screen builds its dominance signal) and three land in Phase 6.

### C-4 and C-12 — resolved 2026-07-30

**C-4.** All seven criteria (S2, S3, S4, S5, S6, S7, S10) now have a `v_i` and a `min_i`/`max_i`
formula, implemented in `analysis/criteria.py` and independently re-implemented as CP-SAT expressions
in `solver/objective.py` (the two layers may not share code — see that module's docstring). Full
formulas and the reasoning behind each choice, including the two genuine judgment calls (S4's resource,
S6's target), are in `docs/open-questions.md`.

**C-12.** S5 uses a labeled proxy — sessions placed in the first or last period of the day — rather
than real preference data, because the objectively better fix (a genuine preferred-window column) needs
`data/instance/` and `instance/loader.py` changes that were outside this session's scope. The proxy
gives S5 genuine candidate-dependent variation (confirmed on the real reference instance: 91–116 of 218
sessions touch an edge period, depending on the profile), which is what the C-12×C-5 risk needed —
without resolving C-5 itself.

**Owed and closed alongside C-4:** the objective's auxiliary variable count, **measured at 5,249** under
catalogue weights and **0** when every weight is zero. `solver/objective.py` builds
`occ`/`any`/`first`/`last`/`idle` variables per (teacher-or-leaf-group, day) pair and per-room deviation
variables for S6; the per-criterion breakdown is in Measurements below and in
`docs/constraint-model.md`, which no longer carries an order-of-magnitude estimate. Closes the last open
half of C-7.

### C-16 — resolved 2026-07-30

**Reproducibility and "at least three candidates" both hold**, at production settings, via
`interleave_search = true` and withholding the warm start when an objective is posted. ADR-011 was
amended rather than reversed: deterministic time bounds the *work*, `interleave_search` orders the
*race between workers*, and both are needed. Full account in `docs/open-questions.md`, including the
reasoning error that made this look like a specification conflict for one session.

### Still open, blocking something later

**C-5 — "at least three candidates" can fail when duplicates are removed.** Blocks the FR-13
acceptance test. The behaviour it worries about does not occur at production settings — three distinct
candidates, zero duplicates removed — but a favourable measurement cannot settle a conflict in the
specification's *wording*.

**C-15 — the objective weights raw counts of incomparable scale.** Deferred by decision 2026-07-30;
blocks FR-13's `✓` because the profiles do not differentiate for the documented reason.

**C-14 — dominance uses the strict reading, and the "dominated top candidate" signal cannot fire.**
Blocks the Phase 4 comparison screen: it would otherwise build an indicator that is provably always
empty.

**C-9 — four requirements have no detailed specification.** Blocks Phase 6 acceptance tests.

---

## Next, in order

1. ~~Loader~~ · ~~Model H1–H12, H12 bug fixed~~ · ~~Decide C-13~~ · ~~Decide C-7~~ — **all done**, see
   `docs/history.md`. Phase 2 is closed.
2. ~~Decide C-12 and C-4~~ · ~~Implement the seven criteria, scoring, ranking, the objective, the
   recommendation translator, the four properties~~ — **done 2026-07-30**. See `docs/dashboard.md`'s
   "Phase 3 — what was built" for the precise file list and what each one does and does not cover.
3. ~~**Portfolio orchestration**: loop over the 3 profiles, score each candidate, remove duplicates.~~
   **Done 2026-07-30** — `services/portfolio.py`, 16 unit tests. On the reference instance: 3 distinct
   candidates, 0 duplicates.
   ⚠️ **This entry previously claimed it was blocked on C-5 and belonged to Phase 4–5. Both were
   wrong.** `docs/open-questions.md` is the authority on what an open question blocks and records C-5
   against *Phase 6 acceptance*; SRS Table 29 already fixes the implementation behaviour ("at most 3,
   duplicates removed"), so only the acceptance *wording* was ever undecided. And `services` needs no
   database to run a portfolio — "needs `services`" is not "needs Phase 4". The error cost nothing here
   because it was caught, but it is the same shape as C-13: a plausible blocker nobody tried to falsify.
4. ~~**Recalibrate the deterministic-time budget.**~~ **Done 2026-07-30.** The budget was never
   failing: it binds exactly per worker, and the "~11× over-run" was `deterministic_time` reporting the
   sum across workers. Calibration in Measurements below; correction in C-2. What the calibration
   *did* uncover is **C-16**, resolved the same day — `interleave_search` makes the parallel search
   deterministic, so ADR-011 was amended rather than refuted.
5. ~~**Validation on the published ITC-2007 instances.**~~ **Done 2026-07-31**, closing Phase 3.
   `optiedt.validation.itc2007` reads the `.ctt` format (**not `.ectt`** — an earlier note in this file
   named the wrong extension; the archive holds plain `.ctt`), implements ITC-2007's own four hard
   constraints and four soft costs, and models the problem in CP-SAT. Run it with
   `scripts/validate-itc2007.ps1`. Results in Measurements below.

**Phase 3 is closed.** What follows belongs to Phases 4–6, in this order:

6. **Phase 4 — the web interface.** Availability grid, generation screen, comparison screen, the four
   timetable views. Also the first consumer of the portfolio and the decomposition, which exist and are
   tested but are not yet reachable by a user. ⚠️ Settle **C-14** before building the dominance signal:
   the "dominated top candidate" indicator both documents ask for can never fire.
7. **Port the five verifications into the application** as FR-12 (Phase 5). The standalone checker at
   `data/verification/verify_instance.py` already has the logic; the in-application version reports
   structural risks through the API. ⚠️ **Port the contiguity bound, not just the period bound** — the
   period bound alone is what let C-13 through, and shipping it alone would put the same blind spot in
   the product.
8. **Fill H10's dormant gap** when recommendation regeneration needs it: `build_variables` currently
   refuses to run if any session is locked, because `SolverInput` carries session ids without the
   target slot and room. Safe today only because the reference instance has none.
   `recommendations/translator.py` already reads a `lock_session`'s target slot/room out of the
   candidate correctly (`LockedPlacement`); what is missing is downstream — `SolverInput` needs a way to
   carry that target, and `build_variables` needs to honour it.
9. **Write the instance generator** (`data/generator/`), a stated deliverable of PPM §10 that does not
   exist. The 13 files in `data/instance/` were produced without it, so the application is unaffected
   and nothing is blocked — but the deliverable is owed, and it must **reproduce *the* documented
   instance, not merely a valid one** (ADR-008), because every figure in these documents is measured
   against that specific instance. It imports nothing from `backend/`: the 13 files are the contract
   between generator and application (`docs/data-and-instance.md`).
   ⚠️ **Added to this list 2026-07-31.** It had been recorded in three places — `data-and-instance.md`,
   ADR-008, and C-11's body — and scheduled in none, which is how a deliverable inside a section headed
   *RESOLVED* goes missing. Latest sensible point is Phase 6, with the documentation.

Persistence can wait until Phase 5: the solver reads the CSVs through the loader, and PostgreSQL is
only needed once runs, candidates and publication have to survive a restart.

## Phases — increment 1, 20 working days

| Phase | Work | Days | Milestone |
|---|---|---|---|
| 1 | Needs, specification, source evaluation, instance verification | 3 | Instance verified, sources evaluated, scope fixed |
| 2 | Modelling H1–H12, first valid timetable | **5** | A timetable without conflict on the instance |
| 3 | Profiles, portfolio, score, ranking, decomposition, recommendation catalogue, regeneration, validation on published instances | 3 | Several candidates produced, ordered, and a difference decomposed |
| 4 | Availability grid, generation screen, comparison screen, views | 4 | Complete path from declaring availability to publication |
| 5 | Pre-solve verification, diagnosis run, authentication, rights, run record | 2 | An infeasible instance produces a report naming the rules in conflict |
| 6 | Tests, documentation, presentation | 3 | Application demonstrable, documents complete |

Phase 2 gets the largest share because it carries the most uncertainty.

**Increment 2, conditional on remaining time:** examination session (4 d), weight adjustment (3 d).
Natural-language constraint entry is **not undertaken** — it would require a solver-validation harness
that does not fit the project (see `docs/ai-integration.md`).

---

## Order of scope reduction, if the work runs late

Decided in advance, so the decision is not taken under pressure:

1. The assistant's **report** is abandoned — explanations and answers kept.
2. **Weight adjustment** is abandoned — catalogue weights kept.
3. The **examination session** is reduced to placement under X1–X4, without the spreading criterion.
4. The number of **quality criteria** in the score is reduced.
5. The number of **views** displayed is reduced.
6. **Rights management** is reduced to the separation between the person in charge and other users.

**Never reduced**, because they carry the demonstration that the application works and that its results
can be justified: the engine, pre-solve verification, diagnosis of infeasible instances, the score with
its decomposition, and validation on the published instances.

---

## Live risks

| Risk | Effect | Handling |
|---|---|---|
| **~2.5 unbudgeted assistant days** (C-1) | ≈12% overrun on 20 days | Confirmed, not contingent. Release valve is reduction step 1 |
| **91% laboratory occupancy** (of two-period windows) | A modelling regression looks like an infeasible instance — **and, as C-13 showed, an infeasible instance looks like a slow model** | Pre-analysis first, always, and read the *window* figure rather than the period figure. Re-check both whenever the instance changes |
| **A pre-analysis check that is necessary but not sufficient** | Passes an infeasible instance, so the next failure is attributed to the model. Cost three sessions on C-13 | Both bounds now checked in `verify_instance.py`. Any new check must state whether it is sufficient, and FR-12 must port both |
| **The cumulative reformulation and the warm-start were built for a problem that did not exist** | Two committed mechanisms (`cumulative_room_types`, `solver/warm_start.py`) are carried for a reason now known to be wrong. Both are correct and tested, neither is load-bearing: the model solves with the warm start off, and the greedy now reaches 218/218 in 0.04 s | **Still not removed.** The objective has now landed and confirmed a real cost: `cumulative_room_types` also means S6 (room efficiency) cannot be optimised for those room types at all, only scored after the fact — see below. **Whether the plain per-room encoding would now serve for every type remains untested** |
| **Objective encoding — done, with one gap** | S2–S5, S7, S10 are fully encoded in `solver/objective.py`. **S6 only covers non-cumulative room types (Salle)** — cumulative types (Amphi, Lab_Info, Lab_Sciences) have no per-room CP-SAT variable, only a post-solve labeller the objective cannot influence | `analysis/criteria.py` still scores S6 correctly for every room. Closing the solver-side gap needs `solver/variables.py` changes (out of the scope this landed in) |
| ~~**Deterministic-time calibration — the budget does not bind**~~ | ~~a consistent ~11× over-run~~ | **RESOLVED 2026-07-30 — the claim was false.** The budget binds exactly, per worker; `deterministic_time` reports the sum across workers, and ~11 was the worker count. Calibration recorded in Measurements below. See C-2 |
| ~~**Reproducibility does not hold at the production worker count**~~ | ~~identical runs returned different candidates~~ | **RESOLVED 2026-07-30 (C-16).** `interleave_search = true` makes the search deterministic at full parallelism; the warm start is withheld under an objective because it pinned all three profiles to one timetable. Both criteria now met simultaneously, and the configuration is ~2× faster than before. ADR-011 amended |
| ⚠️ **`interleave_search` is marked "Experimental" upstream** | Reproducibility — a written acceptance criterion — now rests on one OR-Tools parameter whose guarantee could change between releases | **Pin the OR-Tools version.** `tests/integration/test_reproducibility.py` verifies the behaviour at production settings rather than trusting the documentation; treat a failure there as blocking, not flaky |
| ⚠️ **`interleave_search` misreports `CpSolver.objective_value`** | Measured 2026-07-31 on ITC-2007 comp02/comp18/comp21: the reported objective sat **5–15 units above** the objective expression evaluated at the solution the solver returned, on solves that stopped before proving optimality. With the parameter off, the two agree exactly | **Affects nothing today, by design.** No score, ranking, comparison or display reads `SolverOutput.cost` — `analysis/criteria.py` recomputes every criterion from the placements, which the ban on `analysis → solver` forces. The two guards that could have gone flaky were pinned: `test_objective_matches_analysis.py` requires `proven_optimal`, and the ITC-2007 harness compares the encoding rather than the reported objective. **Do not start ranking on `cost`** — ADR-011 |
| **Raw-weight objective lets a large-scale criterion swamp a small one** | The objective minimises `Σ(weight_i × violations_i)` in **raw** units, and the criteria have incomparable scales — S5 ~100 (session count) against S3 ~15 (idle periods). In teacher-favouring, S5 contributes ≈32 to the objective against S3's ≈4.5, so it behaves as an S5-only profile. Measured across budgets: S5 improves 101 → 72 (beating balanced's 81) while S3 *degrades* 13 → 18. **"Teacher-favouring" does not currently favour teachers on S3** | Not an implementation defect — the profile raises both weights exactly as documented, and the analysis layer scores both correctly. It is a consequence of the objective's raw-weight formulation meeting criteria of different magnitudes. Needs a decision: normalise the objective's weights by each criterion's bound range, or set the emphasis factor per criterion. **Not decided here** |
| **Exam multi-room assignment** (R-6) | Breaks a shared `room[s]` abstraction | Keep it out of shared solver code from the start |
| ~~`uv` not installed~~ | — | **Resolved.** uv 0.12.0 installed; the whole toolchain runs |
| **Kaggle `students.csv` holds personal data** | 3,000 rows with names, emails, phones, addresses | Never load it beyond `student_id` + enrolment; never let such a field reach the assistant context |
| **`recommendations/translator.py` cannot build a complete `SolverInput`** | `Run` carries no instance reference or base profile weights; `Candidate` carries a profile *name*, not its weights; neither carries prior locks/exclusions | Returns a `RunOverride` (plain domain data: `WeightOverride`, `LockedPlacement`, `ExcludedOption`) instead, leaving assembly of the actual `SolverInput` to a later layer with run/instance context (`services/`, Phase 4–5) |
| ~~**C-12 × C-5 interaction**~~ | ~~If S5 measures zero, the teacher-favouring profile differs by S3 alone, candidates converge, and the "three candidates" acceptance test fails for an invisible reason~~ | **C-12 resolved 2026-07-30** — S5 now varies genuinely with the candidate (measured 91–116 of 218 sessions on the reference instance across two profiles). **C-5 itself is still open** and still needs its own decision before the FR-13 acceptance test is written |

---

## Housekeeping — three copies of the benchmark archives

| Location | Status |
|---|---|
| `data/reference/` | **Canonical.** Gitignored, documented by `PROVENANCE.md` |
| `dataset/` (repo root) | Duplicate. Gitignored by an explicit `/dataset/` rule — **safe to delete** |
| `..\dataset` (outside the repo) | The original. Safe to delete once you are happy with `data/reference/` |

⚠️ **Why the ignore rule matters.** `dataset/` was not covered by any pattern, so
all 161 files were staged for commit — including `students.csv` (3,000 rows of
names, e-mail addresses, phone numbers and postal addresses) and a 742 KB Windows
binary. Committing personal-data-shaped files is hard to undo once pushed. The
rule is now explicit; do not remove it.

## Measurements

Fill these in as they are taken. They are referenced from `CLAUDE.md` and `docs/constraint-model.md`.

| Measurement | Value | Taken on | Notes |
|---|---|---|---|
| **Toolchain** | **all green** | 2026-08-01 | **9/9** layer contracts kept · ruff · format · mypy strict on **59** source files · **168 backend tests** (146 fast + 22 solver-marked) · instance verified · frontend `tsc` clean · **7 frontend tests** (`vitest`, added M5 and wired into `run-checks.ps1`). Ninth contract (`api ⇸ solver`) added in Phase 4 M1 and verified to fire; `pytest` exit 5 no longer tolerated |
| **Python** | **3.14.2** | 2026-07-29 | Resolved by uv 0.12.0 |
| **OR-Tools CP-SAT imports and solves** | **yes** | 2026-07-29 | On Python 3.14. `max_deterministic_time` **is accepted by the solver parameters** — ADR-011 is implementable, not just plausible |
| **Deterministic time → wall clock, reference instance** | **1 deterministic unit per worker ≈ 4.8 s wall at `workers=1`; ≈ 19 s at `workers=0` (16 cores)** | 2026-07-30 | ✅ **ADR-011's overdue Phase 2 calibration, discharged.** Budget 5, objective posted, catalogue weights. `workers=1` → 24.1 s · `2` → 17.2 s · `4` → 17.5 s · `8` → 57.2 s · `0` → 94.8 s. More workers cost *more* wall clock for the same per-worker budget, because the budget is per worker and the total work scales with the count |
| **Does `max_deterministic_time` bind?** | **Yes — exactly, per worker** | 2026-07-30 | ⚠️ **This corrects a recorded error.** Budget 5 → reported 5.00 at `workers=1` (ratio **1.00**); 8.79 at 2, 13.70 at 4, 30.26 at 8, 53.63 at 0. `CpSolver.deterministic_time` reports the **sum across workers**, so the "~11× overshoot" previously recorded here was an aggregate misread as an overrun. A whole portfolio at total budget 15 consumed exactly 15.0 at one worker. The budget was never failing |
| ~~Deterministic time → wall clock (superseded)~~ | ~~"not a clean ratio"~~ | ~~2026-07-30~~ | **Superseded by the two rows above.** The original observation — 60 requested, 247.98 consumed — was the same aggregate artefact, measured on an infeasible model. Kept so the correction is traceable |
| **First valid timetable** | **2.84–3.30 s wall · 0.13–0.21 deterministic** | 2026-07-30 | ✅ **Target < 60 s met with a wide margin.** Seven seeds (1, 7, 42, 123, 999, 2026, 31337), production defaults (`num_workers=0`, warm start on); all seven placed 218/218. Full pipeline: warm-start construction, solve, and independent re-verification of every hard constraint from the raw CSVs (`tests/integration/test_h1_h12.py`). Measured on the repaired instance — see C-13; the earlier `UNKNOWN` results were an infeasible instance, not a slow model |
| **Portfolio of 3 candidates** | **147–150 s (2.5 min) at production settings, total budget 90** — 3 distinct candidates, 0 duplicates, reproducible. ✅ **Target < 5 min met.** (Before C-16: 306 s, not reproducible) | 2026-07-30 | Reference instance, seed 42, three profiles, budget divided 5 per profile. ⚠️ **The 5-minute figure is an estimate, not an acceptance criterion** — ADR-011 demoted both the 60 s and 5 min figures to "estimates, not wall-clock promises", and no acceptance criterion names a portfolio time bound. It is met comfortably today; do not turn it into a promise, because a deterministic budget is a unit of *work* and its wall-clock cost varies by machine |
| **Portfolio reproducibility** | **✅ at production settings** | 2026-07-30 | With `interleave_search = true` and the warm start withheld under an objective: two identical runs agree on candidate ids, order, placements, scores and sub-scores. **Before** the change, `workers=0` gave different order and different scores on every repeat; `workers=1` reproduced but yielded only 1–2 candidates. See **C-16** |
| **Effect of the C-16 configuration** | wall **306 s → 147–150 s**; candidates 3 → 3; reproducible **no → yes**; best score 82.23 → 80.31 | 2026-07-30 | Reference instance, seed 42, total budget 90. Roughly 2× faster and reproducible, at ~1.9 score points — the luck of a racing parallel search, given up deliberately. H1–H12 re-derived from the raw CSVs for all three candidates and the feasibility path: 32 checks, all pass. Feasibility-only solve ~3 s → ~4.4 s, still far inside its 60 s target |
| **ITC-2007 Track 3 — hard constraints** | **21 of 21 timetables violate none** | 2026-07-31 | ✅ **The claim `docs/testing-strategy.md` §1 makes first.** All four ITC-2007 hard constraints (Lectures, Conflicts, Availability, RoomOccupancy) re-derived from each instance and checked against the placements, never taken from CP-SAT's status. Seed 42, deterministic budget 60 per instance, production configuration. Total wall ~17 min |
| **ITC-2007 — the cost function itself** | **reproduces all 7 published solutions exactly** | 2026-07-31 | ✅ The archive ships solutions for comp01–07 produced by a third-party solver; `cost.py` re-evaluates them to exactly the cost its bundled report publishes — **all four components, all seven instances**. This is what makes every other figure in these rows checkable rather than self-consistent. Runs on every `run-checks.ps1` (no solver needed) |
| **ITC-2007 — cost vs the archive's published results** | **gap 255 %–9985 %, median 1269 %** on the 7 instances the archive gives figures for | 2026-07-31 | comp01 26 (best 5) · comp02 1035 (36) · comp03 531 (66) · comp04 479 (35) · comp05 1059 (298) · comp06 4034 (40) · comp07 852 (14). ⚠️ **Large, expected, and not a defect.** The strategy document states "the objective is not to beat published results"; the reference figures come from metaheuristics tuned for this exact problem, several with no time limit at all, against ~50 s of exact CP-SAT search here. **The model is demonstrably correct** — see the next row. The other 14 instances have no in-repo reference and are reported on validity alone |
| **ITC-2007 — evidence the model, not just the search, is right** | **comp11 solved to cost 0, proven optimal**; comp01 reaches the published optimum of **5** given more search | 2026-07-31 | Cost 0 is optimal by definition — no soft cost can be negative — and CP-SAT proved it. comp01 reached 5, equalling the best figure the archive records, when the same model was given roughly 8× the search (measured with `interleave_search` off, which does ~`num_workers`× more total work for the same per-worker budget). **The gap on the larger instances is search budget, not modelling.** Quote validity first, cost second, always with the budget |
| **ITC-2007 — reproducibility across runs** | **identical costs on all 21, twice** | 2026-07-31 | Two full sweeps, same seed and budget, on a machine whose load differed enough that per-instance wall clock moved by up to 2× (comp01 79 s → 41 s). Every one of the 21 costs matched. ADR-011's deterministic budget doing exactly what it was chosen for, on instances the project did not design |
| ⚠️ **`CpSolver.objective_value` vs the solution returned** | **disagreed on 2 of 21** (comp18, comp21), by 5–15 units | 2026-07-31 | Reported objective sat *above* the objective expression evaluated at the placements handed back, on solves that stopped before proving optimality. With `interleave_search = false` the two agree exactly on the same instances. **No figure anywhere depends on it** — every cost is re-derived by `cost.py`, and no score or ranking in the product reads `SolverOutput.cost`. Recorded in ADR-011; the two guards that could have gone flaky were pinned |
| **Full run through the API and the generation screen** | **COMPLETED in 105.3 s wall**, 3 distinct candidates, 0 duplicates, 218/218 placed each | 2026-08-01 | ⚠️ **Not comparable with the 147–150 s portfolio row below**: total budget **45**, `OPTIEDT_SOLVER_WORKERS=4` (set to keep the machine responsive during the check, not a product default), against that row's budget 90 at all workers. Reported deterministic 45.76 against 45 requested. Scores 79.82 / 79.79 / 79.62 — teacher-favouring, student-favouring, balanced. **student-favouring drove S2 to 0**, so the profiles do steer. What this measures is the *path* — launch, poll, score, render — not the engine, which has its own rows |
| **FR-18 room occupancy, rendered** | **matches `verify-instance` exactly, all four room types** | 2026-08-01 | The timetable screen's occupancy view sums to Amphi **32**, Salle **82**, Lab_Info **160**, Lab_Sciences **48** periods on the candidate it displays — the same figures `scripts/verify-instance.ps1` reports for the instance. Independent arithmetic (frontend, over placements) agreeing with the verifier is what makes the view trustworthy rather than merely plausible. ⚠️ It is the *period* figure; the bound that binds for laboratories is two-period windows, and the view says so on screen |
| **A budget too small to solve** | **run lands in `FAILED` carrying the reason** | 2026-08-01 | Total budget 3 (1 per profile) makes CP-SAT return `UNKNOWN`; `solver/engine.py` raises rather than reporting it as a normal result, the executor records `FAILED`, and the API surfaces the message. Correct behaviour, not a defect — and the C-13 lesson working: an `UNKNOWN` is never quietly passed off as an answer |
| Diagnosis run on an infeasible instance | *not yet measured* | — | Single worker, no objective — expect it to be slow |
| **Effective `y[s][t]` count after pruning** | **5,328** of 6,104 | 2026-07-30 | 87.3% of the upper bound. Start indicators `x[s,t₀]`: **4,720**. Together 10,048 variables (C-7) |
| **Cost of building the C-7 accounting** | **2.9–4.1 s → 7.6–8.0 s** | 2026-07-30 | Same configuration, three seeds; deterministic time 0.4–1.9 → ~6.1. Why `build_occupancy()` is called on demand and not by the feasibility solve |
| **First solve with the C-4/C-12 objective posted** | **~49 s wall · ~84 deterministic units**, feasible (not proven optimal) | 2026-07-30 | Seed 42, catalogue default weights, `deterministic_budget=30`, `num_workers=0`. 218/218 placed. ⚠️ The ~84 deterministic units against a budget of 30 is the **per-worker sum**, not an overshoot — see the two calibration rows above. This row previously read it as confirming a "calibration live again" risk that turned out not to exist |
| **Sub-scores, no objective vs. catalogue-weighted objective** | S2 65→2, S3 22→11, S4 45→52, S5 116→87, S6 1.76→1.53, S7 45→14, S10 104→139; score 78.0→**85.5** | 2026-07-30, after the S6 scale fix | Same seed (42). Every weighted criterion improves except S4; S10 (weight 0, never optimised for) degrades, which is expected multi-criteria behaviour. **Figures before the S6 fix were S2 19, S7 29, score 83.6** — the 28× over-weighting of S6 had been consuming search effort belonging to the criteria that actually carry weight (C-4) |
| **Objective auxiliary variables** | **5,249** under catalogue weights; **0** when every weight is zero | 2026-07-30 | Per criterion alone: S3 2,376 · S4 1,628 · S2 1,620 · S7 984 · S5 218 · S6 7 · S10 0. Closes the last open half of C-7 |
| **Normalised sub-score spread over 40 random placements** | S2 0.869–0.932 · S3 0.953–0.981 · S4 0.663–0.762 · S5 0.495–0.647 · S6 0.627–0.789 · S7 0.735–0.828 · S10 0.411–0.617 | 2026-07-30 | Bounds are **sound** (nothing left [0,1]) but **loose**, as ADR-009 accepts. ⚠️ S3's whole observable range is ~3 points of normalised scale, so at weight 0.15/0.9 it can move the score by at most ~0.5/100 — it is close to inert in the ranking. A tuning matter for Phase 4, not a correctness one |

### Measured on the instance, 2026-07-30 (after the C-13 repair)

Two bounds, because **the period bound alone is misleading** — that is what hid C-13. A two-period
session needs two *consecutive* open periods inside one day, so what a room really offers is
`Σ floor(L/2)` over its contiguous runs: **11 two-period windows a week**, not 28 periods.

| Room type | Rooms | Periods used / available | Period occupancy | 2-period windows used / offered | **Binding** |
|---|---|---|---|---|---|
| Amphi | 2 | 32 / 56 | 57.1% | — (no 2-period sessions) | — |
| Salle | 7 | 82 / 196 | 41.8% | — | — |
| **Lab_Info** | **8** | 160 / 224 | 71.4% | **80 / 88** | **90.9% ← tightest point** |
| Lab_Sciences | 3 | 48 / 84 | 57.1% | 24 / 33 | 72.7% |

`Lab_Info` has **8 spare two-period windows in the whole week**. Withdrawing one computer laboratory
removes 11 and makes the instance infeasible again. Re-run `scripts/verify-instance.ps1` after any
change to the instance — it now checks both bounds and fails, naming the shortfall, if either is
violated.

**For comparison, the original mix and why it read as feasible:** `Lab_Info` 6 rooms, 160 / 168
periods = **95.2 %** — comfortable — against 80 sessions needing 66 windows, **short by 14**.
`Lab_Sciences` 2 rooms, 48 / 56 = 85.7 %, against 24 needing 22, **short by 2**. The period figure was
never wrong arithmetically; it was answering a question that does not determine feasibility.

---

## Acceptance criteria — increment 1

Track these as they are met; the project is accepted requirement by requirement.

- [x] **No hard-constraint violation on the reference instance** — met 2026-07-30. Every one of H1–H12
      re-derived from the raw CSVs and checked against the returned placements, independently of
      CP-SAT's own status (`tests/integration/test_h1_h12.py`)
- [x] **At least three candidates, each with its overall score and sub-scores** — met 2026-07-30. Three distinct candidates at production settings, 0 duplicates removed, each with all seven sub-scores (C-16). ⚠️ Still subject to **C-5**, which is about the *wording* of the acceptance test, not the behaviour
- [x] **The sum of displayed contributions equals the score difference, to display precision** — met 2026-08-01, Phase 4 M5. The computation was verified 2026-07-30 (three real candidates, agreeing to 9 decimal places, plus a hypothesis property test); what was missing was *displayed*, and rounding happens in the component. `frontend/src/features/comparison/ContributionsTable.test.tsx` renders the table and reads the figures back out of the DOM. ⚠️ It caught a real defect: rounding each term independently does **not** preserve the sum — 2.7567 and −3.6663 show as 2.757 and −3.666, totalling −0.909 against a true difference of −0.910. Fixed with largest-remainder rounding, so each displayed term stays within one unit of the last place of its true value and the column adds up exactly
- [x] **Two runs with the same data, weights and seed produce the same candidates in the same order** — met 2026-07-30 at production settings, via `interleave_search` (C-16, ADR-011 amended). Verified on identical ids, order, placements, scores and sub-scores; guarded by `tests/integration/test_reproducibility.py`
- [ ] An instance without a solution produces a report naming the rules in conflict
- [ ] A teacher account obtains only its own availability and timetable
- [ ] Closing a half-day in configuration removes those slots from every timetable, **with no code change**
- [ ] The availability grid is filled in under 5 minutes without training
- [ ] Every published timetable traces back to its run, seed and weights
