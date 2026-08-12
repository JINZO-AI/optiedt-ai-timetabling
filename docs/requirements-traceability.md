# Requirements traceability

FR-1 … FR-25 mapped to the module that implements each and the test that proves it.

**Update the Status column when you finish a requirement.** This table is how anyone answers "is FR-15
built?" without reading code.

Status: `—` not started · `WIP` in progress · `✓` implemented and tested

**Phase 6 M2 added the acceptance suite** — `backend/tests/acceptance/`, 42 tests over **FR-3, FR-5,
FR-11, FR-13, FR-15, FR-17 and FR-19**, each driven through the HTTP API because a requirement is `✓`
only once a user can *reach* it. ⚠️ **A passing acceptance test is necessary, not sufficient**: FR-13
still waits on **C-15**, FR-11 on account management and a `secret_key` that is not published in this
repository. *(FR-2's own reasons are both discharged as of 2026-08-07; **FR-13's and FR-11's are too**
— C-15 on 2026-08-07, account management in Phase 11.)* The suite is what makes those remaining reasons
the *only* ones.

✅ **The whole table was reviewed against evidence in one pass at M7**, as M2 promised — not row by row
as work landed, which is how a table acquires a count nobody can reproduce.

---

## Phase 13 — FR-20 closed by building it, 2026-08-12

**FR-20 reached `✓`. The count moved 22 → 23 of 25.** The last requirement with
no software outside the one that remains conditional.

⚠️ **FR-20's criterion was supervisor-written all along, and this file had no
record of it.** SRS §3.2 **Table 19** states it in full. The arithmetic that
would have revealed it was already on this page and in
`docs/testing-strategy.md` §4: §3.2 covers 21 requirements and is absent for
exactly C-9's four, so FR-20 has a row. **This is the third time a requirement
was carried as unspecified without checking §3.2 and Table 36** — after FR-1
(Phase 12) and C-9's four (Phase 10). The row is now transcribed verbatim in
`docs/testing-strategy.md` §4.

| | The supervisor's own words (SRS §3.2, Table 19) |
|---|---|
| **Input** | Examinations, students, rooms, period of the session and supervisors |
| **Processing** | Construction of the model of section 6.8 then solving |
| **Output** | One slot and one or more rooms assigned to each examination |

**What was built.** A parallel examination model: `ExamPlacement` carrying
`rooms: tuple[...]` beside the weekly single-room `Placement`, a CP-SAT model of
SRS §6.8's X1–X4 with SX1 as its objective, `POST`/`GET /api/examinations`
(person in charge only, 202-and-poll like `POST /runs`), and the calendar view
SRS §5.5 asks for, by group and by room. **`Student` was wired into `Instance`**
after four phases of deliberate exclusion — X1 is stated per individual student.

⚠️ **The derivation rule is a PROJECT DECISION and is labelled wherever cited** —
**C-23** and **ADR-013**. Three of FR-20's five stated inputs (examinations, the
period, supervisors) have no source: SRS Table 25 defines no Examination entity.
One examination per course, the supervisor the course's CM teacher, the period
two calendar keys — each settled on a measurement, not a preference.

⚠️ **A mutation survived and produced a whole test file.** Deleting X4 left
`acceptance/test_fr20.py` entirely green: with 55 slots for 32 examinations and
SX1 spreading them, the solver avoids supervisor collisions whether or not X4 is
posted, so the acceptance test proved that one optimal solution satisfied X4 and
not that X4 is enforced. `unit/test_examination_solver.py` is the answer —
instances small enough that one rule is load-bearing, asserting **infeasibility**
rather than placement, because infeasibility cannot pass by luck. **8 mutations
run, 7 detected**; the eighth is recorded in that file rather than hidden.

⚠️ **A real defect was found by running the model rather than reading it.** X2 is
a covering constraint with no cost, so the first working solve assigned **all
twenty rooms (882 seats) to a 120-candidate examination** — satisfying X2 and
serialising the whole session, since a room hosts one examination per slot. Room
economy is now a secondary objective under SX1, and it is documented as a
mechanism rather than a requirement.

---

## Phase 12 — FR-1 closed by building it, 2026-08-11

**FR-1 reached `✓`. The count moved 21 → 22 of 25.** It was the last requirement with no software at
all outside the two conditional phases: the only way into the application was thirteen hand-authored
CSVs.

⚠️ **FR-1's criterion was supervisor-written all along, and this file said otherwise.** The gap table
below recorded FR-1 as "absent from Table 35 — not yet relevant" and stopped there. It **has a full
SRS §3.2 row, Table 4**, which puts it in the same class as FR-4, FR-7, FR-14 and FR-16 — the four
Phase 10 closed against their §3.2 rows. The inference was available from this repository's own
figures: §3.2 covers 21 requirements and is absent for *exactly* C-9's four, so the twenty-first is
FR-1. **Nobody drew it, and the requirement was carried as unspecified for four phases.** The row is
now transcribed verbatim in `docs/testing-strategy.md` §4.

| | The supervisor's own words (SRS §3.2, Table 4) |
|---|---|
| **Input** | Files or forms validated by the server |
| **Processing** | Verification of the types and of the references, then recording |
| **Output** | Entities recorded and report of the rejected lines |

**What was built.** `POST`/`GET`/`DELETE /api/dataset` for the person in charge — **SRS Table 2, and
C-8's ruling that Table 2 wins where CdC §4.3 and SRS §3.3 name the administrator instead** — a
validator that reports every rejected line with its file, line, column and value, a
`department_dataset` table holding the supplied files as one document, and a screen that shows what is
in force, what was refused and why.

⚠️ **`constraint_catalogue.csv` is refused rather than ignored**, and that is invariant 7 rather than
tidiness: an upload able to replace the catalogue could delete a hard rule. It is excluded by
construction — `validate_dataset` takes the catalogue as a *parameter* from the application, so no
supplied file has a path to `Instance.constraints`.

⚠️ **The replacement rule is a PROJECT DECISION and is labelled wherever it is cited** — **C-22** and
**ADR-012**. The specification says how a dataset is loaded and says nothing about what a *second* load
does to the FR-2 declarations and FR-9 closures already stored against the first. A replacement that
would orphan either is refused; no overlay is ever deleted. Everything above this paragraph is the
supervisor's; this paragraph is the project's.

⚠️ **Mutation testing found two tests passing for the wrong reason, and both were real gaps.** A guard
filtering the compatibility check to stored declarations turned out to be unfirable — a candidate's own
rows have already had their references verified — and was **removed** rather than kept as decoration.
And the revision-keyed instance cache had **no test that a second import replaces the first**, so a
cache ignoring the revision passed; that test now exists. **39 of 39 mutations detected** once both
were fixed.

---

## C-9 closed — FR-6, FR-10 and FR-18 reach `✓`, 2026-08-11

> **Project decision — determined from repository evidence and engineering research because supervisor
> clarification was unavailable.** Full reasoning, alternatives and the reversal condition:
> **C-9's RESOLVED subsection** in [`docs/open-questions.md`](open-questions.md), which stays the
> authority. Nothing is attributed to the supervisor that the supervisor did not write.

**The count moved 18 → 21 of 25.** ⚠️ **The three did not close for the same reason, and the difference
is what a reader needs**, because their criteria are not of equal standing:

| FR | Criterion source | Class | What was missing until now |
|---|---|---|---|
| **FR-6** | **SRS §6.7, quoted verbatim** — "The candidates are ordered by decreasing score. Equal scores are separated by the criteria taken in the order of their weights." | ✅ **Supervisor-written** — the strongest class the project has | Only the acceptance file. Found unblocked on 2026-08-10 |
| **FR-10** | *"A timetable view can be printed or exported, and what leaves the screen is the displayed view."* | ⚠️ **Project decision** (adopted 2026-08-10 from CdC §3, the CdC module list and SRS §4.1) | Only the acceptance file |
| **FR-18** | *"An authorised user can consult, for each classroom and each laboratory, the share of the week's open periods it occupies on a given candidate."* | ⚠️ **Project decision** (2026-08-11) | The **quantity**, and every test — `roomOccupancy` had none of any kind |

**⚠️ FR-18's blocker was a false premise, and one search falsified it.** C-9 said *"no document anywhere
defines what the occupancy figure IS"*. It was defined in **C-4, in the same file**, under a different
name — `utilisation(r,k)` = occupied periods / open slots — adopted 2026-07-30, **implemented twice**
(`analysis/criteria.py` and `solver/objective.py`, held together by
`integration/test_objective_matches_analysis`), and computed identically by
`frontend/model.ts::roomOccupancy`, which is the figure FR-18's screen has been displaying all along.
C-9 was searching §3.2 for a row; the definition was never in §3.2.

**⚠️ The rejected alternative is recorded because it is genuinely strong.** External research — the SMG
**UFO** framework, standard in UK/US/AU higher-education space management — defines *frequency* = hours
used / hours available, *occupancy* = occupants / seats, *utilisation* = F × O. **In that vocabulary the
project's figure is a frequency rate and "occupancy" means seats**, and on the reference instance the two
readings **invert**: Salle is emptiest by time (41.8 %) and fullest by seats (92.9 %). It was rejected
because **SRS Table 36 maps FR-18 → §4.1 and §5.1, "Views by classroom and by laboratory"** — FR-18 is a
*view*, and views show when a resource is busy — and because a per-room seat figure would need a new
aggregation rule, which is a business requirement rather than an interpretation. What the research did
oblige is **naming**: the screen and the CSV now state that the rate measures time, not seats.

**⚠️ FR-10's evidence is the project's first FRONTEND acceptance file**, and that is deliberate rather
than convenient: Phase 9 delivered print and export **without touching a backend file**, because
`docs/architecture.md` puts "display, filter, print" in the presentation layer. A requirement whose
whole surface is the rendered DOM must be verified there, or its status would be decided by a directory
layout. `printAndExport.acceptance.test.tsx` renders the grid, exports the same view and compares them as
sets — automating the check Phase 9's audit had performed by hand.

**⚠️ FR-6 was closed WITHOUT changing the product, and the near-miss is worth recording.** Writing its
tie-break test surfaced that two candidates equal in decimal arithmetic can differ as floats by 7.1e-15,
so the score comparison decides before §6.7's tie-break is consulted. Three fixes were considered;
**exact rational arithmetic was refuted by measurement** (the inexactness is in the inputs — `0.4 + 0.2
!= 0.6` as floats — so `Fraction` still gives unequal scores), and a tolerance was rejected as an
invented threshold the specification does not state. `analysis/ranking.py` is **unchanged**; the
behaviour is pinned by a test that states it, and the trigger for revisiting is recorded.

⚠️ **Mutation testing found four of these tests passing for the wrong reason**, three of them because
the candidate ids happened to sort the way the tie-break did. All four were hardened and now fail when
the behaviour is removed. **19 of 19 mutations detected.**

**FR-8 remains `WIP`, and was deliberately not swept up with the others.** Its criterion would have to
be narrowed to accommodate what the software cannot do — on the C-13 contiguity shape CP-SAT proves no
infeasibility, so no rules can be named — and this project refuses that direction. Promoting it would
move a goalpost toward the implementation, which is the exact opposite of what FR-17's promotion did.

---

## Phase 11 — two requirements closed by building their screens, 2026-08-11

**FR-9 and FR-11 reached `✓`.** The count moved **16 → 18 of 25**. Unlike Phase 10, this phase closed
them by writing software rather than by finding a criterion: both had a working, tested *mechanism* and
**no surface a user could reach**, which is precisely what this project's `✓` rule forbids counting.

| | What was already true | What Phase 11 added |
|---|---|---|
| **FR-9** | `Slot.is_open` + H9, acceptance-tested against the real solver — a closure had to be made by editing `slots.csv` | `PUT/GET/DELETE /api/calendar` (administrator), the overrides layered over the pristine instance at run assembly, and `features/admin`'s week, holiday list and shortened-day window |
| **FR-11** | Token authentication and per-endpoint role checks, tested with real tokens | `GET/POST/DELETE /api/accounts` (administrator) — **what C-18 recorded as owed** — plus the student's own surface, `GET /api/me/timetable`, and the role restriction that keeps a student off every other timetable endpoint |

⚠️ **FR-9's criterion is now met through the screen, and the two-engine split is deliberate.** SRS Table
35 asks that closing a half-day *in configuration* remove those slots *from every timetable, with no
code change*. Whether H9 removes them is a question about the **engine** and stays with the four
`solver`-marked tests at production settings; whether an administrator's save reaches the instance a run
is assembled from is a question about the **application** and is tested through the API against the fake
solver. `acceptance/test_fr09.py` carries both halves and says which is which.

⚠️ **One limitation is recorded rather than absorbed, and it is a gap between FR-9's *statement* and the
product — not a gap in its criterion.** ADR-003 gives the shortened-day window one effect: *displayed and
printed hours*. Phase 11 makes the window configurable, persisted and served, and shows the hours it
produces **on the administration screen**. The timetable views and the CSV export still print the
ordinary hours. **Nothing in Table 35 or §3.2 asks for more**, and the criterion FR-9 is ticked against
is exclusively about closing a half-day — but a department that sets a Ramadan window and prints a
timetable will see 08:30. Whether to carry the shift into the timetable views is the project owner's
call, and it is listed in `docs/status.md`'s remaining work rather than left to be discovered.

⚠️ **FR-11's second historical hold is discharged by a guard, not by removing the default.**
`secret_key` still defaults to `change-me-in-env` so the suite and a local demonstration need no
configuration; **Phase 8's `Settings.require_deployable()` refuses that default when
`OPTIEDT_ENVIRONMENT=production`**, and `unit/test_config_guard.py` holds it. The application is safe to
demonstrate and safe to deploy *only when configured*; that is a deployment instruction, not an unmet
requirement.

⚠️ **The student surface has no requirement code, and this table does not invent one.** SRS Table 2
grants the student *"read the timetable of their group"*; that is a **rights** row, not an acceptance
test, so `acceptance/test_student_view.py` says so at its head and the evidence is counted under FR-11,
whose statement is *restrict access by role*.

**An authorisation defect recorded at Phase 9's audit is closed here.** `GET /runs/{id}` accepted any
authenticated caller. That was harmless while every role worked on timetables; a student is the first
role for which it is not, because a run carries every group's drafts and candidates nobody published.
The run, candidate, comparison, assistant and availability endpoints now admit the three roles that work
on timetables, and refuse the student.

---

## Phase 10 — five requirements closed by test, 2026-08-10

**FR-3, FR-4, FR-7, FR-14 and FR-16 reached `✓`.** Each was already built, reachable and working; what
each lacked was an acceptance test against its criterion. The count moved **10 → 15**.

⚠️ **The phase's stated premise was half wrong, and finding out changed the work.** The roadmap said
these five were held "only because no acceptance test exists against their criterion" — but **four of
the five had no criterion either**. SRS §8.6 Table 35, which `docs/testing-strategy.md` §4's table
transcribes, has **no row for FR-4, FR-7, FR-14 or FR-16**.

**What they do have is the thing C-9's four are missing: an SRS §3.2 input/processing/output row.**
That asymmetry is the whole of Phase 10's reasoning, and it is why the phase closed five requirements
without touching C-9:

| | Table 35 row | §3.2 row | Can a test quote a promise? |
|---|---|---|---|
| FR-3 | ✅ yes | ✅ yes | Yes — both, and `test_fr03` now opens with both |
| **FR-4, FR-7, FR-14, FR-16** | ❌ **no** | ✅ **yes** | **Yes** — the §3.2 row, quoted verbatim |
| FR-17 | ❌ no | ❌ no | ✅ **Yes — SRS §6.7 and §8.4 Table 34, found 2026-08-10.** Table 36 names both. Corrected below; FR-17 is `✓` |
| FR-6 | ❌ no | ❌ no | ✅ **Yes — SRS §6.7, found 2026-08-10.** Table 36 names it. Leaves C-9; still needs an acceptance test |
| FR-10, FR-18 | ❌ no | ❌ no | **No. This is what remains of C-9** |

The four §3.2 rows were **transcribed verbatim into `docs/testing-strategy.md` §4**, so no future
session needs the PDF to check what these requirements promise. Nothing was invented: every criterion
quoted in the five acceptance files is the supervisor's own wording.

**What each file establishes, and what it deliberately does not:**

| FR | Evidence | Held back from claiming |
|---|---|---|
| **FR-3** | `test_fr03` — **all twelve H codes by their catalogue number**, eleven re-derived from the placements a user obtains through the API | H10 is **vacuous here** (the instance locks nothing) and says so; `integration/test_h10_locks` exercises it |
| **FR-4** | `test_fr04` — both Table 7 inputs are real inputs the run records, every priced criterion is measured on the solution returned, §6.4's zero-weight rule in both halves, and the search ends on its deterministic limit with a complete timetable | Nothing is built on `SolverOutput.cost` (informational, ADR-011), and **no assertion compares `deterministicTimeUsed` with the budget** — that figure is the sum across workers (C-2) |
| **FR-7** | `test_fr07` (API half) + `model.test.ts` (the selection) + `TimetableGrid.test.tsx` (the weekly grid) | The selection is display logic and no backend test can reach it — both halves are required, as FR-15's are |
| **FR-14** | `test_fr14` — two candidates **of the same run** (a foreign candidate is refused), the two values read from what each candidate **recorded**, a difference per criterion | The contributions-sum identity stays FR-15's; this file does not repeat it |
| **FR-16** | `test_fr16` — the recommendation names the candidate the run ranked first, holds the highest score, states one checkable rule, and recommends nothing on an empty portfolio | ⚠️ **"Verification of dominance happened" is NOT establishable through the API**, because its outcome is provably constant. Found by deliberate mutation: deleting the `dominance()` call from `recommend()` left every acceptance test green. `unit/test_recommendation` is what establishes the machinery is real |

**Every new assertion was verified to fire** by mutating the source before being relied on — eight
backend mutations and three frontend ones. One of them is the FR-16 finding above, which is recorded in
the test's own docstring rather than papered over with a stronger-sounding name.

**Where the project actually is: 23 of 25 requirements are finished, 1 is under way, 1 is not
started.** *(✓ FR-1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25 ·
WIP FR-8 · — FR-21 — count them in the table rather than trusting this line.)*

⚠️ **This line has been wrong twice and is therefore kept with its warning.** It read "10 finished, 11
under way, 4 not started" until 2026-08-10, and the second and third figures contradicted the table in
the same file: Phase 9 moved FR-10 from `—` to `WIP` and this sentence was not re-derived, so it kept
counting FR-10 as not started — the identical fault it already records against itself at M7, in the
identical sentence, eleven days later. **Count the table.** It was re-derived from the table again on
2026-08-11, when Phase 11 moved FR-9 and FR-11.

---

## Pre-Phase-11 audit — FR-17 closed, C-9 narrowed, 2026-08-10

> **Project decision — determined from repository evidence because supervisor clarification was
> unavailable.** The supervisor did not answer and the project owner directed that the question be
> settled from the material to hand. **No wording below is attributed to the supervisor that the
> supervisor did not write.** Full reasoning: **C-9's NARROWED subsection** in
> [`docs/open-questions.md`](open-questions.md), which stays the authority.

**✅ FR-17 → `✓`. The count moves 15 → 16 of 25.**

The question was framed as *"may a project-authored criterion tick a requirement?"* — and that framing
was wrong, which is why it looked undecidable. **FR-17's criterion is not project-authored.** SRS
**Table 36** maps FR-17 → **"§6.7 and §8.4 — Test of dominance"**, and both sections state it:

> **§6.7:** "A candidate which another candidate improves on every criterion is signalled…"
> **§8.4, Table 34:** *Detection of dominance* — "A candidate improved on every criterion is signalled."

**Neither says "recommended" or "top-ranked".** That clause lives only in the *summary* tables, which
this file already records as damaged by cell-offset with Table 36 the reliable source. So C-14's
decision (ii) restored the specification's own detailed wording rather than inventing a reading.

C-14's decision (i) — strict `>` → Pareto — is a project-owner amendment and it **widens** the signal:
`>` on every criterion implies `≥` on every and `>` on one, so the implementation satisfies §8.4
**literally** and catches more besides. ⚠️ **That is why this is not FR-8's situation.** FR-8's criterion
was *narrowed* to accommodate something the software cannot do, and promoting on it would move a
goalpost. FR-17's was widened, and the requirement it now meets is the harder one.

**Evidence for the tick, against this project's own rule — `✓` once a user can reach it and it is
tested end to end:**

| | Evidence |
|---|---|
| Reachable | `features/comparison/DominanceNotice.tsx`, under "Dominance" on the comparison screen |
| Tested end to end | `acceptance/test_fr17.py` — 5 tests through the HTTP API |
| The §8.4 property itself | `property/test_scoring_properties.py::test_dominance_is_detected` — hypothesis, which is the form §8.4 asks for ("properties tested on candidates generated at random") |
| **The signal provably fires** | `unit/test_recommendation.py::test_dominance_still_reports_non_top_candidates` — a dominated runner-up is named. Not a control that can never fire |
| Displayed honestly | `DominanceNotice.test.tsx` — 8 tests, including that an empty result reads as "checked, none found" |

⚠️ **What this tick does not claim.** FR-17 still has **no SRS §3.2 row and no Table 35 row**, and the
ERRATA table's two corrections for it are still unsent. If the supervisor later insists on the strict
reading, the implementation still satisfies it — which is precisely why this tick is safe to take
without an answer.

**C-9 narrowed from four requirements to two.** FR-6 also leaves it: SRS §6.7 states its behaviour
verbatim ("ordered by decreasing score… equal scores separated by the criteria taken in the order of
their weights") and Table 36 points FR-6 at that section. ⚠️ **FR-6 is unblocked, not finished** — the
behaviour is implemented and reachable, and **no acceptance file exists**. That is scheduled work now,
not a blocker.

**FR-10 and FR-18 are what remains of C-9**, and the reason has changed: both are named in
supervisor-written scope statements, so it is no longer "nobody specified them". What is missing is an
acceptance *standard* — and for FR-18, something sharper: **no document defines what the occupancy
figure is.** C-13 is this project's record of losing three sessions to the wrong occupancy denominator,
so choosing one here is the one invention that could actively mislead. C-9 records the strongest
defensible criterion for each; **neither is ticked**, and `OccupancyView.tsx` has no test of any kind.

✅ **FR-25 is `✓` since Phase 7 M5**, and it reached `✓` before the *Necessary* FR-24 beside it for a
reason worth keeping: FR-25's criterion is about the service being **off** — verifiable in full with
no provider — and the computed report is complete: run parameters, every candidate with its score, and
the published candidate. FR-24's criterion is about what a model does when **asked**, and only half of
that was verifiable without one. *(The other half was settled on 2026-08-07 by the live call in
[`docs/demonstration.md`](demonstration.md) §4, which is what finally moved FR-24.)*

✅ **FR-23 was promoted at Phase 7 M2, 2026-08-06**, and it is the first requirement to reach `✓` with
no outstanding reason of any kind. It is reachable from the comparison screen, has an acceptance test
against `testing-strategy.md` §4's criterion, and both of the things that had blocked it are closed:
H10's dormant gap (C-19, M1) and the missing `RunOverride` → `SolverInput` assembly (C-20, M2).
⚠️ Its `recommendations` package had **zero test coverage** until M2 — the Phase 6 audit's finding —
so `unit/test_recommendations.py` is the first test that has ever imported it.

⚠️ *This line said "12 under way, 9 not started" when the M7 audit commit was made, contradicting its
own list of thirteen in the same sentence. It was written before FR-9 moved from `—` to `WIP` and not
re-derived afterwards. Caught by counting the table on the next pass — the same shape as the defect
Phase 4's audit introduced and caught, and the reason a clean pass has to be a **whole** pass rather
than a spot check of what was just edited.*

**The four promoted at M7, and the evidence for each.** Each is reachable through the interface, has an
acceptance test against a criterion in `testing-strategy.md` §4, and has **no stated outstanding
reason** left:

| FR | Reachable via | Acceptance test | What had been blocking it |
|---|---|---|---|
| **FR-5** | Generation screen | `test_fr05` — 5 tests | "no acceptance test" — written in M2 |
| **FR-12** | Pre-analysis report on the generation screen | `test_fr12` — 8 tests | "no acceptance test" — written in M3 |
| **FR-15** | Comparison screen | `test_fr15` + `ContributionsTable.test` | "no acceptance test" — written in M2 |
| **FR-19** | Publications screen | `test_fr19` — both its criteria | "no acceptance test" — written in M2 |

⚠️ **FR-12 carries one documented limit into its `✓`**: `Instance` excludes `Student`, so *"425
students match the declared subgroup sizes"* stays with `scripts/verify-instance.ps1` and the
in-application check says so in its own report. That is a deliberate scope line (increment 2), not an
incompleteness of FR-12's own statement.

**Five that were NOT promoted, though they look close, and why:**

- **FR-3** — H10 is registered but **dormant**: `build_variables` refuses to run if any session is
  locked. One of the twelve rules does not actually execute, so "respecting H1–H12" is not fully built.
  ✅ **Closed 2026-08-06, Phase 7 M1 (C-19).** H10 now executes; `tests/integration/test_h10_locks.py`
  verifies it against the real solver. FR-3's remaining reason is its acceptance test's own scope, not
  a rule that does not run.
- **FR-8** — the acceptance test passes, but the *requirement* says "report the rules in conflict when
  no timetable exists" and on the C-13 contiguity shape **no rules are reported**. The **criterion** was
  reworded to carry that limit (project-owner decision, 2026-08-05); the **requirement statement** was
  not. Promoting on a reworded criterion would be promoting on a moved goalpost.
- ~~**FR-13** — **C-15** is open: the profiles do not differentiate for the documented reason.~~
  ✅ **Closed 2026-08-07. C-15 was resolved by refuting its own diagnosis**: the objective formulation
  is sound and unchanged; what was wrong was *which criteria the profile raised*. `teacher-favouring`
  now raises **S3 and S4** — S5 being an admitted proxy for absent preference data (C-12) and the most
  expensive criterion to optimise. Measured: S3 **29 → 0** (the proven single-criterion optimum), S5
  103 → 95, score 79.45 → 81.10. **FR-13 is `✓`.**
- ~~**FR-11** — account management through the interface is not built (C-18), and `secret_key` still
  defaults to a value published in this repository.~~ ✅ **Both closed. Phase 11 built account
  management (2026-08-11), and Phase 8's `require_deployable()` refuses the published default when
  `OPTIEDT_ENVIRONMENT=production` (2026-08-07).** The default itself remains, deliberately, so the
  suite and a local demonstration need no configuration — the guard is what stops it reaching a
  deployment. **FR-11 is `✓`.**
- **FR-17** — built, displayed and tested, but **C-9** is open: it has no input/processing/output row in
  the SRS, so its criterion comes from this project's own design document rather than the specification.

✅ **FR-22 is `✓` since Phase 7 M4. FR-24 joined it on 2026-08-07**, when the one thing it was waiting
on — a first live provider call — was performed and recorded.

- **FR-22** — the adapter, context builder, verifier and computed forms are built and tested, the
  acceptance criterion is **met** (`test_fr22`), and a user reaches an explanation from the comparison
  screen. Nothing is outstanding.
- **FR-24** — the acceptance criterion was already met by the suite, and the last stated reason for
  holding it at `WIP` was that **no test establishes that a real provider answers a question well**,
  and none can (C-21). That gap is closed the only way it could be: **not by a test, but by the
  deployment step the documentation always named** — one deliberate live call, recorded in
  [`docs/demonstration.md`](demonstration.md) §4. Both halves are now evidenced: a question the context
  *cannot* answer produced no invented figure, and a question it *can* answer returned the top
  candidate's score correct to three decimals.

⚠️ **What promoting FR-24 does NOT mean, because the distinction is the whole of C-21.** The suite is
exactly as provider-free as before — **no test calls a live model, and none may.** The `✓` rests on a
dated, reproducible record of one call, not on automation, and it is not a claim that any provider
answers well in general. §4 also records an imprecision in that very answer (an ambiguous *"candidat
1"*), kept deliberately: the grounding check verifies figures, never the sentence around them.

⚠️ **Performing that call found a real defect no reading had.** `assistant/adapter.py` sent no
`User-Agent`, so `urllib`'s default was refused by the provider's CDN (HTTP 403 / Cloudflare 1010) and
every answer fell back to its computed form — degraded mode behaving correctly, which is exactly why
nothing failed loudly. Fixed, and pinned by a test that intercepts `urlopen` and calls no provider.

**FR-9 moved from `—` to `WIP`** at M7: the mechanism is built and its acceptance criterion is met and
tested (`test_fr09`), while the administration screen it also names is not. `—` said "not started",
which stopped being true when M4 landed. ✅ **`✓` since 2026-08-11** — Phase 11 built the screen and the
endpoint under it, and `test_fr09` now performs the closure through the API as an administrator. See the
Phase 11 section above, **including the one limitation it records**: the shortened-day window is
configured and previewed, and the timetable views still print ordinary hours.

**FR-11 joined in Phase 5 M4**, and it moves an acceptance criterion: *a teacher account obtains only
its own availability and timetable* is **met** — verified against the real API with seeded accounts.
⚠️ It stayed `WIP` for two reasons beyond the acceptance test. **Account management through the
interface was not built** (SRS Table 2 gives it to the administrator; C-18 records why a seed command
stood in), and **`secret_key` still defaults to a value published in this repository**, so the
application was safe to demonstrate rather than safe to expose. ✅ **Both are discharged and FR-11 is
`✓` since 2026-08-11**: Phase 11 built account management, and **Phase 8's `require_deployable()`
refuses the published default when `OPTIEDT_ENVIRONMENT=production`** — the default remains for the
suite and for a local demonstration, which is why the guard, rather than its removal, is the answer.

**FR-19 joined in Phase 5 M3.** Runs, weights, pre-analysis checks, the diagnosis, candidates,
placements and sub-scores are recorded in PostgreSQL behind the Protocols Phase 4 left in place, and
**no router changed**. Verified by killing the API and reading a run back from a fresh process. It
**M5 added publication**, and the criterion it serves — *every **published** timetable traces back to
its run, seed and weights* — is now **met**: the trace is assembled from the run record and survives a
restart. ✅ **FR-19 is `✓` since M7** — `acceptance/test_fr19` covers both criteria it carries.

**FR-8 joined in Phase 5 M2.** The diagnosis run names exactly the guilty rule on instances where one
rule can be at fault, and — after **C-17** replaced enforcement literals with rule withdrawal over
plain subset solves — it answers on the reference instance too: `('H3',)`, minimal, in 1.9 s where the
old mechanism returned `UNKNOWN` after 240 s.

⚠️ **FR-8's acceptance test landed in M6 M3 and FR-8 stays `WIP` anyway** — see the M7 review above:
the criterion was reworded to carry the limit, the requirement statement was not. The limit: on an
infeasibility CP-SAT cannot prove at all — the C-13 contiguity shape — the report is honestly **inconclusive**, and the
pre-analysis is what names the resource. Do not write the acceptance test as though stage 3 always
produces codes.

**FR-12 joined in Phase 5 M1.** The five checks run in `optiedt.preanalysis.verifications`, carry both
the period bound and the contiguity bound, are recorded on every run and are displayed on the
generation screen. ✅ **FR-12 is `✓` since M7** — `acceptance/test_fr12`. ⚠️ Note that no acceptance test
replaces `test_the_original_room_mix_is_caught`, which is what actually pins the bound C-13 turned
on; the acceptance test asserts the report NAMES the resource and quantity, that one asserts the
bound still fires.

⚠️ **Written at Phase 4's close, and kept because the reasoning is what governed the M7 review:**
*"Phase 4 delivered all six milestones and the count of finished requirements is still zero. That is
not a contradiction, and it is the number most likely to be misread."* What kept each requirement at
`WIP` was one of three things, none of them a missing screen: no authentication decided who may see or
do what (FR-11, Phase 5), no run record survived a restart (FR-19, Phase 5), and no acceptance test had
been written against the criterion (Phase 6). **All three were discharged by Phase 6 M2–M3, which is
why four requirements moved to `✓` at M7 and not before.** The rule it states — do not promote a status
because a phase closed — is exactly why the promotion waited for evidence rather than for the calendar.

FR-2 joined the list in Phase 4 M1 and its grid landed in M6: two states, because
`teacher_availability.csv` carries a boolean and there is no third to record (C-12(a), decided
2026-08-01). ✅ **Its acceptance criterion was settled on 2026-08-07** — reworded by project-owner
decision to *"completed without assistance by a user who had not previously seen it"*, because the run
measured no time and so could not support *"under 5 minutes"*. Record and limitations:
[`docs/demonstration.md`](demonstration.md) §2.

✅ **FR-2 is `✓` since 2026-08-07**, once `acceptance/test_fr02` was written — the bar every
requirement promoted at M7 had to clear, and the one FR-2's row had carried with a ⚠️ since it was
written. **Five tests, real tokens, no dependency override**, for the reason `test_fr11` uses them:
FR-2 is about what a *teacher* can do with their own grid, so overriding `current_user` would test the
override rather than the path.

⚠️ **The test does not automate the criterion and says so in its own docstring.** Whether a person
completes the grid unaided was settled by the walkthrough, with its limitations recorded in
[`docs/demonstration.md`](demonstration.md) §2. What the test establishes is the half a stopwatch
cannot: that the capability is **reachable by a teacher over the same HTTP path the screen uses**, that
the whole week arrives in one request as a full day × period rectangle, that closed slots are **marked
as data** so the grid can withhold them without special-casing a day (invariant 7, ADR-003), and that a
generated declaration stays distinguishable from the teacher's own — which is precisely what §2 asks
the participant whether they noticed. **FR-7 and FR-18 joined in M4**: the four
timetable views render a candidate by teacher, group and room, and report each room's occupancy —
verified against the real solver, with the occupancy totals matching `verify-instance` exactly. They
stayed `WIP` because no automated test covered the views yet and there was no authentication deciding
who may see which timetable (FR-11, Phase 5). ✅ **FR-7 is `✓` since Phase 10** — both halves tested,
and the second half is a display-layer test because the *selection* is display logic. **FR-18 is not**:
it is one of C-9's four and has no criterion of any kind. **FR-14 joined in M5**, with the comparison screen; FR-15's
display half is now built and tested, and the acceptance criterion it serves — displayed contributions
summing to the displayed score difference — is **met** (`docs/status.md`). ✅ **FR-15 is `✓` since
M7**, with both halves tested: the identity by `acceptance/test_fr15`, the rendering by
`ContributionsTable.test`.

✅ **FR-17 advanced in Phase 6 M1, once C-14 was resolved.** Phase 4's M5 deliberately did not advance
it: the comparison screen showed no dominance signal at all, because the "dominated top candidate"
indicator both documents ask for is provably unreachable and building it would have shipped a control
that can never fire. **C-14 was decided on 2026-08-05** — the standard Pareto rule, with the signal
moved off the top candidate — and `features/comparison/DominanceNotice.tsx` now reports dominance
wherever it occurs in the portfolio, with eight display tests. It stays `WIP` for its acceptance test
(Phase 6 M2) and then for **C-9**, not for a missing decision — see the M7 review above. Phase 2 built
the decision layer (FR-3) and Phase 3 built the objective, scoring, ranking, decomposition, dominance,
the portfolio and the recommendation rule (FR-4, FR-5, FR-6, FR-13, FR-15, FR-16, FR-17) — but a
requirement is only `✓` once a user can reach it, and there is no API or interface yet. Do not read the
run of `—` below as "nothing works": see [`docs/dashboard.md`](dashboard.md).

**Phases 1–3 are complete as of 2026-07-31, and the count above does not move.** That is not a
contradiction: the phases deliver capability, the requirements deliver *reachable* capability, and every
remaining `—` needs the interface (Phase 4) or the run record (Phase 5). The one thing to watch is the
temptation to promote a status because a phase closed.

⚠️ **FR-16 lost a clause on 2026-08-05 rather than gaining an implementation.** "A dominated top
candidate is signalled alongside" describes a state the arithmetic forbids — a dominated candidate
cannot outscore its dominator under a linear weighted sum with non-negative weights, so it can never
rank first. **C-14 resolved this by deleting the clause**, and the ERRATA table in
[`docs/open-questions.md`](open-questions.md) carries the replacement wording for the CdC and SRS. The
field still exists, is still tested, and is still provably always empty — kept because FR-16's
statement names it and because a non-linear score or a negative weight would revive it. ⚠️ **Adopting
the Pareto rule did not revive it**, and that was checked rather than assumed: `TIE_BREAK_ORDER` covers
all seven criteria, so even the tie Pareto newly admits resolves in the dominator's favour.

✅ **FR-3 reached `✓` in Phase 10, and the paragraph it replaces is kept because its three reasons
were closed one at a time by three different phases.** It read: *"FR-3 is `WIP`, not `✓`, deliberately.
H1–H12 are implemented and demonstrated on the reference instance, with every hard constraint
re-derived from the raw CSVs rather than trusted from CP-SAT's status
(`backend/tests/integration/test_h1_h12.py`). What is missing is the path to it: no endpoint, no run
record, no interface."*

The path arrived with Phases 4 and 5. **H10's dormancy closed in Phase 7 M1 (C-19)**, so all twelve
rules execute. **Phase 10 closed the last of the three**: `acceptance/test_fr03` now re-derives all
twelve rules by their catalogue code from the timetable a user obtains through the API — it checked
seven and mis-numbered two of those until then, which is a test that could not bear the claim its own
requirement makes.

**FR-4, FR-5, FR-6, FR-13, FR-15, FR-16 and FR-17 are `WIP` as of Phase 3's close (2026-07-31), for the
same reason as FR-3** — all seven of them, which is every Phase 3 requirement. The seven soft criteria
(`analysis/criteria.py`), the scorer and ranker (`analysis/scoring.py`, `analysis/ranking.py`, including
`recommend()` for FR-16), the CP-SAT objective (`solver/objective.py`) and the portfolio
(`services/portfolio.py`) are implemented and tested — the four properties the specification requires
pass, verified by ten hypothesis tests in `tests/property/test_scoring_properties.py`, and a real
portfolio run on the reference instance returns three distinct candidates, each scored /100 with its
seven sub-scores.

⚠️ **Updated after Phase 4 M2: the endpoints now exist.** `POST /runs`, `GET /runs/{id}`, the candidate
reads, `GET /runs/{id}/comparison`, `/dominance` and `/recommendation` are implemented and tested. All
seven stay `WIP` regardless, because **a requirement is `✓` only once a user can reach it** and there is
still no screen. What each is now waiting on is narrower than "no endpoint": FR-5, FR-6 and FR-13 need
M3's generation screen; FR-14 and FR-15 need M5's comparison screen; FR-16 and FR-17 need M5 too, and
FR-17 additionally needed **C-14** settled, which it was on 2026-08-05. FR-13 also still carries its own
second reason below.

**FR-16 was on that list and stayed `WIP` for the ordinary reason** — no user could reach the
recommendation. The ⚠️ note above is about something else: one *clause* of FR-16 describes a state that
can never occur. Do not read that note as the reason FR-16 was unfinished; C-14 governs the clause, not
the requirement, and the instruction *"do not let it delay FR-16's `✓` once the interface exists"* was
followed — ✅ **FR-16 is `✓` since Phase 10**, on `acceptance/test_fr16` against SRS §3.2 Table 17.
`dominated_by` remains provably `None` and remains checked.

✅ **FR-13 reached `✓` on 2026-08-07, and the second reason it carried is worth keeping.** It read:
*"the profiles do not yet differentiate — teacher-favouring raises S3 and S5 and measurably improves
only S5, because the objective weights raw violation counts of very different magnitudes."*

**That diagnosis was wrong, and measuring it is what fixed FR-13.** Six measurements on the reference
instance refuted four candidate fixes — including normalising the objective by bound range, which is
**worse** because S3 has the largest range of the seven, and renormalising the weights, which returned a
*bit-identical* timetable because scaling cannot move an argmin. The objective formulation is sound and
is **unchanged**. What was wrong was *which criteria the profile raised*: S5 is an admitted proxy for
absent preference data (**C-12**) and the most expensive criterion to optimise, so weighting it 0.40 left
teacher-favouring **worst of the three on S3, S4 and S5 at once**.

`teacher-favouring` now raises **S3 and S4** — the two criteria that measure teacher experience from
real placements, which is why **C-4** chose *teacher* as S4's resource. Measured: S3 **29 → 0**, S5
103 → 95, score 79.45 → 81.10. `acceptance/test_fr13` now asserts the promise as C-15 reworded it — a
favouring profile holds the best value of its **headline** criterion — which is the only reading the
arithmetic can deliver, since the teacher criteria genuinely conflict.

---

## Increment 1

| FR | Requirement | Priority | Module | Test | Status |
|---|---|---|---|---|---|
| **FR-1** | Load and manage the data of the department | Necessary | `instance/validation` ✓; `services/dataset` ✓; `db` ✓ — `department_dataset`, one migration; `api/routers/dataset` ✓; `features/dataset` ✓ | `acceptance/test_fr01` ✓ (34), `unit/test_dataset_validation` ✓ (45), `unit/test_dataset` ✓ (16), `integration/test_store_contract` ✓ (12, over both stores), `frontend DatasetPanel.test` ✓ (20) | **✓** ⚠️ *replacement rule is a project decision (C-22, ADR-012)* |
| **FR-2** | Teacher declares availability on a weekly grid | Necessary | `api`, `db`; `features/availability` ✓ | `unit/test_availability_api` ✓, `acceptance/test_fr02` ✓, **walkthrough** `demonstration.md` §2 ✓ | **✓** |
| **FR-3** | Generate a timetable respecting H1–H12 | Necessary | `solver` | `integration/test_h1_h12` ✓, `acceptance/test_fr03` ✓ — **all twelve codes, Phase 10** | **✓** |
| **FR-4** | Improve quality criteria within a time limit | Necessary | `solver` — objective ✓ | `integration/test_objective_matches_analysis` ✓, `integration/test_reproducibility` ✓, `acceptance/test_fr04` ✓ | **✓** |
| **FR-5** | Produce several candidates, each scored out of 100 | Necessary | `analysis` — scoring ✓; `features/generation` ✓ | `acceptance/test_fr05` ✓ | **✓** |
| **FR-6** | Order candidates by score | Necessary | `analysis` — ranking ✓ | `property` ✓, `acceptance/test_fr06` ✓ (8) | **✓** |
| **FR-7** | Display the timetable by teacher, group and room | Necessary | `features/timetable` ✓ | `acceptance/test_fr07` ✓, `frontend model.test` ✓, `frontend TimetableGrid.test` ✓ | **✓** |
| **FR-8** | Report the rules in conflict when no timetable exists | Necessary | `preanalysis` ✓, `solver` — `diagnose()` ✓; `features/conflicts` ✓ | `unit/test_diagnosis` ✓, `integration/test_api_runs` ✓, `frontend ConflictReport.test` ✓, `acceptance/test_fr08` ✓ | **WIP** |
| **FR-9** | Configure the calendar: holidays, closed slots, shortened day | Necessary | `db` ✓ — `Slot.is_open` + H9; `services/calendar` ✓; `api/routers/calendar` ✓; `features/admin` ✓ | `acceptance/test_fr09` ✓ (15), `unit/test_calendar` ✓ (16), `integration/test_store_contract` ✓, `frontend CalendarEditor.test` ✓ | **✓** |
| **FR-10** | Print or export a timetable view | Expected | `features/timetable` ✓ — `export.ts`, `PrintHeader.tsx`; `styles.css` `@media print` ✓ | `frontend printAndExport.acceptance.test` ✓ (7), `frontend export.test` ✓, `frontend PrintHeader.test` ✓ | **✓** ⚠️ *criterion is a project decision* |
| **FR-11** | Authenticate users and restrict access by role | Necessary | `core/security` ✓; `services/users` ✓; `api/deps` + `routers/auth` ✓; `routers/accounts` ✓; `routers/student` ✓; `features/auth` ✓; `features/admin` ✓; `features/student` ✓ | `integration/test_rbac` ✓, `unit/test_seed` ✓, `acceptance/test_fr11` ✓ (20), `acceptance/test_student_view` ✓ (12), `frontend AccountsPanel.test` ✓ | **✓** |
| **FR-12** | Verify data before solving; report structural risks | Necessary | `preanalysis` ✓; `api` — `RunOut.preAnalysis`; `features/generation` ✓ | `unit/test_preanalysis` ✓, `integration/test_preanalysis_matches_verifier` ✓, `frontend PreAnalysisReport.test` ✓, `acceptance/test_fr12` ✓ | **✓** |
| **FR-13** | Produce candidates under distinct weight profiles | Necessary | `services` — runs ✓; `solver` ✓ | `unit/test_portfolio` ✓, `acceptance/test_fr13` ✓ | **✓** |
| **FR-14** | Compare two candidates criterion by criterion | Necessary | `analysis` — decomposition ✓; `features/comparison` ✓ | `acceptance/test_fr14` ✓, `frontend ContributionsTable.test` ✓ | **✓** |
| **FR-15** | State each criterion's contribution to the difference | Necessary | `analysis` — decomposition; `features/comparison` | `property` ✓, `frontend ContributionsTable.test` ✓, `acceptance/test_fr15` ✓ | **✓** |
| **FR-16** | Recommend one candidate and state the rule | Expected | `analysis` — ranking ✓; `features/comparison` ✓ | `unit/test_recommendation` ✓, `acceptance/test_fr16` ✓ | **✓** |
| **FR-17** | Signal a candidate that another dominates, wherever it appears in the portfolio ⚠️ *statement corrected, C-14* | Expected | `analysis` — dominance ✓; `features/comparison` ✓ | `property` ✓ (SRS §8.4 Table 34), `unit/test_recommendation` ✓, `frontend DominanceNotice.test` ✓, `acceptance/test_fr17` ✓ | **✓** |
| **FR-18** | Display occupancy of each classroom and laboratory | Expected | `features/timetable` ✓ — `OccupancyView.tsx`, `model.roomOccupancy` | `acceptance/test_fr18` ✓ (7), `frontend OccupancyView.test` ✓ (10) | **✓** ⚠️ *criterion is a project decision* |
| **FR-19** | Record every run with its data, seed, weights, results | Necessary | `db` ✓ — models, migrations, repositories; `services/stores` ✓; `services/publications` ✓; `features/publication` ✓ | `integration/test_store_contract` ✓, `integration/test_publication` ✓, `frontend TraceTable.test` ✓, `acceptance/test_fr19` ✓ | **✓** |
| **FR-22** | Explain a candidate's quality from computed figures | Necessary | `assistant` ✓ — adapter, context builder, verifier, computed forms; `api/routers/assistant` ✓; `features/assistant` ✓ | `unit/test_assistant` ✓, `frontend Answer.test` ✓, `acceptance/test_fr22` ✓ | **✓** |
| **FR-23** | Regenerate from an accepted recommendation, preserving H1–H12 | Necessary | `recommendations` ✓; `services/regeneration` ✓; `api/routers/runs` ✓; `features/comparison/RegenerationPanel` ✓ | `unit/test_recommendations` ✓, `unit/test_regeneration` ✓, `frontend RegenerationPanel.test` ✓, `acceptance/test_fr23` ✓ | **✓** |
| **FR-24** | Answer a question in ordinary language about a run | Necessary | `assistant` ✓; `api/routers/assistant` ✓; `features/assistant` ✓ | `unit/test_assistant` ✓, `frontend Answer.test` ✓, `acceptance/test_fr24` ✓, **live call** `demonstration.md` §4 ✓ | **✓** |
| **FR-25** | Produce a readable report on a run | Expected | `assistant` ✓; `api/routers/assistant` ✓; `features/assistant` ✓ | `acceptance/test_fr25` ✓ | **✓** |

## Increment 2 — conditional

| FR | Requirement | Priority | Module | Test | Status |
|---|---|---|---|---|---|
| **FR-20** | Generate an examination session timetable | Expected | `domain/examination` ✓; `examination/derive` ✓; `examination/solver` ✓ — X1–X4 + SX1; `services/examinations` ✓; `api/routers/examination` ✓; `features/examination` ✓ | `acceptance/test_fr20` ✓ (14), `unit/test_examination_solver` ✓ (14), `frontend ExamCalendar.test` ✓ (9) | **✓** ⚠️ *derivation rule is a project decision (C-23, ADR-013)* |
| **FR-21** | Adjust criterion weights from recorded comparisons | Optional | `analysis` — weight fitting | leave-one-out evaluation | — |

---

## Gaps in the specification

Recorded rather than silently filled. See **C-9** in `docs/open-questions.md`.

| Gap | Detail |
|---|---|
| ~~**FR-6, FR-10, FR-17, FR-18**~~ → **FR-10 and FR-18** | Listed in the summary tables, but **no input/processing/output row** in SRS §3.2. ⚠️ **Narrowed 2026-08-10**: SRS **Table 36** names a specifying section for three of the four, and two of those sections state testable behaviour — **FR-6 → §6.7** ("ordered by decreasing score… equal scores separated by the criteria taken in the order of their weights") and **FR-17 → §6.7 and §8.4 Table 34** ("A candidate improved on every criterion is signalled"). Both leave C-9. **FR-10 and FR-18 remain**: their scope is named in the CdC but no document states an acceptance standard, and for FR-18 **no document defines the occupancy figure itself**. See C-9's NARROWED subsection |
| **FR-4, FR-7, FR-14, FR-16** | ⚠️ **A different gap, found in Phase 10, and NOT part of C-9.** They have a full §3.2 row and **no row in SRS §8.6 Table 35**, the acceptance-test table. The §3.2 row is therefore what their acceptance files verify against, quoted verbatim and transcribed into `docs/testing-strategy.md` §4 so the PDF need never be opened again. **This gap is closed** — all four are `✓` — and it is recorded because the distinction is what makes C-9 unclosable by comparison: a requirement with no promise of *either* kind cannot be verified at all |
| **FR-20** | ⚠️ **Absent from Table 35, and this file recorded no criterion for it until Phase 13 — wrongly.** It has a full SRS §3.2 row, **Table 19**, transcribed into `docs/testing-strategy.md` §4. What it genuinely lacks is a source for three of the five inputs it names; see **C-23** |
| **FR-1** | ⚠️ **This row said "Also absent from Table 35. Not yet relevant" until Phase 12, and the second half was a missed inference.** FR-1 is absent from Table 35, but it **has a full SRS §3.2 row — Table 4** — which puts it in exactly the class Phase 10 closed FR-4, FR-7, FR-14 and FR-16 against. The inference was available all along: §3.2 covers 21 requirements and is absent for *exactly* FR-6, FR-10, FR-17 and FR-18, so 25 − 4 = 21 leaves FR-1 with one. Nobody drew it, and FR-1 was carried as unspecified for four phases. **Transcribed verbatim into `docs/testing-strategy.md` §4 in Phase 12.** ⚠️ What FR-1 *does* lack is any statement about the **second** load — see **C-22** |
| **FR-10** | **Missing entirely from SRS Table 36**, the traceability matrix. Its mapping above is reconstructed, not quoted. ⚠️ **Built in Phase 9, and `✓` since 2026-08-11** when C-9 closed on a **project-authored** criterion, labelled as such wherever cited. ⚠️ **This cell said "still `WIP`, deliberately" until Phase 13**, two phases after the tick moved — in the file that is the authority on requirement status |
| **FR-13's acceptance test** | ⚠️ "Three distinct candidates" can fail while the system behaves correctly — see **C-5** |

**On reconstructing the numbering.** SRS Table 36 is the only reliable source for which code maps to
which requirement. The summary tables in both the CdC and the SRS are damaged by cell-offset in the PDF
layout: read literally, codes and statements do not line up. If you need to check a mapping, use Table
36 — and where Table 36 is silent (FR-10), use this file.

---

## Requirements dropped between documents

None. All 25 codes appear in both the Cahier des Charges and the SRS with consistent statements and
priorities.

The only cross-document disagreement about scope is the **assistant's increment** — resolved as
increment 1 in ADR-010, which is why FR-22, FR-23, FR-24 and FR-25 appear in the increment 1 table
above despite SRS §2.3.
