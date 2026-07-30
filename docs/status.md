# Status

**Increment 1 of 2 · Phase 2 complete · Phase 3 blocked on a specification decision (C-4, C-12).**
**Last updated 2026-07-30.**

Keep this file current. A stale status file is worse than none, because the next session trusts it.

> **Read [`docs/dashboard.md`](dashboard.md) first.** It carries the project state, the roadmap and the
> Phase 3 brief in one page. This file is the detail behind it: blockers, measurements, phases,
> acceptance criteria. Session-by-session history is archived in [`docs/history.md`](history.md).

---

## Where the project is

| | |
|---|---|
| **Current phase** | **Phase 2 complete**, committed and pushed. H1–H12 built and demonstrated correct — the reference instance produces a conflict-free timetable in ~3 s with every hard constraint re-verified from the raw CSVs. C-13 resolved (the model was correct; the *instance* was infeasible and has been repaired). C-7 resolved (`y[s][t]` channelled, tested, built on demand) |
| **Next step** | **Phase 3, blocked.** C-4 (a `v_i` and bounds for all seven soft criteria) and C-12 (S5 carries weight 0.20 with no input data) are the technical lead's decisions, not the keyboard's. Nothing further can be encoded until they land |
| **Days used** | ~2 of 20. Phases 1–2 were budgeted 8 |
| **Repo** | https://github.com/JINZO-AI/optiedt-ai-timetabling · `main` · **15 commits**, working tree clean, in sync with `origin/main` · latest `0dc0078` |
| **Blocked on** | **C-4 and C-12** — specification decisions. Nothing is blocked inside Phase 2 |

---

## Blockers, precisely

*C-6, C-7 and C-13 were resolved on 2026-07-30 and are recorded in `docs/open-questions.md`. What
follows is only what is still open.*

Both remaining blockers are decisions only the technical lead can make. Neither can be taken at the
keyboard, and guessing at either is what `CLAUDE.md` forbids.

### Blocks Phase 3

**C-4 — no soft criterion has a measurement formula.** All seven have codes, names and weights and
none has a definition of `v_i`. It feeds the score, the contributions, monotonicity, dominance and the
weight learning. Each also needs its `min_i`/`max_i` formula, which is one task per criterion, not two.
S6 additionally has a dead half: H5 already forbids a room smaller than its group, so "over-used" must
mean utilisation rate — the documents never say.

**C-12 — S5 carries weight 0.20 and has no input data.** `teacher_availability.csv` is a boolean and
all 157 rows are 0. Nothing expresses a *preferred* window, yet SRS §4.1 specifies a three-state grid.
⚠️ **This is C-5 in disguise** — see C-12 in `docs/open-questions.md` for why the two must be resolved
in one pass.

**Also owed once C-4 lands:** the objective's auxiliary variable count (first/last occupied period per
group-day, reified gap indicators). It follows from the criterion formulas, so it is recorded as
unknown rather than guessed — see C-7 in `docs/open-questions.md`.

---

## Next, in order

1. ~~Loader~~ · ~~Model H1–H12, H12 bug fixed~~ · ~~Decide C-13~~ · ~~Decide C-7~~ — **all done**, see
   `docs/history.md`. Phase 2 is closed.
2. **Decide C-12 and C-4**, then scoring — Phase 3. The immediate next step, and a specification
   decision rather than a keyboard one. The variables the objective will read (`x[s,t₀]`, `y[s,t]`)
   are already built and tested.
3. **Port the five verifications into the application** as FR-12. The standalone checker at
   `data/verification/verify_instance.py` already has the logic; the in-application version reports
   structural risks through the API. ⚠️ **Port the contiguity bound, not just the period bound** — the
   period bound alone is what let C-13 through, and shipping it alone would put the same blind spot in
   the product.
4. **Fill H10's dormant gap** when recommendation regeneration needs it: `build_variables` currently
   refuses to run if any session is locked, because `SolverInput` carries session ids without the
   target slot and room. Safe today only because the reference instance has none.

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
| **The cumulative reformulation and the warm-start were built for a problem that did not exist** | Two committed mechanisms (`cumulative_room_types`, `solver/warm_start.py`) are carried for a reason now known to be wrong. Both are correct and tested, neither is load-bearing: the model solves with the warm start off, and the greedy now reaches 218/218 in 0.04 s | **Not removed** — no evidence they harm anything, and both should earn their place once the objective makes the search non-trivial. **Whether the plain per-room encoding would now serve for every type is untested.** Re-evaluate when the objective lands; delete then if they still pay for nothing |
| **Objective encoding** | The auxiliary variables it needs are still absent from the size estimate | **Moved to Phase 3.** C-7 built the variables the objective reads (`x`, `y`); the auxiliaries follow from the criterion formulas, so the count is owed when C-4 lands |
| **Deterministic-time calibration unmeasured** | The user-facing time limit is a guess | **Dormant, not resolved.** Phase 2 ended without needing it — solves take ~0.2 deterministic units, far below any budget. Live again once the objective lengthens them; calibrate then |
| **Exam multi-room assignment** (R-6) | Breaks a shared `room[s]` abstraction | Keep it out of shared solver code from the start |
| ~~`uv` not installed~~ | — | **Resolved.** uv 0.12.0 installed; the whole toolchain runs |
| **Kaggle `students.csv` holds personal data** | 3,000 rows with names, emails, phones, addresses | Never load it beyond `student_id` + enrolment; never let such a field reach the assistant context |
| **C-12 × C-5 interaction** | If S5 measures zero, the teacher-favouring profile differs by S3 alone, candidates converge, and the "three candidates" acceptance test fails for an invisible reason | Resolve C-12 before Phase 3 |

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
| **Toolchain** | **all green** | 2026-07-30 | **7/7** layer contracts kept · ruff · format · mypy strict on **32** source files · **33 tests** (29 fast + 4 solver-marked) · instance verified · frontend `tsc` clean |
| **Python** | **3.14.2** | 2026-07-29 | Resolved by uv 0.12.0 |
| **OR-Tools CP-SAT imports and solves** | **yes** | 2026-07-29 | On Python 3.14. `max_deterministic_time` **is accepted by the solver parameters** — ADR-011 is implementable, not just plausible |
| Deterministic time → wall clock, reference instance | **not a clean ratio under `num_workers=0`** | 2026-07-30 | `max_deterministic_time=60` consumed 247.98 units before the 360s wall-clock ceiling stopped the run. Measured while searching an infeasible model, but the finding does not depend on that. Not urgent now — the repaired instance solves in ~0.2 deterministic units, far below any budget — and becomes urgent again once the objective makes solves long enough to reach one |
| **First valid timetable** | **2.84–3.30 s wall · 0.13–0.21 deterministic** | 2026-07-30 | ✅ **Target < 60 s met with a wide margin.** Seven seeds (1, 7, 42, 123, 999, 2026, 31337), production defaults (`num_workers=0`, warm start on); all seven placed 218/218. Full pipeline: warm-start construction, solve, and independent re-verification of every hard constraint from the raw CSVs (`tests/integration/test_h1_h12.py`). Measured on the repaired instance — see C-13; the earlier `UNKNOWN` results were an infeasible instance, not a slow model |
| Portfolio of 3 candidates | *not yet measured* | — | Target < 5 min |
| Diagnosis run on an infeasible instance | *not yet measured* | — | Single worker, no objective — expect it to be slow |
| **Effective `y[s][t]` count after pruning** | **5,328** of 6,104 | 2026-07-30 | 87.3% of the upper bound. Start indicators `x[s,t₀]`: **4,720**. Together 10,048 variables (C-7) |
| **Cost of building the C-7 accounting** | **2.9–4.1 s → 7.6–8.0 s** | 2026-07-30 | Same configuration, three seeds; deterministic time 0.4–1.9 → ~6.1. Why `build_occupancy()` is called on demand and not by the feasibility solve |

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
