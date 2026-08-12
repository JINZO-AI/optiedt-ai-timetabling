# Project roadmap — one continuous sequence of phases

**This is the practical tracking view.** One question, one answer: *what phase are we in?*

> **Phase 13 — Examination session. ✅ COMPLETE 2026-08-12.** Phases 1–13 are complete. **Phase 14
> (FR-21, weight adjustment) remains CONDITIONAL** and is the only phase left; opening it is the
> project owner's call, not a session's.
>
> ⚠️ **Phase 13 was opened after a gate that re-anchored the work against the original product
> vision.** ITC-2007 Track 1 was deliberately **not** downloaded: it is benchmark evidence for the
> examination engine, not a product requirement, and treating it as one would have spent half the
> phase outside the product (`docs/testing-strategy.md` §1 keeps that distinction).
>
> ✅ **23 of 25 requirements are `✓`, and every open question is resolved.** Phase 10 took the count from
> 10 to 15; the pre-Phase-11 audit added FR-17; Phase 11 added FR-9 and FR-11; closing C-9 on
> 2026-08-11 added FR-6, FR-10 and FR-18; Phase 12 added FR-1; and **Phase 13 added FR-20**.
>
> ⚠️ **FR-20's criterion was supervisor-written too — SRS §3.2 Table 19 — and was found only in Phase 13.
> That is the THIRD requirement carried as unspecified while its row sat in §3.2**, after C-9's four and
> FR-1. The arithmetic that finds them has been on the page since Phase 10.
>
> ⚠️ **FR-1's criterion was supervisor-written all along — SRS §3.2 Table 4 — and this repository had
> recorded it as unspecified for four phases.** The arithmetic that revealed it was already on the page:
> §3.2 covers 21 requirements and is absent for exactly C-9's four, so the twenty-first is FR-1. **A new
> project decision, C-22 / ADR-012, covers only what the specification is silent about**: what a
> *second* load does to declarations and closures already stored.
>
> ✅ **C-9 — the last open question — is CLOSED**, in two stages and both times by falsifying its own
> premise. **SRS Table 36** gave FR-6 and FR-17 supervisor-written criteria nobody had looked for. Then
> **C-4, in the same file, was found already to define FR-18's occupancy figure** — the claim that no
> document defined it was wrong. `docs/open-questions.md` carries the reasoning and stays the authority.
> ⚠️ **FR-10's and FR-18's criteria are project decisions, not supervisor wording**, labelled as such
> wherever cited and therefore reversible.

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
| **9** | Outputs and distribution | ✅ COMPLETE | A timetable that can leave the screen — print and CSV, all four views | FR-10 *(software; ticked 2026-08-11 when C-9 closed)* | `004f38d` |
| **10** | Requirement closure by test | ✅ COMPLETE | Five requirements closed on the supervisor's own wording; **10 ✓ → 15 ✓** | FR-3 · FR-4 · FR-7 · FR-14 · FR-16 → ✓ | `375c220` |
| **11** | Administrative surfaces | ✅ COMPLETE | The screens whose mechanisms already existed, and the endpoints under them; **16 ✓ → 18 ✓**. Followed by **C-9's closure — 18 ✓ → 21 ✓** | FR-9 · FR-11 → ✓ · student view · then FR-6 · FR-10 · FR-18 → ✓ | *derive it: `git log --oneline`* |
| **12** | Data management | ✅ COMPLETE | A department's data can be supplied, verified and recorded through the application; **21 ✓ → 22** | FR-1 → ✓ | *derive it: `git log --oneline`* |
| **13** | Examination session | ✅ COMPLETE | An examination timetable under X1-X4 with SX1, reachable and tested; **22 ✓ → 23** | FR-20 → ✓ | *derive it: `git log --oneline`* |
| **14** | Weight adjustment | ⬜ CONDITIONAL | Learn weights from recorded comparisons (*was increment 2*) | FR-21 | — |

✅ **~~Cross-phase blocker — C-9~~ — RESOLVED 2026-08-11. The paragraph below is what it said.**

🔴 ~~**Cross-phase blocker — C-9, now two requirements: FR-10 and FR-18.**~~ Neither has an acceptance
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
| FR-1 | Load and manage the data of the department | ✅ | **12** | **12** | — ⚠️ *replacement rule is a project decision (C-22)* |
| FR-2 | Teacher declares availability | ✅ | 4 | **8** | — |
| FR-3 | Generate respecting H1–H12 | ✅ | 2 | **10** | — |
| FR-4 | Improve quality within a time limit | ✅ | 3 | **10** | — |
| FR-5 | Several candidates, each scored | ✅ | 3 | **6** | — |
| FR-6 | Order candidates by score | ✅ | 3 | **11 (C-9)** | — |
| FR-7 | Display by teacher, group, room | ✅ | 4 | **10** | — |
| FR-8 | Report rules in conflict | WIP | 5 | 🔴 supervisor | statement ≠ criterion |
| FR-9 | Configure the calendar | ✅ | 5–6 | **11** | — ⚠️ *shortened-day shift not carried into the timetable views; see §5* |
| FR-10 | Print or export a view | ✅ | **9** | **11 (C-9)** | — ⚠️ *criterion is a project decision* |
| FR-11 | Authenticate and restrict by role | ✅ | 5 | **11** | — |
| FR-12 | Verify data before solving | ✅ | 5 | **6** | — |
| FR-13 | Candidates under distinct profiles | ✅ | 3 | **8** | — |
| FR-14 | Compare two candidates | ✅ | 4 | **10** | — |
| FR-15 | State each criterion's contribution | ✅ | 3 | **6** | — |
| FR-16 | Recommend one candidate | ✅ | 3 | **10** | — |
| FR-17 | Signal a dominated candidate | ✅ | 3–6 | **10 (audit)** | — |
| FR-18 | Display room occupancy | ✅ | 4 | **11 (C-9)** | — ⚠️ *criterion is a project decision* |
| FR-19 | Record every run with its trace | ✅ | 5 | **6** | — |
| FR-20 | Examination session timetable | ✅ | **13** | **13** | — ⚠️ *derivation rule is a project decision (C-23)* |
| FR-21 | Adjust weights from comparisons | — | — | **14** | conditional |
| FR-22 | Explain a candidate's quality | ✅ | 7 | **7** | — |
| FR-23 | Regenerate from a recommendation | ✅ | 7 | **7** | — |
| FR-24 | Answer a question in ordinary language | ✅ | 7 | **8** | — |
| FR-25 | Produce a readable report | ✅ | 7 | **7** | — |

**Totals: 23 ✅ · 1 WIP · 1 not started = 25.** ⚠️ **The single `WIP` is FR-8, and it is a decision
rather than an omission**: promoting it would need its criterion narrowed to match what the software
cannot do — on the C-13 contiguity shape CP-SAT proves no infeasibility — and this project refuses that
direction. **The one not started is FR-21, in the conditional Phase 14** — so
**every non-conditional requirement is now either `✓` or held by a wording this project will not
narrow.**

✅ ~~**FR-6 is the only requirement in the project waiting on a test.**~~ **Superseded: `test_fr06`
was written when C-9 closed on 2026-08-11 (8 tests) and FR-6 is `✓`.** The paragraph is kept because it
records what was believed on the day. **No requirement is now waiting on a test.**

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

⚠️ **FR-10 is `WIP`, not `✓`, and that is the correct outcome** *(true on 2026-08-10, superseded 2026-08-11 when C-9 closed and FR-10 reached `✓`; kept because it records what Phase 9 concluded)* — C-9 leaves it with no criterion to
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

## 4 · Current phase — none open; Phase 14 remains conditional

**Status: Phase 13 closed on 2026-08-12.** **Opening Phase 14 (FR-21) is the project owner's call**,
and PPM makes it conditional on remaining time. ⚠️ **FR-21 has no counterpart in the project's own
notes**: the optimization loop those notes describe — the administrator accepts a suggestion and the
application re-runs — is FR-23, delivered in Phase 7. Weight LEARNING from recorded comparisons is an
SRS requirement only, and `Comparison` is still a domain type nothing instantiates.

### Why Phase 12 was last, and what it changed
**FR-1 was the largest genuine gap and the only requirement left with no software at all** outside the
two conditional phases. The only way into the application was 13 hand-authored CSVs, so no second
institution could use it. Phases 10 and 11 were the right order before it: the model and the surfaces
around it had stopped moving, so the import path was built on something stable.

### What no phase can do
✅ **Nothing. C-9 — the last thing no phase could do — was closed on 2026-08-11**, and the paragraph
below is what it said until then.

~~**C-9 blocks two ticks and no software: FR-10 and FR-18.** The supervisor must supply an acceptance
standard, and for FR-18 something more basic: a definition of what its occupancy figure is, which no
document contains.~~ ⚠️ **Both halves of that were wrong.** FR-18's figure was defined in **C-4** all
along; FR-10's and FR-18's criteria were adopted as **project decisions** from specification text the
CdC and SRS do contain. **Phase 9 is still the proof that building software does not move a tick** — it
delivered FR-10 in full and the count did not change; what moved it was writing down the promise and
testing against it.

---

## 5 · Current and future phases in detail

### Phase 11 — Administrative surfaces ✅ **COMPLETE 2026-08-11**

**Mission, as it was written.** Give an administrator and a student the surfaces SRS Table 2 says they
have — three capabilities whose *decision mechanisms* were already built and tested. **Delivered:**
FR-9 and FR-11 are `✓`, and the student has a screen.

⚠️ **The handoff's central warning was right, and it is what shaped the phase: this was NOT
frontend-only.** At its opening the API had **19 endpoints and not one wrote a slot, a holiday or an
account**, and `api/deps.py::get_instance` loaded the instance from the 13 CSVs, `lru_cache`d for the
process. Phase 11 added **six endpoints** and a persistence story for calendar edits.

#### What was delivered

| | Delivered | Where |
|---|---|---|
| **Calendar administration (FR-9)** | `GET`/`PUT`/`DELETE /api/calendar`, administrator only. Closures, the holiday list and the shortened-day window, **layered over the pristine instance** and applied at run assembly | `services/calendar.py`, `api/routers/calendar.py`, `features/admin/CalendarEditor.tsx` |
| **Account management (FR-11)** | `GET`/`POST`/`DELETE /api/accounts`, administrator only — **what C-18 recorded as owed** | `api/routers/accounts.py`, `features/admin/AccountsPanel.tsx` |
| **The student's surface** | `GET /api/me/timetable` — the **published** timetable of the account's own group, filtered on the server, with print and CSV reused from FR-10 | `services/timetables.py`, `api/routers/student.py`, `features/student/` |
| **Persistence** | `calendar_overrides` (one row, the whole calendar) and `users.group`; one migration, `SqlCalendarStore` under the same store contract as the other four | `db/models.py`, `db/repositories.py`, `migrations/versions/e62aaacddedf_*` |
| **Authorisation** | The run, candidate, comparison, assistant and availability endpoints admit the three roles that work on timetables and **refuse the student** | `api/deps.WorksOnTimetablesDep` |

#### The decisions taken, and by whom

- ⚠️ **Where account management belongs was contested inside this repository, and the project owner
  settled it.** **C-18** said the administrator's account-management right *"stays unimplemented and
  belongs with FR-1's data management"* — Phase 12 — while this roadmap put it in Phase 11. **The
  project owner opened Phase 11 naming FR-11 among its requirements**, which is the ruling the handoff
  asked for. The reading the handoff recorded holds: **SRS Table 2 pairs accounts with the calendar
  under one actor**, C-8 already settled that Table 2 wins where prose disagrees, and C-18's sentence
  was a scheduling remark made under Phase 5's budget rather than a scope ruling.
- **Where an edited calendar lives: a database table, layered over a pristine instance** — the shape
  FR-2's declarations already use, which the handoff named as the strongest evidence in the repository.
  It was followed for the reason `services/availability.py` gives: an edit that is layered can be
  withdrawn, and `DELETE /api/calendar` is that withdrawal.
- **A calendar that leaves no room for a timetable is saved, not refused.** The handoff's risk note
  said the honest response is FR-12's pre-analysis, not a refusal to save; refusing would also put a
  feasibility judgement outside the solver. `test_the_pre_analysis_measures_the_week_the_administrator_left`
  is that decision as a test.

#### ⚠️ The one limitation, recorded rather than absorbed

**ADR-003 gives the shortened-day window one effect — displayed and printed hours — and Phase 11
delivers the configuration but not that effect everywhere.** The window is stated, validated, persisted
and served, and the administration screen shows the hours it produces; **the timetable views and the CSV
export still print the ordinary hours.** Nothing in Table 35 or §3.2 asks for more, and FR-9's criterion
is exclusively about closing a half-day — but a department that sets a Ramadan window and prints a
timetable will see 08:30. **Carrying the shift into the timetable views is unscheduled work and the
project owner's call**; it is listed in `docs/status.md` rather than left to be discovered.

#### What the phase did not touch

The solver, the analysis layer, the objective and the run pipeline; the eleven `import-linter`
contracts (**11/11 kept throughout**); ADR-003's mechanism — the constraint catalogue still holds
exactly H1–H12 and `test_fr09` asserts it; `OPTIEDT_SECRET_KEY`'s production guard; FR-1, which is
Phase 12. **FR-6's acceptance file remains unwritten and unscheduled**, as the handoff instructed.

#### Evidence

`acceptance/test_fr09.py` (15: 4 `solver`-marked, 11 through the administration API) ·
`acceptance/test_fr11.py` (20) · `acceptance/test_student_view.py` (12) · `unit/test_calendar.py` (16) ·
`unit/test_timetables.py` (11) · 18 store-contract tests over **both** stores ·
`CalendarEditor.test.tsx` (12) · `AccountsPanel.test.tsx` (8) · `StudentTimetable.test.tsx` (6).
**80 backend tests and 26 frontend.** ⚠️ **Every new assertion was verified to fire** — 11 backend
mutations and 6 frontend — and **two mutations survived on the first pass, both revealing a defective
test rather than defective code**: a holiday-withdrawal test with nothing to withdraw, and a
"never mutated" test comparing a dict to itself. Both were repaired and the mutations then failed them.

### Phase 12 — Data management ✅ **COMPLETE 2026-08-11**

**Mission, as it was written:** *"a second institution's data can be loaded, validated and solved
without editing files by hand."* **Delivered, and verified live**: a department dataset supplied as
eleven CSVs through the interface was recorded, served to every screen, and **solved by the real CP-SAT
engine — 212 placements over 43 teachers, COMPLETED in 212 s** on data that had never touched
`data/instance/`.

⚠️ **The scope warning held, and one line of it was the phase's main decision.** The brief said *"an
import path must not grow into a student information system"*. **SRS §4.1 settles it**: it enumerates
nine user interfaces, names the administration screen's contents to the item — accounts, holidays,
closed half-days, shortened-day period — and names **no** data-management form. So FR-1's *"files or
forms"* is a disjunction, the file half is what was missing, and no per-entity CRUD was built.

#### What was delivered

| | Delivered | Where |
|---|---|---|
| **Verification of types and references** | Every rejected line reported with its file, physical line number, column and value — in one pass, never one per attempt | `instance/validation.py` |
| **Recording** | `department_dataset`, one row holding the supplied **file texts**, one migration, `SqlDatasetStore` under the same store contract as the other five | `db/models.py`, `db/repositories.py` |
| **The surface** | `POST`/`GET`/`DELETE /api/dataset`, **person in charge only** (SRS Table 2, C-8), and a screen showing what is in force, what was refused and why | `api/routers/dataset.py`, `features/dataset/` |
| **Base resolution** | `base_instance()` — the imported dataset, else the reference files — beneath FR-9's and FR-2's layers, keyed by the store's revision so a stale read is not possible | `api/deps.py` |

#### The decisions taken, and by whom

- ⚠️ **The replacement rule is a PROJECT DECISION, and it is the only part of FR-1 that is** — **C-22**
  and **ADR-012**. The specification says how a dataset is loaded and is silent on what a *second* load
  does to the declarations and closures already stored. A replacement that would orphan either is
  refused; nothing is ever silently deleted. **The rest of FR-1 rests on the supervisor's own §3.2
  Table 4.**
- **`constraint_catalogue.csv` is refused, not ignored** — invariant 7. It is excluded by construction:
  the catalogue reaches `Instance.constraints` as a *parameter from the application*, so no supplied
  file has a path to it.
- **The dataset is stored as file texts, not as a serialisation of the entities** — one parse path, so
  a stored dataset cannot drift from what was verified, and eleven tables are not added to answer a
  question nobody asks.

#### ⚠️ Two limitations, recorded rather than absorbed

1. **A slot whose numeric index survives but whose meaning changes is undetectable.** Detecting it needs
   a slot identity the model does not have.
2. **No concurrency protection.** A declaration saved between the compatibility check and the write is
   not seen by the check. The repository has no locking anywhere and the specification asks for none.

#### What the phase did not touch

The solver, the analysis layer, the objective and the scoring; the eleven `import-linter` contracts
(**11/11 kept throughout**); `data/instance/` — **nothing writes to the reference files**, which is what
keeps `verify-instance.ps1` meaningful; the constraint catalogue; FR-8, which stays `WIP` by decision.

#### Evidence

`acceptance/test_fr01.py` (34) · `unit/test_dataset_validation.py` (45) · `unit/test_dataset.py` (16) ·
**12** store-contract tests over **both** stores · `DatasetPanel.test.tsx` (20). **107 backend tests and
20 frontend** — the collected backend total moved 647 → **754**, the frontend 142 → **162**, and the
acceptance suite 197 → **231 over 22 requirements**.

⚠️ **`test_fr01.py` was written WITHOUT `pytestmark = pytest.mark.acceptance` and was silently excluded
from `run-acceptance.ps1` for its first full run.** The script selects by the **marker**, not by the
directory, so the file sat in `tests/acceptance/`, passed under `run-checks.ps1`, and was absent from
the one report that answers *"is FR-1 verified against its criterion?"* — 197 selected where the
directory held 231. Caught by comparing the two counts rather than by any test failing, which is the
point: **a missing marker cannot fail.** The marker is now on the file with that reasoning beside it. ⚠️ **39 mutations run, 39 detected — but two survived the first pass and both revealed a
real gap**: a compatibility guard that could never fire (removed, not kept as decoration) and a missing
test that a *second* import replaces the first, which let a cache ignoring the store's revision pass.

### Phase 13 — Examination session ✅ **COMPLETE 2026-08-12**

**Mission:** FR-20 — the timetable of an examination session. Opened by the
project owner on 2026-08-12 after a gate that re-anchored the remaining work
against the original product vision rather than against this roadmap.

⚠️ **FR-20's criterion was supervisor-written all along.** **SRS §3.2, Table 19**
states it in full — input *"Examinations, students, rooms, period of the session
and supervisors"*, processing *"Construction of the model of section 6.8 then
solving"*, output *"One slot and one or more rooms assigned to each
examination"*. This repository had recorded FR-20 as unspecified. **Third time**:
after C-9's four (Phase 10) and FR-1 (Phase 12), and the same arithmetic would
have found it each time.

#### What was delivered

| | Delivered | Where |
|---|---|---|
| **The model (X1-X4, SX1)** | CP-SAT over SRS §6.8. X1 per individual student, X2 a capacity SUM, X3 by the domain of the variable, X4 per supervisor; SX1 minimised | `examination/solver.py` |
| **The inputs** | Derived from the instance — one examination per course, supervisor the CM teacher, period two calendar keys (**C-23, ADR-013**) | `examination/derive.py` |
| **Students** | `Instance.students` wired at last; the loader reads `students.csv` | `domain/instance.py`, `instance/loader.py` |
| **The surface** | `POST`/`GET /api/examinations`, person in charge only, **202 and poll** like `POST /runs` (ADR-005) | `services/examinations.py`, `api/routers/examination.py` |
| **The view** | SRS §5.5's *"calendar of the session by group and by room"*, both groupings | `features/examination/` |

#### ⚠️ R-6 was the supervisor's own words, not an inference

SRS §6.8: *"An examination may occupy several rooms at once, so the assignment
of the rooms becomes a sum of capacities and not the choice of a single room."*
The weekly `Placement` was **not** widened — `ExamPlacement` carries a tuple of
rooms and lives beside it. Two new import contracts (**13 kept**) keep the two
models from sharing a variable schema, both verified to fire.

#### ⚠️ Two findings from running the model rather than reading it

1. **X2 is a covering constraint with no cost, so the first working solve took
   every room** — 20 rooms, 882 seats, for 120 candidates. Satisfying X2 and
   useless: a room hosts one examination per slot, so that serialises the
   session. Room economy is now a secondary objective under SX1, documented as
   a mechanism rather than a requirement.
2. **Deleting X4 left the whole acceptance file green.** With 55 slots for 32
   examinations and SX1 spreading them, the solver avoids supervisor collisions
   whether or not X4 is posted. `unit/test_examination_solver.py` is the answer:
   sessions small enough that one rule is load-bearing, asserting
   **infeasibility** rather than placement, because infeasibility cannot pass by
   luck. **8 mutations, 7 detected**; the eighth is recorded in that file.

#### What the phase did not touch

The weekly solver, the analysis layer, the objective, scoring or ranking; FR-1's
eleven-file contract; the constraint catalogue (X1-X4 are not in it — SRS §6.8
keeps them separate, and invariant 7 makes the catalogue unimportable anyway);
FR-21, which stays conditional and unbuilt; ITC-2007 Track 1, which was **not
downloaded** — it is benchmark evidence, not a product requirement.

#### Evidence

`acceptance/test_fr20.py` (14: 8 `solver`-marked, X1-X4 each re-derived from the
placements a user obtains through the API) · `unit/test_examination_solver.py`
(14) · `ExamCalendar.test.tsx` (9). **28 backend tests and 9 frontend**
(collected: 754 → **782** backend, 162 → **171** frontend; the acceptance suite 231 → **245 over 23
requirements**, measured **25 min 36 s**).

### ~~Phase 13 — Examination session ⬜ CONDITIONAL~~ — the brief, kept
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
| ~~**FR-10 export/print**~~ | 9 | ✅ **DELIVERED 2026-08-10, and `✓` since 2026-08-11** when C-9 closed. ⚠️ **This cell said "still `WIP`" until Phase 13** — stale by two phases, in a table a reader consults for what remains |
| ~~**Acceptance tests for 5 requirements**~~ | 10 | ✅ **DELIVERED 2026-08-10.** 10 `✓` → 15 `✓`, and no new software. Four of the five were verified against their **SRS §3.2** row, Table 35 having no row for them |

**Nothing remains on this list.** Every hold on a requirement is now external to the code — see §2's
coverage table.

### 🔵 Optional — improves the product, not required by the gate
~~Phase 11 (administrative surfaces)~~ ✅ **DELIVERED 2026-08-11** — FR-9 and FR-11 are `✓`. ·
~~Phase 12 (FR-1 data management)~~ ✅ **DELIVERED 2026-08-11** — FR-1 is `✓`. · the six unscheduled
usability findings in `status.md` · **the shortened-day shift in the timetable views** (Phase 11's
recorded limitation).

**Nothing remains on this list either.** What is left is the two conditional phases and two recorded
limitations, none of which the acceptance gate asks for.

### ~~🔴 Supervisor-dependent~~ — ✅ **nothing remains here**
~~**C-9, now two requirements.**~~ **RESOLVED 2026-08-11.** It listed four until 2026-08-10; FR-6 and
FR-17 left once SRS Table 36 was checked, and FR-10 and FR-18 left when their criteria were adopted as
**project decisions** — FR-18's quantity having turned out to be defined already, in C-4. ⚠️ **A Table
35 row is still absent for FR-10 and FR-18 and none was invented**; both ticks are labelled and
reversible. **FR-8's statement** was never reworded to match its criterion, which is why it stays `WIP`
— **a decision, not a blocker**: narrowing it to fit the software is the one direction this project
refuses.
⚠️ **FR-17 is no longer on this list** — SRS §6.7 and §8.4 state its behaviour in the supervisor's own
words, so no ruling was needed and none was taken.

### ⬜ Out of scope unless time permits
Phase 14, and **ITC-2007 Track 1** — benchmark evidence for the examination engine, deliberately not undertaken in Phase 13 and belonging in `optiedt.validation` if ever taken up. PPM defines increment 2 as **"conditional on remaining time"**, and
`docs/ai-integration.md` records **natural-language constraint entry as not undertaken** — it would need
a solver-validation harness that does not fit the project.

---

## 7 · Progress — several honest measures

| Measure | Value | Note |
|---|---|---|
| **Phases complete** | **13 of 14** (93 %) | Phase 13 was opened by the project owner on 2026-08-12 and delivered; only Phase 14 remains conditional |
| **Acceptance criteria** | **9 of 9 (100 %)** | The specification's actual gate |
| **Requirements `✓`** | **23 of 25 (92 %)** | **10 → 15 in Phase 10, → 16 at the pre-Phase-11 audit, → 18 in Phase 11, → 21 when C-9 closed, → 22 in Phase 12, → 23 in Phase 13** |
| **Open questions** | **22 of 22 resolved** | ✅ **None open.** ⚠️ Several were project decisions from repository evidence rather than supervisor answers — `docs/open-questions.md` is the authority on which. **C-22 is the newest, and the only one answering a question the specification never raises** |
| **Tests** | **782 backend + 171 frontend** | ⚠️ **Derive these**: `uv run pytest --collect-only -q` and `npm run test` |
| **Mandatory work remaining** | **None** | By the nine-criteria gate |

⚠️ **Why 92 % still understates it.** Of the 2 requirements not `✓`, **1 has working software** —
FR-8, held by a statement this project deliberately refuses to narrow — and **the other is FR-21, which
is conditional and has no counterpart in the project's own notes**. ⚠️ **Nothing is held by a missing acceptance standard any more**: C-9 closed
on 2026-08-11, and FR-6, FR-10 and FR-18 are `✓`. **Every requirement the project committed to
delivering is delivered.**

⚠️ **Phase 9 remains the clearest illustration of the gap.** It delivered a whole requirement's
software and moved the `✓` count by **zero**. Anyone quoting a percentage should say what it measures.

**If a single figure is wanted, use this one and say how it is computed:**

> **100 % of the project as scoped, and the examination session on top of it.** = **all 12
> non-conditional phases complete plus Phase 13**, the **acceptance gate 100 % met**, and 23 of 25
> requirements `✓` with the only non-conditional exception (FR-8) held by a wording this project
> deliberately refuses to narrow rather than by missing software. Phase 14 is excluded as conditional
> by PPM.
>
> ⚠️ **"100 % as scoped" is not "nothing remains".** Two recorded limitations stand — the shortened-day
> shift in the timetable views, and FR-8's statement — plus six usability findings. None is required by
> the gate; all are the project owner's call.

**Realistic remaining effort:** Phase 14 ≈ 3 days if undertaken; nothing otherwise. *(Phase 13 was budgeted 4 days and took one session — the investigation that preceded it found FR-20 already specified in SRS Table 19, so no acceptance standard had to be invented. The same reason Phase 12 came in short.)*
*(Phase 10 was estimated at ≈ 1 day and took one session; Phase 11 at ≈ 2 days and took one session;
**Phase 12 was estimated at ≈ 3–5 days and took one session** — the estimate was the least accurate of
the three, and the reason is worth keeping: the investigation that preceded it found FR-1's criterion
already written in SRS Table 4, so no acceptance standard had to be invented.)*

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
