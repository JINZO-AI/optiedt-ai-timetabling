# Project roadmap — one continuous sequence of phases

**This is the practical tracking view.** One question, one answer: *what phase are we in?*

> **Phase 10 — Requirement closure by test.** Phase 9 closed on 2026-08-10. Phase 10 has not begun.
>
> ⚠️ **Phase 9 delivered FR-10's software and did NOT tick it.** Print and export are reachable from all
> four timetable views and covered by 28 display tests; FR-10 stays **`WIP`** because C-9 leaves it with
> no criterion to verify against. The `✓` count is unchanged at 10 of 25.

⚠️ **This document does not replace anything.** `docs/dashboard.md` remains the handoff page and
`docs/requirements-traceability.md` remains the authority on any single requirement's status. This file
maps *all* of the work — including what the specification calls **increment 1** and **increment 2** —
onto one numbered sequence, so tracking needs only phase numbers.

**Where the increments went.** They are not deleted: ADR-010 commits the assistant to increment 1, and
PPM Table 6 defines increment 2, and both remain true and cited in the technical documents. In this view
their work simply lives in phases — increment 1 in **Phases 1–8**, increment 2 in **Phases 13–14**.

---

## 1 · Project overview

OptiEDT generates, ranks and explains weekly university timetables for a Tunisian public faculty under
the LMD system. **CP-SAT places the sessions** and is the only thing that may; **an exact weighted sum
ranks the results**, decomposing the difference between any two candidates term by term; **a language
model explains them** and is architecturally forbidden from placing, scoring or ranking anything.

Reference instance: 218 sessions · 51 groups · 44 teachers · 20 rooms · 28 open slots of 30.

---

## 2 · Phase roadmap

| Phase | Name | Status | Main outcome | Requirements | Commit(s) |
|---|---|---|---|---|---|
| **1** | Needs, specification, instance | ✅ COMPLETE | Instance verified against the PDFs; scope fixed | — | `eb8f8aa` … `cb802a5` |
| **2** | Modelling H1–H12 | ✅ COMPLETE | A conflict-free timetable, 218/218 in ~3 s | FR-3 | `2c9c356` … `0dc0078` |
| **3** | Score, ranking, portfolio | ✅ COMPLETE | 3 ranked candidates, exact decomposition, ITC-2007 validation | FR-4 · FR-5 · FR-6 · FR-13 · FR-15 · FR-16 · FR-17 | `acf9aa0` … `c6e5193` |
| **4** | Web interface | ✅ COMPLETE | Availability grid, generation, comparison, 4 views | FR-2 · FR-7 · FR-14 · FR-18 | `1e5e24f` … `8d1194b` |
| **5** | Pre-analysis, diagnosis, auth, runs | ✅ COMPLETE | Conflict report, PostgreSQL run record, RBAC, publication | FR-8 · FR-11 · FR-12 · FR-19 | `f2c778e` … `be684de` |
| **6** | Acceptance suite, generator, demo | ✅ COMPLETE | One test per requirement; 8 of 9 criteria met | FR-9 · promotes FR-5, FR-12, FR-15, FR-19 → ✓ | `3c210a7` … `ab98390` |
| **7** | Regeneration and the assistant | ✅ COMPLETE | New run from a recommendation; explain/answer/report | FR-22 · FR-23 · FR-24 · FR-25 | `2fba7c4` … `197b702` |
| **8** | Increment-1 closure and hardening | ✅ COMPLETE | **9/9 criteria** · C-15 resolved · production guard | FR-2 · FR-13 · FR-24 → ✓ | `faf86cc` … `fa5378c` |
| **9** | Outputs and distribution | ✅ COMPLETE | A timetable that can leave the screen — print and CSV, all four views | FR-10 *(software; tick held by C-9)* | `004f38d` … |
| **10** | Requirement closure by test | 🔵 **CURRENT** | Close requirements that lack only an acceptance test | FR-3 · FR-4 · FR-7 · FR-14 · FR-16 | — |
| **11** | Administrative surfaces | ⏳ PLANNED | The screens whose mechanisms already exist | FR-9 · FR-11 · student view | — |
| **12** | Data management | ⏳ PLANNED | A second institution becomes possible | FR-1 | — |
| **13** | Examination session | ⬜ CONDITIONAL | Exam timetabling (*was increment 2*) | FR-20 | — |
| **14** | Weight adjustment | ⬜ CONDITIONAL | Learn weights from recorded comparisons (*was increment 2*) | FR-21 | — |

🔴 **Cross-phase blocker — C-9.** FR-6, FR-10, FR-17 and FR-18 have no input/processing/output row in
SRS §3.2, and FR-10 is absent from Table 36 entirely. **They cannot be marked `✓` until the supervisor
supplies the rows** — this blocks *ticks*, never *software*. It is a gate, not a phase.

### Requirement coverage — all 25, each mapped to exactly one closing phase

Written out so nothing can be lost between views. **"Closing phase"** is the phase that takes the
requirement to `✓`, which is not always the phase that built it.

| FR | Requirement | Status | Built in | Closes in | Held by |
|---|---|---|---|---|---|
| FR-1 | Load and manage department data | — | — | **12** | not started |
| FR-2 | Teacher declares availability | ✅ | 4 | **8** | — |
| FR-3 | Generate respecting H1–H12 | WIP | 2 | **10** | acceptance-test scope |
| FR-4 | Improve quality within a time limit | WIP | 3 | **10** | no acceptance test |
| FR-5 | Several candidates, each scored | ✅ | 3 | **6** | — |
| FR-6 | Order candidates by score | WIP | 3 | 🔴 **C-9** | no SRS row |
| FR-7 | Display by teacher, group, room | WIP | 4 | **10** | no acceptance test |
| FR-8 | Report rules in conflict | WIP | 5 | 🔴 supervisor | statement ≠ criterion |
| FR-9 | Configure the calendar | WIP | 5–6 | **11** | screen not built |
| FR-10 | Print or export a view | WIP | **9** | 🔴 **C-9** | no SRS row |
| FR-11 | Authenticate and restrict by role | WIP | 5 | **11** | account management |
| FR-12 | Verify data before solving | ✅ | 5 | **6** | — |
| FR-13 | Candidates under distinct profiles | ✅ | 3 | **8** | — |
| FR-14 | Compare two candidates | WIP | 4 | **10** | no acceptance test |
| FR-15 | State each criterion's contribution | ✅ | 3 | **6** | — |
| FR-16 | Recommend one candidate | WIP | 3 | **10** | no acceptance test |
| FR-17 | Signal a dominated candidate | WIP | 3–6 | 🔴 **C-9** | no SRS row |
| FR-18 | Display room occupancy | WIP | 4 | 🔴 **C-9** | no SRS row |
| FR-19 | Record every run with its trace | ✅ | 5 | **6** | — |
| FR-20 | Examination session timetable | — | — | **13** | conditional |
| FR-21 | Adjust weights from comparisons | — | — | **14** | conditional |
| FR-22 | Explain a candidate's quality | ✅ | 7 | **7** | — |
| FR-23 | Regenerate from a recommendation | ✅ | 7 | **7** | — |
| FR-24 | Answer a question in ordinary language | ✅ | 7 | **8** | — |
| FR-25 | Produce a readable report | ✅ | 7 | **7** | — |

**Totals: 10 ✅ · 12 WIP · 3 not started = 25.** Of the 12 WIP, **none lacks working software**: 5 need
an acceptance test, **4 wait on C-9**, 2 need a screen over a working mechanism, 1 needs its statement
reworded.

⚠️ **FR-10 moved `—` → `WIP` on 2026-08-10 and the `✓` count did not move.** That is the shape a C-9
requirement takes when it is built: the software is finished and reachable, and the tick is held by a
missing specification row nobody in this repository can write.

---

## 3 · Completed phases

### Phase 1 — Needs, specification, instance verification ✅
Three specification PDFs read in full; 20 open questions catalogued in `open-questions.md`; the 13-file
reference instance verified against every figure the documents state as fact.
**Result:** the documentation's claims are *verified, not asserted* — the condition ADR-008 rests on.

### Phase 2 — Modelling H1–H12 ✅
All twelve hard rules; the `y[s][t]` occupancy encoding (C-7); room assignment reformulated for fully
interchangeable types.
**Research result — C-13, the phase's most valuable output.** Three sessions were spent on what looked
like a hard search problem. It was an **infeasible instance**: a two-period session needs two consecutive
open periods in one day, so a room offers 11 two-period windows a week, not 28 periods. `Lab_Info` was
short by 14. Found by *arithmetic*, not by tuning. The repair left the room total at 20.
**Lesson now enforced in the product:** the period bound is necessary and **not sufficient**; FR-12
carries both bounds.

### Phase 3 — Score, ranking, portfolio, recommendations ✅
Seven criteria with formulas (C-4), the scorer, the ranker, the CP-SAT objective, the closed
recommendation catalogue, the portfolio.
**Research results:** **C-16** — `interleave_search` gives reproducibility *and* diversity, ~2× faster,
refuting the recorded belief that they were mutually exclusive. **ITC-2007** — 21/21 instances violate
no hard constraint, and the cost function reproduces **all 7 published solutions exactly**.
**Test:** `test_objective_matches_analysis` — the cross-layer guard, which caught S6 priced 28× too high.

### Phase 4 — Web interface ✅
Six milestones: API foundation, run lifecycle, generation screen, four timetable views, comparison
screen, availability grid. First frontend tests.
**Its closing audit found 17 defects**, none caught by `run-checks.ps1`.

### Phase 5 — Pre-analysis, diagnosis, authentication, run record ✅
Five checks in-app with **both** occupancy bounds; the diagnosis run; PostgreSQL persistence; RBAC with
the teacher taken from the token; publication with an assembled trace.
**Research result — C-17:** enforcement literals *defeat CP-SAT's presolve*. An infeasibility a plain
solve proves in **0.0 s** returned `UNKNOWN` after 240 s under assumptions. Replaced by deletion-based
subset search: **`('H3',)`, minimal, in 1.9 s**. The documented mechanism was changed **on measurement**.

### Phase 6 — Acceptance suite, generator, demonstration ✅
`tests/acceptance/`, one file per requirement, each opening with the criterion it verifies. The instance
generator (PPM §10). The demonstration script.
**C-5 and C-14 resolved** by project-owner decision before any code — Pareto dominance adopted, and the
"dominated top candidate" clause deleted as describing a state the arithmetic forbids.

### Phase 7 — Regeneration and the assistant ✅
H10 made live (C-19); `services/regeneration.py`; the assistant's adapter, context builder, verifier and
computed forms; the report.
**Guarantee:** an accepted recommendation launches a **new run through the same solver** — never an
edit. The grounding check discards any answer containing a figure absent from its context.

### Phase 8 — Increment-1 closure and hardening ✅ *(2026-08-07)*
| Work | Commit |
|---|---|
| Documentation repair — 4 stale claims | `2d069e4` |
| **FR-24** — adapter `User-Agent` defect found by the **first live provider call** | `e128ee1` |
| **FR-2** — criterion settled (reworded), then its acceptance test | `73029f3`, `cd98437` |
| **C-15 resolved** → **FR-13 `✓`** | `c1aa78a` |
| Production guard on the published secret key | `fa5378c` |

**Research result — C-15, the phase's most valuable output.** The recorded diagnosis was wrong and its
proposed fix was worse. Six measurements refuted four candidate fixes:

1. **Normalise the objective by bound range** — *worse*. S3's range (752) is the **largest** of seven, so
   dividing by it shrinks S3 most: raw S3:S5 = 1:1.33 becomes **1:4.6**.
2. **Renormalise weights to sum 1** — **bit-identical** result. `Σ(wv)` and `Σ((w/T)v)` share an argmin.
3. **More budget** — tripled; the ~16-unit gap held.
4. **Miscoded terms** — no: **S3 alone reaches 0, proven optimal**, in 14.45 of 90 budget units.

The real fault was *which criteria the profile raised*. S5 is an admitted proxy (**C-12** — no
preferred-window column exists), and it is the most expensive criterion to optimise. `teacher-favouring`
now raises **S3 and S4**: S3 **29 → 0**, S5 103 → 95, score 79.45 → 81.10.
**The objective formulation is unchanged** — `minimise Σ(weightᵢ × violationsᵢ)`, raw weights.

**Also delivered:** the FR-24 live call (Groq, `llama-3.3-70b-versatile`, 3/3 generated, none discarded)
and the first-use walkthrough, whose usability findings are recorded **unscheduled** in `status.md`.

### Phase 9 — Outputs and distribution ✅ *(2026-08-10)*

**What FR-10 turned out to promise.** The requirement statement is *"Print or export a timetable view"*
and nothing else: **`docs/requirements-traceability.md` is the authority here**, because FR-10 is absent
from SRS Table 36 entirely and that file is what the project designated for exactly this case. It is a
disjunction naming two destinations — a noticeboard and a spreadsheet — so **both halves were built**,
each minimal. `docs/architecture.md` §Layers permits the presentation layer to *"display, filter,
print"*, which is what put the whole phase in the frontend: **no backend file was touched.**

**Delivered.**
- **Print** — a `@media print` stylesheet, and a print button on the four timetable views and on
  publications. Navigation, selectors, tabs and the buttons themselves are suppressed.
- **Export** — a semicolon-separated, BOM-prefixed CSV per view, built in the browser from data already
  fetched. French separator and decimal mark, because a French Excel opens `71.4` as text.
- **Provenance on both** — `provenanceEntries` is one list with two renderings, so a printed sheet and
  an exported file can never name different runs. It carries run, candidate, profile, score, seed, model
  version, deterministic budget and **the whole weight vector**, which is the FR-19 trace.
- **28 display tests**, `export.test.ts` (22) and `PrintHeader.test.tsx` (6). Frontend total 53 → 81.

⚠️ **The answer to "is a stylesheet enough?" was no, and for one specific reason.** Hiding the
navigation and printing the grid gives a correct but **anonymous** page — two candidates of one run are
indistinguishable on paper. `PrintHeader.tsx` exists to fix precisely that, and it is why the phase's
brief said not to assume.

**Two findings, both from exercising the real product rather than reading it.**

1. **A two-period session straddling the midday break exported as `11:50–15:30`** — arithmetically
   right, and it reads as 3h40 of unbroken laboratory work. The grid shows two bands. A `Périodes`
   column was added so the file can say what the screen says.
2. **`npm run lint` has never worked** — `frontend/package.json` declares the script and `eslint` is a
   devDependency, but **no ESLint config has ever been tracked in this repository**. It is invisible
   because `run-checks.ps1` does not run it. Pre-existing, unrelated to FR-10, **left unfixed on scope
   discipline** and recorded here so it is not lost.

⚠️ **FR-10 is `WIP`, not `✓`, and that is the correct outcome** — C-9 leaves it with no criterion to
verify against. The tests are therefore display-layer tests and **not** an acceptance file: there was no
promise to quote at the top of one, and inventing a criterion would be worse than having none.

---

## 4 · Current phase — Phase 10, Requirement closure by test

**Status: 🔵 CURRENT — not started.** Phase 9 closed on 2026-08-10.

### Why this phase is next
Five requirements are built, reachable and working, and are held at `WIP` only because no acceptance
test exists against their criterion. It is the cheapest remaining move on the `✓` count — pure
evidence, no new software.

### What Claude should do next
One acceptance file per requirement — FR-3, FR-4, FR-7, FR-14, FR-16 — driven through the HTTP API,
each opening with the criterion it verifies, in the established `tests/acceptance/` pattern.

---

## 5 · Current and future phases in detail

### Phase 10 — Requirement closure by test 🔵 CURRENT
**Purpose.** Five requirements are built, reachable and working, and are held at `WIP` only because no
acceptance test exists against their criterion.
**Requirements:** FR-3 (acceptance-test scope), FR-4, FR-7, FR-14, FR-16.
**Dependencies:** Phase 9 for nothing; **C-15 had to be resolved first** — FR-4 is about the objective,
and testing it before Phase 8 would have pinned the old behaviour.
**Tasks.** One acceptance file per requirement, driven through the HTTP API, each opening with the
criterion it verifies — the established pattern.
**Validation.** `run-acceptance.ps1` green; new tests fail before the assertion is satisfied.
**COMPLETE when** all five carry an acceptance test and are `✓`. **Would take the count to 15 of 25.**

### Phase 11 — Administrative surfaces ⏳
**Purpose.** Two requirements whose *mechanism* is built and tested but whose *screen* does not exist.
**Requirements:** FR-9 (calendar administration — `Slot.is_open` works and is acceptance-tested; the
screen is `features/admin/.gitkeep`), FR-11 (account management — C-18 records the seed command as a
development tool, never a provisioning mechanism). Plus the **student view**: the role is seeded and has
no screen.
**Dependencies:** none technical.
**COMPLETE when** an administrator can close a half-day and manage accounts through the interface, and a
student can reach their timetable.

### Phase 12 — Data management ⏳
**Purpose.** **The largest genuine gap.** FR-1 is `—`; the only way in is 13 hand-authored CSVs. Without
it there is no second institution.
**Requirements:** FR-1.
**Dependencies:** should follow Phases 10–11 so the model is stable before an import path is built on it.
**Tasks.** Import, per-entity management, validation surfaced *before* solving rather than inside a run.
⚠️ **Scope discipline:** the solver decides `(slot, room)` only — teacher assignment, session
materialisation and group membership are **inputs**. An import path must not grow into a student
information system.
**COMPLETE when** a second institution's data can be loaded, validated and solved without editing files
by hand.

### Phase 13 — Examination session ⬜ CONDITIONAL
**Purpose.** Exam timetabling. **This is what the specification calls increment 2**, budgeted 4 days.
**Requirements:** FR-20.
**Dependencies.** ⚠️ **ADR-008 places the ITC-2007 Track 1 verification at the start of this phase, and
no property of it may be assumed before then.** ⚠️ **R-6:** an examination may occupy **several rooms at
once**, so room assignment becomes a boolean matrix with a capacity sum — the single-room `room[s]`
abstraction must not be forced onto it.
**COMPLETE when** an exam timetable is produced under X1–X4 and validated on Track 1.

### Phase 14 — Weight adjustment ⬜ CONDITIONAL
**Purpose.** Learn criterion weights from recorded comparisons. **Increment 2**, budgeted 3 days.
**Requirements:** FR-21.
**Dependencies.** `Comparison` already exists in the domain as the training data. ⚠️ **The fitting must
preserve weight non-negativity** — monotonicity follows from it, and `test_scoring_properties` exists
partly to catch this.
**COMPLETE when** fitted weights reproduce recorded preferences under leave-one-out evaluation.

---

## 6 · What "PROJECT COMPLETE" means

Taken from the project's own documents, not from the size of the repository.

### ✅ Required — and **already delivered**
The specification's acceptance gate is **nine acceptance criteria** (`docs/status.md`). **All nine are
met.** ADR-010 commits the assistant to increment 1 and it is built. Phases 1–9 are complete.

> **By the project's own stated gate, the mandatory work is done.**

### 🟡 Strongly recommended before submission
| Item | Phase | Why |
|---|---|---|
| ~~**FR-10 export/print**~~ | 9 | ✅ **DELIVERED 2026-08-10.** Print and CSV on all four views. ⚠️ The requirement is still `WIP` — C-9 holds the tick, not the software |
| **Acceptance tests for 5 requirements** | 10 | Moves 10 `✓` → 15 `✓`; pure evidence, no new software |

### 🔵 Optional — improves the product, not required by the gate
Phase 11 (administrative surfaces) · Phase 12 (FR-1 data management) · the six unscheduled usability
findings in `status.md`.

### 🔴 Supervisor-dependent — **you cannot close these alone**
**C-9.** FR-6, FR-10, FR-17, FR-18 have no SRS specification row. Blocks **four ticks** and no software.
**FR-8's statement** was never reworded to match its criterion, which is why it stays `WIP`.

### ⬜ Out of scope unless time permits
Phases 13–14. PPM defines increment 2 as **"conditional on remaining time"**, and
`docs/ai-integration.md` records **natural-language constraint entry as not undertaken** — it would need
a solver-validation harness that does not fit the project.

---

## 7 · Progress — several honest measures

| Measure | Value | Note |
|---|---|---|
| **Phases complete** | **9 of 14** (64 %) | 9 of 12 (75 %) excluding the two conditional phases |
| **Acceptance criteria** | **9 of 9 (100 %)** | The specification's actual gate |
| **Requirements `✓`** | **10 of 25 (40 %)** | ⚠️ Understates reality badly — see below. **Unchanged by Phase 9**, deliberately |
| **Open questions** | **19 of 20 resolved** | One remains: C-9, supervisor-dependent |
| **Tests** | **517 backend + 81 frontend** | 411 fast + 62 solver + 44 database; frontend 53 → 81 in Phase 9 |
| **Mandatory work remaining** | **None** | By the nine-criteria gate |

⚠️ **Why 40 % is the most misleading number here.** Of the 12 `WIP` requirements, **none lacks working
software**. They are held by: no acceptance test (5), an unwritten SRS row — C-9 (4), an unbuilt screen
over a working mechanism (2), and a requirement statement never reworded to match its criterion (1).

⚠️ **Phase 9 is the clearest illustration of that gap.** It delivered a whole requirement's software
and moved the `✓` count by **zero**. Anyone quoting 40 % as progress should say what it measures.

**If a single figure is wanted, use this one and say how it is computed:**

> **~88 % of the project as scoped.** = Phases 1–9 complete (9/12 non-conditional phases = 75 %),
> weighted by the fact that the **acceptance gate is 100 % met** and the three remaining non-conditional
> phases are refinement rather than core capability. Phases 13–14 are excluded as conditional by PPM.

**Realistic remaining effort:** Phase 10 ≈ 1 day · Phase 11 ≈ 2 days · Phase 12 ≈ 3–5 days ·
Phases 13–14 ≈ 7 days if undertaken.

---

## 8 · How to use this document

| Question | Answer |
|---|---|
| *What phase are we in?* | The banner at the top |
| *What is left before Phase N is complete?* | §5, "COMPLETE when" |
| *Is the project finished?* | §6 — the mandatory gate is met; the rest is recommended or conditional |
| *Is requirement FR-N done?* | `docs/requirements-traceability.md` — that file stays the authority |
| *What is the state today?* | `docs/dashboard.md` — that file stays the handoff page |

⚠️ **Keep this file's phase table in step with `requirements-traceability.md`.** If they disagree, the
traceability table wins on any single requirement and this file is the bug.
