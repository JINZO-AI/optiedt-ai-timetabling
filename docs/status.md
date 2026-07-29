# Status

**Increment 1 of 2 · Phase 0 — repository scaffolded, no implementation yet.**

Keep this file current. A stale status file is worse than none, because the next session trusts it.

---

## Where the project is

| | |
|---|---|
| **Current phase** | Phase 0 — scaffold complete |
| **Next phase** | Phase 1 — instance generator, verification, catalogue |
| **Days used** | 0 of 20 |
| **Blocked on** | Nothing. C-4 and C-7 must be resolved before Phases 3 and 2 respectively |

### Done

- Repository structure, documentation, ADR-001 … ADR-011.
- All three specification documents read end to end; 11 contradictions and 7 architectural risks
  catalogued in `docs/open-questions.md`.
- Four decisions taken and recorded: assistant in increment 1 (ADR-010), deterministic time bound
  (ADR-011), instance-derived normalisation bounds (ADR-009), roles per SRS Table 2 (C-8).
- Layer boundaries expressed as an enforceable contract in `backend/.importlinter`.
- **Reference archives placed in `data/reference/` and re-verified** — ITC-2007 Track 3 (21
  instances), XHSTT-2014 (25 instances), Kaggle exam scheduling. Findings and measured figures in
  [`PROVENANCE.md`](../data/reference/PROVENANCE.md). ITC-2007 Track 1 remains absent; not needed
  until increment 2.
- **The reference instance is present in `data/instance/` and fully verified** — 13 CSVs, 36 KB.
  Every figure the PDFs state as fact was re-measured and matches, including all five verifications
  (Lab_Info at 95.2%, heaviest load 12 periods, smallest margin 11 free slots, 425 students matching
  declared group sizes). Checker: `scripts/verify-instance.ps1`. **C-11 is resolved** — the scaffold
  originally recorded the instance as missing, which was wrong.
- Domain enums corrected to the instance's actual vocabulary (`PROMO`/`TD`/`TP`, `Amphi`/`Salle`/
  `Lab_Info`/`Lab_Sciences`, French teacher ranks) and `occurrences_per_week` added to `Session`.
- **C-12 recorded** — S5 carries weight 0.20 and has no input data in the schema.

### Next, in order

1. **Resolve C-12** — S5 carries weight 0.20 and has no input data. Do this early: it interacts with
   C-5, and getting it wrong makes the acceptance test fail for an invisible reason.
2. **Resolve C-4** — the raw value and bounds of all seven soft criteria. Blocks scoring.
3. **Resolve C-7** — the `y[s][t]` channelling constraint. Blocks the model.
4. **Load the instance** — `data/instance/` into PostgreSQL, via migrations and a loader.
5. **Port the five verifications into the application** as FR-12. The standalone checker already
   exists at `data/verification/verify_instance.py`; the in-application version reports structural
   risks through the API.

**Phase 1 is largely done ahead of schedule.** The instance exists and verifies, and the reference
archives are in place — so the days budgeted to producing and checking data are freed. Consider
spending them on Phase 2, which carries the real uncertainty, or on the ~2.5 unbudgeted assistant days.

---

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
| **95% laboratory occupancy** | A modelling regression looks like an infeasible instance | Pre-analysis first, always. Re-check the figure whenever the instance changes |
| **Objective encoding** | Auxiliary variables absent from the size estimate; second unknown after C-7 | 5 days budgeted to Phase 2 |
| **Deterministic-time calibration unmeasured** | The user-facing time limit is a guess | Calibrate in Phase 2, record below |
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
| **Toolchain** | **all green** | 2026-07-29 | 6/6 layer contracts kept · ruff clean · mypy strict clean on 20 files · frontend `tsc` clean · instance verified |
| **Python** | **3.14.2** | 2026-07-29 | Resolved by uv 0.12.0 |
| **OR-Tools CP-SAT imports and solves** | **yes** | 2026-07-29 | On Python 3.14. `max_deterministic_time` **is accepted by the solver parameters** — ADR-011 is implementable, not just plausible |
| Deterministic time → wall clock, reference instance | *not yet measured* | — | Machine-dependent. Needed before any time limit is meaningful |
| First valid timetable | *not yet measured* | — | Target < 60 s, an estimate not a guarantee |
| Portfolio of 3 candidates | *not yet measured* | — | Target < 5 min |
| Diagnosis run on an infeasible instance | *not yet measured* | — | Single worker, no objective — expect it to be slow |
| Effective `y[s][t]` count after pruning | *not yet measured* | — | Upper bound 6,104 |

### Measured on the instance, 2026-07-29

| Room type | Demand / capacity | Occupancy |
|---|---|---|
| Amphi | 32 / 56 | 57.1% |
| Salle | 82 / 280 | 29.3% |
| **Lab_Info** | **160 / 168** | **95.2%** ← tightest point |
| Lab_Sciences | 48 / 56 | 85.7% |

Lab_Info has **8 spare room-periods in the whole week**. Withdrawing one computer laboratory removes 28
and makes the instance infeasible. Re-run `scripts/verify-instance.ps1` after any change to the
instance.

---

## Acceptance criteria — increment 1

Track these as they are met; the project is accepted requirement by requirement.

- [ ] No hard-constraint violation on the reference instance
- [ ] At least three candidates, each with its overall score and sub-scores *(see C-5)*
- [ ] The sum of displayed contributions equals the score difference, to display precision
- [ ] Two runs with the same data, weights and seed produce the same candidates in the same order
- [ ] An instance without a solution produces a report naming the rules in conflict
- [ ] A teacher account obtains only its own availability and timetable
- [ ] Closing a half-day in configuration removes those slots from every timetable, **with no code change**
- [ ] The availability grid is filled in under 5 minutes without training
- [ ] Every published timetable traces back to its run, seed and weights
