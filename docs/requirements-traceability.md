# Requirements traceability

FR-1 … FR-25 mapped to the module that implements each and the test that proves it.

**Update the Status column when you finish a requirement.** This table is how anyone answers "is FR-15
built?" without reading code.

Status: `—` not started · `WIP` in progress · `✓` implemented and tested

**Phase 6 M2 added the acceptance suite** — `backend/tests/acceptance/`, 42 tests over **FR-3, FR-5,
FR-11, FR-13, FR-15, FR-17 and FR-19**, each driven through the HTTP API because a requirement is `✓`
only once a user can *reach* it. ⚠️ **A passing acceptance test is necessary, not sufficient**: FR-13
still waits on **C-15**, FR-11 on account management and a `secret_key` that is not published in this
repository, and FR-2 on a timed walkthrough no automated check replaces. The suite is what makes those
remaining reasons the *only* ones.

✅ **The whole table was reviewed against evidence in one pass at M7**, as M2 promised — not row by row
as work landed, which is how a table acquires a count nobody can reproduce.

**Where the project actually is: 6 of 25 requirements are finished, 15 are under way, 4 are not
started.** *(✓ FR-5, 12, 15, 19, 22, 23 · WIP FR-2, 3, 4, 6, 7, 8, 9, 11, 13, 14, 16, 17, 18, 24, 25 ·
— FR-1, 10, 20, 21 — count them in the table rather than trusting this line.)*

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
- **FR-13** — **C-15** is open: the profiles do not differentiate for the documented reason.
- **FR-11** — account management through the interface is not built (C-18), and `secret_key` still
  defaults to a value published in this repository.
- **FR-17** — built, displayed and tested, but **C-9** is open: it has no input/processing/output row in
  the SRS, so its criterion comes from this project's own design document rather than the specification.

✅ **FR-22 is `✓` since Phase 7 M4**, and **FR-24 is `WIP`.** Both are built on the same three routes
and the same panel; the difference is what remains outstanding.

- **FR-22** — the adapter, context builder, verifier and computed forms are built and tested, the
  acceptance criterion is **met** (`test_fr22`), and a user reaches an explanation from the comparison
  screen. Nothing is outstanding.
- **FR-24** — the acceptance criterion is met and the question box works, but it stays `WIP` for one
  stated reason: **no test establishes that a real provider answers a question well**, and cannot
  (C-21 — a model's output is not fixed by a seed). What the suite proves is that a question the
  context cannot answer produces no invented figure, which is the criterion. What it does not prove is
  that a question the context *can* answer produces a good answer. **A first live call belongs in the
  demonstration**, and until it happens FR-24 is not finished.

⚠️ **Do not read that asymmetry as inconsistency.** FR-22's criterion is about the service being OFF,
which is fully verifiable without a provider. FR-24's is about what a model does when asked, and only
half of that is verifiable without one.

**FR-9 moved from `—` to `WIP`** at M7: the mechanism is built and its acceptance criterion is met and
tested (`test_fr09`), while the administration screen it also names is not. `—` said "not started",
which stopped being true when M4 landed.

**FR-11 joined in Phase 5 M4**, and it moves an acceptance criterion: *a teacher account obtains only
its own availability and timetable* is **met** — verified against the real API with seeded accounts.
⚠️ It stays `WIP` for two reasons beyond the acceptance test. **Account management through the
interface is not built** (SRS Table 2 gives it to the administrator; C-18 records why a seed command
stands in), and **`secret_key` still defaults to a value published in this repository**, so the
application is safe to demonstrate rather than safe to expose.

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
2026-08-01). It stays `WIP` for the criterion that matters most — "filled in under 5 minutes without
training" needs a timed walkthrough with a real teacher, which no automated check replaces. **FR-7 and FR-18 joined in M4**: the four
timetable views render a candidate by teacher, group and room, and report each room's occupancy —
verified against the real solver, with the occupancy totals matching `verify-instance` exactly. They
stay `WIP` because no automated test covers the views yet and there is no authentication deciding who
may see which timetable (FR-11, Phase 5). **FR-14 joined in M5**, with the comparison screen; FR-15's
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

**FR-3 is `WIP`, not `✓`, deliberately.** H1–H12 are implemented and demonstrated on the reference
instance, with every hard constraint re-derived from the raw CSVs rather than trusted from CP-SAT's
status (`backend/tests/integration/test_h1_h12.py`). What is missing is the path *to* it: no endpoint,
no run record, no interface. ⚠️ **Written at Phase 3's close, when H10 was also registered but dormant.**
That half is closed: Phase 7 M1 made H10 execute (C-19), so all twelve rules now run.

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

**FR-16 is on that list and stays `WIP` for the ordinary reason** — no user can reach the
recommendation yet. The ⚠️ note above is about something else: one *clause* of FR-16 describes a state
that can never occur. Do not read that note as the reason FR-16 is unfinished, and do not let it delay
FR-16's `✓` once the interface exists; C-14 governs the clause, not the requirement.

⚠️ **FR-13 is `WIP`, not `✓`, for a second reason beyond the missing interface.** It produces candidates
under distinct profiles, but the profiles do not yet differentiate for the documented reason:
"teacher-favouring" raises S3 and S5 and measurably improves only S5, because the objective weights raw
violation counts of very different magnitudes. Recorded as a live risk in
[`docs/status.md`](status.md); it needs a decision before FR-13 can be called done.

---

## Increment 1

| FR | Requirement | Priority | Module | Test | Status |
|---|---|---|---|---|---|
| **FR-1** | Load and manage department data | Necessary | `api`, `db`, `services` | `acceptance/test_fr01` | — |
| **FR-2** | Teacher declares availability on a weekly grid | Necessary | `api`, `db`; `features/availability` ✓ | `unit/test_availability_api` ✓, `acceptance/test_fr02` ⚠️ timed walkthrough | **WIP** |
| **FR-3** | Generate a timetable respecting H1–H12 | Necessary | `solver` | `integration/test_h1_h12` ✓, `acceptance/test_fr03` ✓ | **WIP** |
| **FR-4** | Improve quality criteria within a time limit | Necessary | `solver` — objective | `integration` | **WIP** |
| **FR-5** | Produce several candidates, each scored out of 100 | Necessary | `analysis` — scoring ✓; `features/generation` ✓ | `acceptance/test_fr05` ✓ | **✓** |
| **FR-6** | Order candidates by score | Necessary | `analysis` — ranking | `property` ✓ | **WIP** |
| **FR-7** | Display the timetable by teacher, group and room | Necessary | `features/timetable` | `integration` | **WIP** |
| **FR-8** | Report the rules in conflict when no timetable exists | Necessary | `preanalysis` ✓, `solver` — `diagnose()` ✓; `features/conflicts` ✓ | `unit/test_diagnosis` ✓, `integration/test_api_runs` ✓, `frontend ConflictReport.test` ✓, `acceptance/test_fr08` | **WIP** |
| **FR-9** | Configure the calendar: holidays, closed slots, shortened day | Necessary | `db` ✓ — `Slot.is_open` + H9; `features/admin` ⬜ **not built** | `acceptance/test_fr09` ✓ | **WIP** |
| **FR-10** | Print or export a timetable view | Expected | `features/timetable` | `integration` | — |
| **FR-11** | Authenticate users and restrict access by role | Necessary | `core/security` ✓; `services/users` ✓; `api/deps` + `routers/auth` ✓; `features/auth` ✓ | `integration/test_rbac` ✓, `unit/test_seed` ✓, `acceptance/test_fr11` ✓ | **WIP** |
| **FR-12** | Verify data before solving; report structural risks | Necessary | `preanalysis` ✓; `api` — `RunOut.preAnalysis`; `features/generation` ✓ | `unit/test_preanalysis` ✓, `integration/test_preanalysis_matches_verifier` ✓, `frontend PreAnalysisReport.test` ✓, `acceptance/test_fr12` ✓ | **✓** |
| **FR-13** | Produce candidates under distinct weight profiles | Necessary | `services` — runs; `solver` | `unit/test_portfolio` ✓, `acceptance/test_fr13` ✓ ⚠️ | **WIP** |
| **FR-14** | Compare two candidates criterion by criterion | Necessary | `features/comparison` | `integration` | **WIP** |
| **FR-15** | State each criterion's contribution to the difference | Necessary | `analysis` — decomposition; `features/comparison` | `property` ✓, `frontend ContributionsTable.test` ✓, `acceptance/test_fr15` ✓ | **✓** |
| **FR-16** | Recommend one candidate and state the rule | Expected | `analysis` — ranking | `unit/test_recommendation` ✓ | **WIP** |
| **FR-17** | Signal a candidate that another dominates, wherever it appears in the portfolio ⚠️ *statement corrected, C-14* | Expected | `analysis` — dominance ✓; `features/comparison` ✓ | `property` ✓, `unit/test_recommendation` ✓, `frontend DominanceNotice.test` ✓, `acceptance/test_fr17` ✓ | **WIP** |
| **FR-18** | Display occupancy of each classroom and laboratory | Expected | `features/timetable` | `integration` | **WIP** |
| **FR-19** | Record every run with its data, seed, weights, results | Necessary | `db` ✓ — models, migrations, repositories; `services/stores` ✓; `services/publications` ✓; `features/publication` ✓ | `integration/test_store_contract` ✓, `integration/test_publication` ✓, `frontend TraceTable.test` ✓, `acceptance/test_fr19` ✓ | **✓** |
| **FR-22** | Explain a candidate's quality from computed figures | Necessary | `assistant` ✓ — adapter, context builder, verifier, computed forms; `api/routers/assistant` ✓; `features/assistant` ✓ | `unit/test_assistant` ✓, `frontend Answer.test` ✓, `acceptance/test_fr22` ✓ | **✓** |
| **FR-23** | Regenerate from an accepted recommendation, preserving H1–H12 | Necessary | `recommendations` ✓; `services/regeneration` ✓; `api/routers/runs` ✓; `features/comparison/RegenerationPanel` ✓ | `unit/test_recommendations` ✓, `unit/test_regeneration` ✓, `frontend RegenerationPanel.test` ✓, `acceptance/test_fr23` ✓ | **✓** |
| **FR-24** | Answer a question in ordinary language about a run | Necessary | `assistant` ✓; `api/routers/assistant` ✓; `features/assistant` ✓ | `unit/test_assistant` ✓, `frontend Answer.test` ✓, `acceptance/test_fr24` ✓ | **WIP** |
| **FR-25** | Produce a readable report on a run | Expected | `assistant` | `acceptance/test_fr25` | — |

## Increment 2 — conditional

| FR | Requirement | Priority | Module | Test | Status |
|---|---|---|---|---|---|
| **FR-20** | Generate an examination session timetable | Expected | `solver` — exam model | `acceptance/test_fr20` | — |
| **FR-21** | Adjust criterion weights from recorded comparisons | Optional | `analysis` — weight fitting | leave-one-out evaluation | — |

---

## Gaps in the specification

Recorded rather than silently filled. See **C-9** in `docs/open-questions.md`.

| Gap | Detail |
|---|---|
| **FR-6, FR-10, FR-17, FR-18** | Listed in the summary tables, but **no input/processing/output row** in SRS §3.2. Their implementation is inferred from the summary statement alone |
| **FR-10** | **Missing entirely from SRS Table 36**, the traceability matrix. Its mapping above is reconstructed, not quoted |
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
