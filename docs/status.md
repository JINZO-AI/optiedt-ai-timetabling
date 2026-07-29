# Status

**Increment 1 of 2 · Phase 1 complete · Phase 2 ready to start.**
**Last updated 2026-07-29, end of day.**

Keep this file current. A stale status file is worse than none, because the next session trusts it.

---

## ▶ Tomorrow morning — copy this to resume

> Resume OptiEDT. Read `CLAUDE.md`, then `docs/status.md`, then `docs/open-questions.md` — do not open the PDFs.
> We are at the start of Phase 2: build the CP-SAT model H1–H12 and get one conflict-free timetable on `data/instance/`.
> Before you write solver code, ask me to confirm C-7 (the `y[s][t]` channelling rule for 2-period sessions) and C-6 (which of H2/H11 skip their assumption literal).
> Leave C-4 and C-12 alone for now — they block Phase 3, not Phase 2, and I still owe you decisions on both.
> Run `scripts/run-checks.ps1` first to confirm the repo is green, then start with a loader that reads `data/instance/` into the domain types.

---

## Where the project is

| | |
|---|---|
| **Current phase** | Phase 1 complete — instance verified, sources evaluated, scope fixed |
| **Next phase** | Phase 2 — model H1–H12, first conflict-free timetable |
| **Days used** | ~1 of 20. Phase 1 was budgeted 3 days |
| **Repo** | https://github.com/JINZO-AI/optiedt-ai-timetabling · `main` · 3 commits, all green |
| **Blocked on** | Nothing blocks *starting* Phase 2. **C-7 blocks the objective encoding inside it**; C-4 and C-12 block Phase 3 |

**Phase 1's milestone is met**: instance verified, sources evaluated, scope fixed. It came in under
budget because the instance already existed, so roughly 2 days are free. Spend them on Phase 2, which
carries the real uncertainty, or on the ~2.5 unbudgeted assistant days.

---

## Session log — 2026-07-29

What actually happened today, so tomorrow does not re-derive it.

**Read and analysed.** All three specification documents end to end. Produced 12 findings — 11
contradictions or gaps between the documents, plus C-12 found later in the data. All in
`docs/open-questions.md` with options and owners.

**Decided four things**, each recorded as an ADR with its reasoning:
ADR-009 instance-derived normalisation bounds · ADR-010 assistant in increment 1 · ADR-011
`max_deterministic_time` instead of wall clock · C-8 roles per SRS Table 2.

**Built the repository.** 104 files. Twelve working documents, 11 ADRs, boundary types for every
module, config for both stacks. No application logic — that was deliberate.

**Placed and verified the data.** Reference archives into `data/reference/` and the generated instance
into `data/instance/`. Re-measured every figure the PDFs state as fact; all match, including the five
verifications. Wrote `data/verification/verify_instance.py` so it can be rechecked in one command.

**Ran the toolchain for the first time** after uv was installed, and it found a real bug: the layer
contracts were not loading at all (`include_external_packages` missing), so the check protecting the
central invariant of the design was silently doing nothing. Fixed, then confirmed the contract
actually fires by introducing a violation and watching the build fail on the exact line.

**Corrected two of my own mistakes.** C-11 said the instance was missing and told the next session to
write a generator — wrong, it existed. The domain enums used invented English names that could not
have parsed the real CSVs. Both corrected in place rather than quietly deleted.

**Three findings worth remembering:**

- The Kaggle archive calls itself *"Clean CSVs"*. 44% of its timeslot rows end before they start and
  83% of its room-slot pairs are double-booked. Verifying by opening files rather than reading
  documentation earned its keep.
- `.gitignore` inherited from GitHub's Python template contains `instance/` — meaning *Flask's*
  instance folder — and matches at any depth. It silently excluded `data/instance/`, the entire
  dataset. A fresh clone would have had no data and no explanation.
- OR-Tools imports and solves on Python 3.14 **and accepts `max_deterministic_time`**. ADR-011 is now
  something that has been run, not something taken from documentation.

### Done overall

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

---

## Blockers, precisely

Two are decisions only the technical lead can make; the third is a modelling choice that can be made
at the keyboard. **None of them stops Phase 2 from starting.**

### Blocks the *objective* inside Phase 2

**C-7 — the `y[s][t]` channelling constraint is unwritten.** `y[s][t]` is up to 6,104 booleans and its
real job is soft-constraint accounting, not H7. **104 of the 218 sessions span two periods**, so
`y[s][t]` must mean *occupies* t, not *starts at* t — and the rule linking `start[s]`, `iv[s]` and
`y[s][t]` across a 2-period duration appears in none of the three documents. The auxiliary variables
the objective needs are also uncounted, so the stated model size is an underestimate.

*H1–H12 and a first conflict-free timetable do not need this.* Start there; C-7 bites when the
objective goes in.

### Blocks Phase 3

**C-4 — no soft criterion has a measurement formula.** All seven have codes, names and weights and
none has a definition of `v_i`. It feeds the score, the contributions, monotonicity, dominance and the
weight learning. Each also needs its `min_i`/`max_i` formula, which is one task per criterion, not two.
S6 additionally has a dead half: H5 already forbids a room smaller than its group, so "over-used" must
mean utilisation rate — the documents never say.

**C-12 — S5 carries weight 0.20 and has no input data.** `teacher_availability.csv` is a boolean and
all 157 rows are 0. Nothing expresses a *preferred* window, yet SRS §4.1 specifies a three-state grid.
⚠️ **This is C-5 in disguise**: if S5 measures identically zero, the teacher-favouring profile differs
by S3 alone, two candidates converge, duplicate removal drops one, and the three-candidate acceptance
test fails — for a reason nobody would look for.

### Decide at the keyboard, before the diagnosis run

**C-6 — which of H2 / H11 skip their assumption literal.** H2 is subsumed by H12; H11 is implied by H3
and duplicates pre-analysis check 2. Redundant literals let the solver name a rule the user cannot act
on. Needed in Phase 5, but the constraint code is written in Phase 2, so decide it while writing.

---

## Next, in order

1. **Loader** — read `data/instance/` into the domain types. Nothing else can start without it.
2. **Model H1–H12** and get one conflict-free timetable. Phase 2's milestone. Does not need C-4, C-7 or C-12.
3. **Decide C-7**, then encode the objective.
4. **Decide C-12 and C-4**, then scoring — Phase 3.
5. **Port the five verifications into the application** as FR-12. The standalone checker at
   `data/verification/verify_instance.py` already has the logic; the in-application version reports
   structural risks through the API.

Persistence can wait: the solver can read the CSVs through the loader, and PostgreSQL is only needed
once runs, candidates and publication have to survive a restart.

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
