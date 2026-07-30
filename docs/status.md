# Status

**Increment 1 of 2 · Phase 2 complete · Phase 3 core algorithms done (C-4, C-12 resolved 2026-07-30);
portfolio orchestration, persistence and ITC-2007 validation remain, in Phase 4-5's scope.**
**Last updated 2026-07-30.**

Keep this file current. A stale status file is worse than none, because the next session trusts it.

> **Read [`docs/dashboard.md`](dashboard.md) first.** It carries the project state, the roadmap and the
> Phase 3 brief in one page. This file is the detail behind it: blockers, measurements, phases,
> acceptance criteria. Session-by-session history is archived in [`docs/history.md`](history.md).

---

## Where the project is

| | |
|---|---|
| **Current phase** | **Phase 2 complete**, committed and pushed. H1–H12 built and demonstrated correct — the reference instance produces a conflict-free timetable in ~3 s with every hard constraint re-verified from the raw CSVs. C-13 resolved (the model was correct; the *instance* was infeasible and has been repaired). C-7 resolved (`y[s][t]` channelled, tested, built on demand). **Phase 3's core algorithms are now built**: the seven criteria, the scorer, the ranker (decomposition + dominance), the CP-SAT objective and the recommendation translator — see below |
| **Next step** | Port the five pre-analysis checks into the application (FR-12), or start Phase 4 (web interface). Neither is blocked. Portfolio orchestration (loop over 3 profiles, remove duplicates) needs **C-5** decided first and belongs to `services/`, not this pass |
| **Days used** | ~2 of 20 for Phases 1–2, plus this session's Phase 3 work. Phases 1–2 were budgeted 8, Phase 3 budgeted 3 |
| **Repo** | https://github.com/JINZO-AI/optiedt-ai-timetabling · `main` · **15 commits** on `origin/main`, plus this session's Phase 3 work committed locally, not yet pushed · latest pushed commit `0dc0078` |
| **Blocked on** | Nothing inside Phase 3's given scope. **C-5** blocks portfolio orchestration and the FR-13 acceptance test; **C-9** blocks Phase 6 acceptance |

---

## Blockers, precisely

*C-6, C-7 and C-13 were resolved on 2026-07-30 and are recorded in `docs/open-questions.md`. C-4 and
C-12 were resolved the same session, after Phase 2, alongside the Phase 3 code that implements them.
What follows is only what is still open.*

Neither remaining item blocks anything inside the scope this session covered
(`analysis/ · solver/objective.py · recommendations/ · tests/property/`).

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

**Owed and closed alongside C-4:** the objective's auxiliary variable count. `solver/objective.py`
builds `occ`/`any`/`first`/`last`/`idle` variables per (teacher-or-leaf-group, day) pair and per-room
deviation variables for S6 — the order-of-magnitude estimate in `docs/constraint-model.md` can now be
replaced with a measured count (not yet done this session; see Measurements below for what was timed
instead).

### Still open, blocking something later

**C-5 — "at least three candidates" can fail when duplicates are removed.** Blocks portfolio
orchestration (looping over the 3 profiles and deduplicating candidates, which is `services/`, Phase
4–5) and the FR-13 acceptance test. Resolving C-12 lowers the risk of hitting this on the reference
instance but does not resolve the specification's own wording conflict.

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
4. **Port the five verifications into the application** as FR-12. The standalone checker at
   `data/verification/verify_instance.py` already has the logic; the in-application version reports
   structural risks through the API. ⚠️ **Port the contiguity bound, not just the period bound** — the
   period bound alone is what let C-13 through, and shipping it alone would put the same blind spot in
   the product.
5. **Fill H10's dormant gap** when recommendation regeneration needs it: `build_variables` currently
   refuses to run if any session is locked, because `SolverInput` carries session ids without the
   target slot and room. Safe today only because the reference instance has none.
   `recommendations/translator.py` already reads a `lock_session`'s target slot/room out of the
   candidate correctly (`LockedPlacement`); what is missing is downstream — `SolverInput` needs a way to
   carry that target, and `build_variables` needs to honour it.
6. **Recalibrate the deterministic-time budget.** A real solve under the objective took ~92
   deterministic units / ~50s wall against a 30s deterministic-budget target (`num_workers=0`) — the
   same C-2/C-13 under-bounding, now actually reached. Measure across seeds and profiles before Phase 4
   exposes a user-facing time limit.

Persistence can wait: the solver reads the CSVs through the loader, and PostgreSQL is only needed once
runs, candidates and publication have to survive a restart.

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
| **Deterministic-time calibration — the budget does not bind** | Measured 2026-07-30 with the objective posted, `num_workers=0`, reference instance: **10 units requested → 111.1 consumed** (191.6 s wall); **30 requested → 325.4 consumed** (600.7 s wall, stopped by the *wall-clock ceiling*, not the budget). A consistent ~11× over-run. ADR-011 adopted deterministic time precisely so that the wall clock would not be what ends a solve; today it is | **Open — closure checklist item 3.** Until this is fixed, no time bound in this system is trustworthy, and the reproducibility criterion that ADR-011 exists to guarantee is unverified |
| **The portfolio misses its < 5 min target** | 3 profiles at total budget 30 took **9.2 minutes** (551 s) on the reference instance. `services/portfolio.py` divides the budget exactly as docs/constraint-model.md requires (10 units each); the solver then over-runs each allocation ~11× | Mechanism is correct, calibration is not. Measurement is closure checklist item 2; the fix is item 3 |
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
| **Toolchain** | **all green** | 2026-07-30 | **7/7** layer contracts kept · ruff · format · mypy strict on **39** source files · **78 tests** (66 fast + 12 solver-marked) · instance verified · frontend `tsc` clean |
| **Python** | **3.14.2** | 2026-07-29 | Resolved by uv 0.12.0 |
| **OR-Tools CP-SAT imports and solves** | **yes** | 2026-07-29 | On Python 3.14. `max_deterministic_time` **is accepted by the solver parameters** — ADR-011 is implementable, not just plausible |
| Deterministic time → wall clock, reference instance | **not a clean ratio under `num_workers=0`** | 2026-07-30 | `max_deterministic_time=60` consumed 247.98 units before the 360s wall-clock ceiling stopped the run. Measured while searching an infeasible model, but the finding does not depend on that. Not urgent now — the repaired instance solves in ~0.2 deterministic units, far below any budget — and becomes urgent again once the objective makes solves long enough to reach one |
| **First valid timetable** | **2.84–3.30 s wall · 0.13–0.21 deterministic** | 2026-07-30 | ✅ **Target < 60 s met with a wide margin.** Seven seeds (1, 7, 42, 123, 999, 2026, 31337), production defaults (`num_workers=0`, warm start on); all seven placed 218/218. Full pipeline: warm-start construction, solve, and independent re-verification of every hard constraint from the raw CSVs (`tests/integration/test_h1_h12.py`). Measured on the repaired instance — see C-13; the earlier `UNKNOWN` results were an infeasible instance, not a slow model |
| Portfolio of 3 candidates | *not yet measured* | — | Target < 5 min |
| Diagnosis run on an infeasible instance | *not yet measured* | — | Single worker, no objective — expect it to be slow |
| **Effective `y[s][t]` count after pruning** | **5,328** of 6,104 | 2026-07-30 | 87.3% of the upper bound. Start indicators `x[s,t₀]`: **4,720**. Together 10,048 variables (C-7) |
| **Cost of building the C-7 accounting** | **2.9–4.1 s → 7.6–8.0 s** | 2026-07-30 | Same configuration, three seeds; deterministic time 0.4–1.9 → ~6.1. Why `build_occupancy()` is called on demand and not by the feasibility solve |
| **First solve with the C-4/C-12 objective posted** | **~49 s wall · ~84 deterministic units**, feasible (not proven optimal) | 2026-07-30 | Seed 42, catalogue default weights, `deterministic_budget=30`, `num_workers=0`. 218/218 placed. Confirms the "deterministic-time calibration live again" risk above — not yet measured across seeds |
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
- [ ] At least three candidates, each with its overall score and sub-scores *(see C-5)*
- [ ] The sum of displayed contributions equals the score difference, to display precision
- [ ] Two runs with the same data, weights and seed produce the same candidates in the same order
- [ ] An instance without a solution produces a report naming the rules in conflict
- [ ] A teacher account obtains only its own availability and timetable
- [ ] Closing a half-day in configuration removes those slots from every timetable, **with no code change**
- [ ] The availability grid is filled in under 5 minutes without training
- [ ] Every published timetable traces back to its run, seed and weights
