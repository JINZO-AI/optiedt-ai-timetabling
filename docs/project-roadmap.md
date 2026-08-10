# Project roadmap — one continuous sequence of phases

**This is the practical tracking view.** One question, one answer: *what phase are we in?*

> **Phase 11 — Administrative surfaces. NOT STARTED.** Phases 1–10 are complete. Opening Phase 11 is
> the project owner's call, not a session's — but everything it needs is written down: **§5 below is
> the handoff**, and it is what a fresh session should read after the dashboard.
>
> ✅ **16 of 25 requirements are `✓`.** Phase 10 took the count from 10 to 15 (FR-3, FR-4, FR-7, FR-14,
> FR-16); the **pre-Phase-11 audit of 2026-08-10 added FR-17**, on evidence nobody had looked for.
>
> ⚠️ **C-9 narrowed from four requirements to two — FR-10 and FR-18.** SRS **Table 36** names a
> specifying section for three of its four, and two of those sections state testable behaviour: FR-6 →
> §6.7, FR-17 → §6.7 and §8.4. **Neither had ever been checked.** `docs/open-questions.md` carries the
> reasoning and stays the authority.

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
| **9** | Outputs and distribution | ✅ COMPLETE | A timetable that can leave the screen — print and CSV, all four views | FR-10 *(software; tick held by C-9)* | `004f38d` |
| **10** | Requirement closure by test | ✅ COMPLETE | Five requirements closed on the supervisor's own wording; **10 ✓ → 15 ✓** | FR-3 · FR-4 · FR-7 · FR-14 · FR-16 → ✓ | `375c220` |
| **11** | Administrative surfaces | 🔵 **NEXT — not started** | The screens whose mechanisms already exist | FR-9 · FR-11 · student view | — |
| **12** | Data management | ⏳ PLANNED | A second institution becomes possible | FR-1 | — |
| **13** | Examination session | ⬜ CONDITIONAL | Exam timetabling (*was increment 2*) | FR-20 | — |
| **14** | Weight adjustment | ⬜ CONDITIONAL | Learn weights from recorded comparisons (*was increment 2*) | FR-21 | — |

🔴 **Cross-phase blocker — C-9, now two requirements: FR-10 and FR-18.** Neither has an acceptance
standard anywhere in the specification, and **FR-18's central figure — what "occupancy" means — is
undefined in every document**. This blocks *ticks*, never *software*. It is a gate, not a phase.
⚠️ **It listed four requirements until 2026-08-10.** SRS **Table 36** names a specifying section for
three of them and two of those sections state testable behaviour — FR-6 → §6.7, FR-17 → §6.7 and §8.4 —
so both left C-9. **Table 36 had never been checked**, because C-9 framed the question as a missing
§3.2 row. `docs/open-questions.md` carries the full reasoning.

### Requirement coverage — all 25, each mapped to exactly one closing phase

Written out so nothing can be lost between views. **"Closing phase"** is the phase that takes the
requirement to `✓`, which is not always the phase that built it.

| FR | Requirement | Status | Built in | Closes in | Held by |
|---|---|---|---|---|---|
| FR-1 | Load and manage department data | — | — | **12** | not started |
| FR-2 | Teacher declares availability | ✅ | 4 | **8** | — |
| FR-3 | Generate respecting H1–H12 | ✅ | 2 | **10** | — |
| FR-4 | Improve quality within a time limit | ✅ | 3 | **10** | — |
| FR-5 | Several candidates, each scored | ✅ | 3 | **6** | — |
| FR-6 | Order candidates by score | WIP | 3 | **unscheduled** | ✅ criterion found (SRS §6.7); **no acceptance test** |
| FR-7 | Display by teacher, group, room | ✅ | 4 | **10** | — |
| FR-8 | Report rules in conflict | WIP | 5 | 🔴 supervisor | statement ≠ criterion |
| FR-9 | Configure the calendar | WIP | 5–6 | **11** | screen not built |
| FR-10 | Print or export a view | WIP | **9** | 🔴 **C-9** | no acceptance standard; software complete |
| FR-11 | Authenticate and restrict by role | WIP | 5 | **11** | account management |
| FR-12 | Verify data before solving | ✅ | 5 | **6** | — |
| FR-13 | Candidates under distinct profiles | ✅ | 3 | **8** | — |
| FR-14 | Compare two candidates | ✅ | 4 | **10** | — |
| FR-15 | State each criterion's contribution | ✅ | 3 | **6** | — |
| FR-16 | Recommend one candidate | ✅ | 3 | **10** | — |
| FR-17 | Signal a dominated candidate | ✅ | 3–6 | **10 (audit)** | — |
| FR-18 | Display room occupancy | WIP | 4 | 🔴 **C-9** | ⚠️ **the occupancy figure is undefined**; no test of any kind |
| FR-19 | Record every run with its trace | ✅ | 5 | **6** | — |
| FR-20 | Examination session timetable | — | — | **13** | conditional |
| FR-21 | Adjust weights from comparisons | — | — | **14** | conditional |
| FR-22 | Explain a candidate's quality | ✅ | 7 | **7** | — |
| FR-23 | Regenerate from a recommendation | ✅ | 7 | **7** | — |
| FR-24 | Answer a question in ordinary language | ✅ | 7 | **8** | — |
| FR-25 | Produce a readable report | ✅ | 7 | **7** | — |

**Totals: 16 ✅ · 6 WIP · 3 not started = 25.** Of the 6 WIP, **none lacks working software**: **2 wait
on C-9** (FR-10, FR-18), 2 need a screen over a working mechanism (FR-9, FR-11), 1 needs its statement
reworded (FR-8), and 1 needs only an acceptance file (FR-6).

⚠️ **FR-6 is the only requirement in the project waiting on a test, and it is a small one.** Phase 10
emptied that group; the pre-Phase-11 audit put one requirement back into it by *unblocking* FR-6 rather
than by leaving it under C-9. `DefaultRanker.rank()` implements SRS §6.7's two sentences and
`GET /runs/{id}/candidates` returns that order — covered by `integration/test_api_runs` and
`unit/test_portfolio`, but **not** by an acceptance file. **It is unscheduled**: assigning it to a phase
is the project owner's call.

✅ **FR-17's row was the one open disagreement between this table and
[`docs/open-questions.md`](open-questions.md), and it is settled.** This table called FR-17 C-9-blocked
while the stated authority named only three requirements — a divergence of one that would have grown
every time either file was counted. The audit of 2026-08-10 found why the authority was right: **SRS
Table 36 maps FR-17 to §6.7 and §8.4, and both state the behaviour in the supervisor's own words**, so
FR-17's criterion was never project-authored and the question "may a project-authored criterion tick a
requirement?" never applied to it. **FR-17 is `✓`.** The question itself remains unasked and unanswered
— no requirement now depends on it.

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

#### Independently verified at closure, 2026-08-10

A separate audit session re-ran everything and drove the running application against the real reference
run (`21887fab4ed6`, 3 candidates). **What a test suite could not establish, and this did:**

| Check | Result |
|---|---|
| **The file matches the screen** | Rendered grid cells parsed out of the DOM and compared with the exported rows, as sets: **6 = 6, identical, nothing on only one side** |
| **A two-period session is not double-counted** | On a TP subgroup: **16 file rows = 16 rendered session cells**, while the `Périodes` column sums to **20 = 16 + 4 continuation cells**. One row per session, and the true occupancy still recoverable |
| **Print actually inverts** | The `@media print` rules lifted into screen media and computed styles read back: nav, controls, outputs bar and view tabs `flex/block → none`; the print header `none → block`; the grid survives as `table` |
| **Provenance follows the selection** | Switching to candidate 2 moved the header to `…-cand-3`, `teacher-favouring`, `80,58 / 100` — matching the dropdown exactly |
| **All four views** | Correct print title, filename, header row, run id, seed and all **7** weights on each |
| **No new attack surface** | **19 endpoints before and after**; `export.ts` imports only `model` and `types/domain` and performs **no I/O**. The export re-serialises what the user was already served, so it inherits the view's permissions exactly and grants nothing new |

⚠️ **What that last row does *not* say.** `GET /runs/{id}` takes any authenticated user, so any signed-in
account can read any run — **a Phase 4/5 property, unchanged by Phase 9**, and not FR-10's to fix. The
export makes taking the data away *easier*; it does not make it *permitted*.

### Phase 10 — Requirement closure by test ✅ *(2026-08-10)*

**FR-3, FR-4, FR-7, FR-14 and FR-16 reached `✓`. The count went 10 → 15 of 25.** No product behaviour
was changed: the phase added 35 backend tests and 18 frontend ones, and touched one source file — a
comment.

**Research result — the phase's premise was wrong, and checking it is what made the work correct.**
The brief said these five were held "only because no acceptance test exists against their criterion".
Four of them had **no criterion**: SRS §8.6 Table 35, which `docs/testing-strategy.md` §4 transcribes,
has no row for FR-4, FR-7, FR-14 or FR-16. Writing tests without noticing would have meant this project
inventing the promises it then declared itself to have met — the exact failure Phase 9 refused for
FR-10.

**What made them closable anyway is an asymmetry with C-9 that nobody had written down.** FR-4, FR-7,
FR-14 and FR-16 each have a **detailed SRS §3.2 input/processing/output row** written by the
supervisor. C-9's four have neither kind of row. So the §3.2 row is the promise, it was quoted verbatim
at the head of each acceptance file, and all four rows were transcribed into
`docs/testing-strategy.md` §4 so no session needs the PDF again. **C-9 is untouched.**

⚠️ **That last sentence was true on the day and is now superseded** — kept because it records what
Phase 10 believed. The **pre-Phase-11 audit of 2026-08-10** narrowed C-9 to FR-10 and FR-18 by checking
**SRS Table 36**, which Phase 10 never opened: it names a specifying section for three of C-9's four.

**Two defects found, both by writing the test rather than by reading the code:**

1. **`acceptance/test_fr03` named two rules by the wrong code.** The room-type check was called H5 (it
   is **H4**) and the availability check H7 (it is **H6**), against `constraint_catalogue.csv`. It also
   covered seven of twelve rules while carrying a claim about all twelve — a reader auditing the twelve
   would have ticked rules that were never checked. It now re-derives **eleven of twelve** from the
   placements, including H2 and H11 which the solver posts for neither; H10 is vacuous on this instance
   and **asserts that it is** rather than assuming it.
2. **`ComparisonScreen.tsx` still described C-15 as open**, three days after C-15 was resolved *by
   refuting that very diagnosis*. A stale comment on the screen FR-14 was being closed against.

⚠️ **One test was found unable to fire, and it is recorded rather than renamed.** FR-16's Table 17 says
"selection of the first, **then verification of dominance**" — and deleting the `dominance()` call from
`recommend()` left every acceptance test green. That gap **cannot** be closed at the API: the verdict
for a top-ranked candidate is provably always null, so no run distinguishes a performed check from a
skipped one. `unit/test_recommendation` is what establishes the machinery, and the acceptance test's
docstring says so plainly instead of claiming more than it proves.

**Every new assertion was verified to fire** by mutating the source first — eight backend mutations,
three frontend. The FR-3 additions were exercised against deliberately broken timetables, since a
mutation there would have cost a 150-second solve each.

---

## 4 · Current phase — Phase 11, Administrative surfaces

**Status: 🔵 NEXT — not started, and opening it needs the project owner's approval.** Phase 10 closed
on 2026-08-10.

### Why this phase is next
Two requirements have a working, tested *mechanism* and no *screen*: FR-9 (a closed half-day already
takes effect through `Slot.is_open`, and `acceptance/test_fr09` proves it) and FR-11 (accounts are
provisioned by a seed command, which C-18 records as a development tool and not a provisioning
mechanism). Plus the student view: the role is seeded and has no screen.

### What no phase can do
**C-9 blocks two ticks and no software: FR-10 and FR-18.** Phase 9 is the proof that building the
software does not move them — it delivered FR-10 in full and the count did not change. **The supervisor
must supply an acceptance standard**, and for FR-18 something more basic: **a definition of what its
occupancy figure is**, which no document contains. ⚠️ **This said "three ticks … FR-6, FR-10 and FR-18"
until 2026-08-10**; FR-6 left C-9 when SRS Table 36 was finally checked and found to name §6.7.

---

## 5 · Current and future phases in detail

### Phase 11 — Administrative surfaces 🔵 NEXT — **THE HANDOFF**

**This subsection is written for a session that has just run `/clear` and knows nothing.** Read
`docs/dashboard.md` first, then this. Everything below was verified against the code on 2026-08-10.

**Mission.** Give an administrator and a student the surfaces SRS Table 2 says they have. Three
capabilities whose *decision mechanisms* are already built and tested.

⚠️ **Phase 11 is NOT frontend-only, and assuming it is would be the phase's first mistake.** Verified
2026-08-10: the API has **19 endpoints and not one of them writes a slot, a holiday or an account.**
The write endpoints are availability (`PUT`), sign-in, run creation, regeneration, publication and the
assistant question — that is all. `GET /instance` is **read-only**, and `api/deps.py::get_instance`
loads the instance **from the 13 CSVs on disk, `lru_cache`d for the process**. So an administration
screen needs *new backend surface and a persistence story for calendar edits*, and neither exists.
**That is the largest single unknown in this phase — size it before promising a date.**

If you find yourself changing the solver, the analysis layer or the run pipeline, stop — that is not
this phase.

**Requirements: FR-9, FR-11, plus the student view.**

#### What already exists — do not rebuild it

| | Built and tested | Where |
|---|---|---|
| **FR-9 mechanism** | Closing a half-day is `Slot.is_open = 0`; H9 removes those slots from every session's domain. **Acceptance-tested against the real solver**: `acceptance/test_fr09.py` closes Wednesday afternoon by setting that flag **and nothing else**, and no placement in any candidate occupies a closed slot | `solver/constraints/domain_pruned.py` (H9), ADR-003, invariant 7 |
| **FR-11 mechanism** | Token authentication, role checks on every request, the teacher taken **from the token**. **Tested with real tokens, no dependency override**: `integration/test_rbac.py` (19) and `acceptance/test_fr11.py` (7) | `core/security`, `api/deps`, `api/routers/auth`, `features/auth` |
| **Accounts today** | `uv run python -m optiedt.services.seed` creates one person in charge, one administrator, one student and one account per teacher. **C-18 records this as a development tool, never a provisioning mechanism**, and it refuses to run if any account exists | `services/seed.py`, `unit/test_seed.py` (8) |
| **The student's data path** | `GET /runs/{id}` and the candidate reads already serve a timetable; `features/timetable` renders it by teacher, group and room, and prints and exports it (FR-7 ✓, FR-10 software) | `features/timetable/` |

#### What is missing — the actual work

1. **An administration screen.** `frontend/src/features/admin/` contains **one file: `.gitkeep`**. There
   is no route for it in `App.tsx`, which today routes exactly five paths: `/disponibilites`,
   `/generation`, `/emplois-du-temps`, `/comparaison`, `/publications`.
2. **Calendar administration (FR-9) — and the endpoint under it.** A surface that sets `Slot.is_open`,
   holidays and the shortened-day window. ⚠️ **No endpoint writes a slot today, and the instance is
   loaded from CSV files and cached for the process.** So this needs a decision about *where an edited
   calendar lives*: a database table read at run assembly (the shape FR-2's declarations already use —
   see `services/availability.apply_declarations`), or edits to the instance files. **The declarations
   precedent is the strongest evidence in the repository**: FR-2 faced the same problem and solved it by
   layering stored declarations over a pristine loaded instance, deliberately, "so a declaration can be
   withdrawn" (`api/deps.py`). Follow it unless there is a reason not to.
3. **Account management (FR-11) — and the endpoints under it.** SRS **Table 2** gives the administrator
   *"Management of the accounts and of the calendar"* — one actor, both surfaces, which is why they are
   one phase. There is no account endpoint beyond `POST /auth/token` and `GET /auth/me`.
4. **A student view.** SRS Table 2 gives the student *"Read on the timetable of the group"*. The CdC
   adds printing: *"Students to consult and print the timetable of their group"*. The role exists in
   `UserRole`, is seeded, and **has no route and no screen**.

#### Decisions a fresh session must not take alone

⚠️ **Where account management belongs is genuinely contested inside this repository, and it is not a
session's call.** **C-18** says the administrator's account-management right *"stays unimplemented and
belongs with FR-1's data management"* — which is **Phase 12**. This roadmap puts it in Phase 11. The
strongest reading of the evidence: **SRS Table 2 pairs accounts with the calendar under one actor**, and
C-8 already settled that Table 2 wins where prose disagrees — so accounts belong with the administration
screen, and C-18's sentence was a scheduling remark made under Phase 5's budget, not a scope ruling.
**Recorded as a reading, not a decision.** Put it to the project owner when Phase 11 opens.

#### Constraints — what Phase 11 must not touch

- **The solver, the analysis layer, the objective and the run pipeline.** No placement is written
  outside `solver/` (invariant 2), and the analysis layer may not import the solver (invariant 1).
- **Invariant 7 / ADR-003.** A closed half-day is **configuration**: it sets `slot.is_open = 0` and H9
  does the rest. **Adding a CP-SAT constraint for a holiday or a closed Saturday is a bug**, and FR-9's
  acceptance test asserts "with no code change" by holding the catalogue to exactly H1–H12.
- **The eleven `import-linter` contracts.** Never relax one to make a change compile.
- **`OPTIEDT_SECRET_KEY`.** Phase 8 made production start-up refuse the published default. Do not weaken
  that guard to make an admin screen convenient.
- **FR-1 (department data import) is Phase 12**, not this one. An account screen must not grow into a
  data-management screen.
- **FR-6's acceptance file is unscheduled work, not Phase 11's.** It is small and tempting; it is also
  not what this phase is for.

#### Risks

- **A calendar write path is new surface.** Changing `Slot.is_open` changes what every future run can
  produce. ⚠️ **On this instance it is tight**: `test_fr09` records that any half-day closure takes
  `Lab_Info` to **exactly 100.0 %** of its two-period windows — a solution exists only if a perfect
  packing does. An administration screen that lets someone close two half-days can make the instance
  infeasible, and the honest response is FR-12's pre-analysis, not a refusal to save.
- **Account management touches authentication.** `integration/test_rbac.py` must keep using real tokens.
- **`GET /runs/{id}` takes any authenticated user** — recorded at Phase 9's audit and still true. A
  student view that reads a run inherits that. **Phase 11 is where it becomes a question worth asking**,
  because a student is the first role that should *not* see everything.

**COMPLETE when** an administrator can close a half-day and manage accounts through the interface, a
student can reach their own group's timetable, and each is covered the way this project covers a
requirement: an acceptance file quoting its criterion, plus display tests for what only a rendering test
can establish.

**Validation.** `scripts/run-checks.ps1` green across its nine steps; `scripts/run-acceptance.ps1` green
(**16–22 min**, quote the range or none); new tests **verified to fire** by mutating the source before
being relied on — the standard Phases 9 and 10 both used.

**Documentation to update on completion.** `docs/dashboard.md` (state), `docs/status.md` (detail),
`docs/requirements-traceability.md` (any status change — it is the authority),
`docs/testing-strategy.md` §4 (any new criterion, quoted), and this file's phase table and coverage
table.

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
met.** ADR-010 commits the assistant to increment 1 and it is built. Phases 1–10 are complete.

> **By the project's own stated gate, the mandatory work is done.**

### 🟡 Strongly recommended before submission
| Item | Phase | Why |
|---|---|---|
| ~~**FR-10 export/print**~~ | 9 | ✅ **DELIVERED 2026-08-10.** Print and CSV on all four views. ⚠️ The requirement is still `WIP` — C-9 holds the tick, not the software |
| ~~**Acceptance tests for 5 requirements**~~ | 10 | ✅ **DELIVERED 2026-08-10.** 10 `✓` → 15 `✓`, and no new software. Four of the five were verified against their **SRS §3.2** row, Table 35 having no row for them |

**Nothing remains on this list.** Every hold on a requirement is now external to the code — see §2's
coverage table.

### 🔵 Optional — improves the product, not required by the gate
Phase 11 (administrative surfaces) · Phase 12 (FR-1 data management) · the six unscheduled usability
findings in `status.md`.

### 🔴 Supervisor-dependent — **you cannot close these alone**
**C-9, now two requirements.** **FR-10** and **FR-18** have no acceptance standard in any document, and
**FR-18's central figure — what "occupancy" means — is defined nowhere**. Blocks **two ticks** and no
software. ⚠️ **It listed four until 2026-08-10**; FR-6 and FR-17 left it once SRS Table 36 was checked.
**FR-8's statement** was never reworded to match its criterion, which is why it stays `WIP`.
⚠️ **FR-17 is no longer on this list** — SRS §6.7 and §8.4 state its behaviour in the supervisor's own
words, so no ruling was needed and none was taken.

### ⬜ Out of scope unless time permits
Phases 13–14. PPM defines increment 2 as **"conditional on remaining time"**, and
`docs/ai-integration.md` records **natural-language constraint entry as not undertaken** — it would need
a solver-validation harness that does not fit the project.

---

## 7 · Progress — several honest measures

| Measure | Value | Note |
|---|---|---|
| **Phases complete** | **10 of 14** (71 %) | 10 of 12 (83 %) excluding the two conditional phases |
| **Acceptance criteria** | **9 of 9 (100 %)** | The specification's actual gate |
| **Requirements `✓`** | **16 of 25 (64 %)** | ⚠️ Still understates reality — see below. **10 → 15 in Phase 10, → 16 at the pre-Phase-11 audit** |
| **Open questions** | **19 of 20 resolved** | One remains: C-9, supervisor-dependent |
| **Tests** | **552 backend + 99 frontend** | 441 fast + 67 solver + 44 database. ⚠️ **Derive these**: `uv run pytest --collect-only -q` and `npm run test` |
| **Mandatory work remaining** | **None** | By the nine-criteria gate |

⚠️ **Why 64 % still understates it.** Of the 9 requirements not `✓`, **6 have working software** and
3 are not started. The 6 are held by: no acceptance standard the supervisor wrote — C-9 (2: FR-10,
FR-18), an unbuilt screen over a working mechanism (2: FR-9, FR-11), a statement never reworded to match
its criterion (1: FR-8), and **one acceptance file that has simply not been written** (1: FR-6).

⚠️ **Phase 9 remains the clearest illustration of the gap.** It delivered a whole requirement's
software and moved the `✓` count by **zero**. Anyone quoting a percentage should say what it measures.

**If a single figure is wanted, use this one and say how it is computed:**

> **~91 % of the project as scoped.** = Phases 1–10 complete (10/12 non-conditional phases = 83 %),
> weighted by the fact that the **acceptance gate is 100 % met** and the two remaining non-conditional
> phases are refinement rather than core capability. Phases 13–14 are excluded as conditional by PPM.

**Realistic remaining effort:** Phase 11 ≈ 2 days · Phase 12 ≈ 3–5 days · Phases 13–14 ≈ 7 days if
undertaken. *(Phase 10 was estimated at ≈ 1 day and took one session.)*

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
