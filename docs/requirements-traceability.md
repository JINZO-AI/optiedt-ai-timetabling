# Requirements traceability

FR-1 … FR-25 mapped to the module that implements each and the test that proves it.

**Update the Status column when you finish a requirement.** This table is how anyone answers "is FR-15
built?" without reading code.

Status: `—` not started · `WIP` in progress · `✓` implemented and tested

**Where the project actually is: 16 of 25 requirements are under way, none is finished.**
*(FR-2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 19 — count them in the table rather than trusting this line.)*

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
restart. FR-19 stays `WIP` only for its acceptance test, which is Phase 6.

**FR-8 joined in Phase 5 M2.** The diagnosis run names exactly the guilty rule on instances where one
rule can be at fault, and — after **C-17** replaced enforcement literals with rule withdrawal over
plain subset solves — it answers on the reference instance too: `('H3',)`, minimal, in 1.9 s where the
old mechanism returned `UNKNOWN` after 240 s.

⚠️ It stays `WIP` for its acceptance test, and one limit belongs in it: on an infeasibility CP-SAT
cannot prove at all — the C-13 contiguity shape — the report is honestly **inconclusive**, and the
pre-analysis is what names the resource. Do not write the acceptance test as though stage 3 always
produces codes.

**FR-12 joined in Phase 5 M1.** The five checks run in `optiedt.preanalysis.verifications`, carry both
the period bound and the contiguity bound, are recorded on every run and are displayed on the
generation screen. It stays `WIP` for its acceptance test (Phase 6) — and note that no acceptance test
can replace `test_the_original_room_mix_is_caught`, which is what actually pins the bound C-13 turned
on.

⚠️ **Phase 4 delivered all six milestones and the count of finished requirements is still zero. That is
not a contradiction, and it is the number most likely to be misread.** Every Phase 4 screen exists and
was verified against the real solver; what keeps each requirement at `WIP` is now one of three things,
none of them a missing screen: **no authentication** decides who may see or do what (FR-11, Phase 5),
**no run record** survives a restart (FR-19, Phase 5), and **no acceptance test** has been written
against the criterion (Phase 6). Do not promote a status because a phase closed — the same temptation
Phase 3 recorded.

FR-2 joined the list in Phase 4 M1 and its grid landed in M6: two states, because
`teacher_availability.csv` carries a boolean and there is no third to record (C-12(a), decided
2026-08-01). It stays `WIP` for the criterion that matters most — "filled in under 5 minutes without
training" needs a timed walkthrough with a real teacher, which no automated check replaces. **FR-7 and FR-18 joined in M4**: the four
timetable views render a candidate by teacher, group and room, and report each room's occupancy —
verified against the real solver, with the occupancy totals matching `verify-instance` exactly. They
stay `WIP` because no automated test covers the views yet and there is no authentication deciding who
may see which timetable (FR-11, Phase 5). **FR-14 joined in M5**, with the comparison screen; FR-15's
display half is now built and tested, and the acceptance criterion it serves — displayed contributions
summing to the displayed score difference — is **met** (`docs/status.md`). FR-15 stays `WIP` only for
its acceptance test, which is Phase 6.

⚠️ **FR-17 is deliberately not advanced by M5.** `GET /runs/{id}/dominance` exists and is tested, but
the comparison screen shows no dominance signal: **C-14** is open, and the "dominated top candidate"
indicator both documents ask for is provably unreachable. Building it would ship an indicator that can
never fire. Phase 2 built
the decision layer (FR-3) and Phase 3 built the objective, scoring, ranking, decomposition, dominance,
the portfolio and the recommendation rule (FR-4, FR-5, FR-6, FR-13, FR-15, FR-16, FR-17) — but a
requirement is only `✓` once a user can reach it, and there is no API or interface yet. Do not read the
run of `—` below as "nothing works": see [`docs/dashboard.md`](dashboard.md).

**Phases 1–3 are complete as of 2026-07-31, and the count above does not move.** That is not a
contradiction: the phases deliver capability, the requirements deliver *reachable* capability, and every
remaining `—` needs the interface (Phase 4) or the run record (Phase 5). The one thing to watch is the
temptation to promote a status because a phase closed.

⚠️ **FR-16 is implemented but one third of it can never fire.** "A dominated top candidate is signalled
alongside" describes a state the arithmetic forbids — a dominated candidate cannot outscore its
dominator under a linear weighted sum with non-negative weights, so it can never rank first. The field
exists, is tested, and is provably always empty. See C-14 in [`docs/open-questions.md`](open-questions.md);
the specification wording needs revising, which is not a keyboard decision.

**FR-3 is `WIP`, not `✓`, deliberately.** H1–H12 are implemented and demonstrated on the reference
instance, with every hard constraint re-derived from the raw CSVs rather than trusted from CP-SAT's
status (`backend/tests/integration/test_h1_h12.py`). What is missing is the path *to* it: no endpoint,
no run record, no interface. H10 is also registered but dormant — `build_variables` refuses to run if
any session is locked, which is safe only because the reference instance has none.

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
FR-17 additionally needs **C-14** settled. FR-13 also still carries its own second reason below.

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
| **FR-3** | Generate a timetable respecting H1–H12 | Necessary | `solver` | `integration/test_h1_h12` ✓ | **WIP** |
| **FR-4** | Improve quality criteria within a time limit | Necessary | `solver` — objective | `integration` | **WIP** |
| **FR-5** | Produce several candidates, each scored out of 100 | Necessary | `analysis` — scoring | `acceptance/test_fr05` | **WIP** |
| **FR-6** | Order candidates by score | Necessary | `analysis` — ranking | `property` ✓ | **WIP** |
| **FR-7** | Display the timetable by teacher, group and room | Necessary | `features/timetable` | `integration` | **WIP** |
| **FR-8** | Report the rules in conflict when no timetable exists | Necessary | `preanalysis` ✓, `solver` — `diagnose()` ✓; `features/conflicts` ✓ | `unit/test_diagnosis` ✓, `integration/test_api_runs` ✓, `frontend ConflictReport.test` ✓, `acceptance/test_fr08` | **WIP** |
| **FR-9** | Configure the calendar: holidays, closed slots, shortened day | Necessary | `db`, `features/admin` | `acceptance/test_fr09` | — |
| **FR-10** | Print or export a timetable view | Expected | `features/timetable` | `integration` | — |
| **FR-11** | Authenticate users and restrict access by role | Necessary | `core/security` ✓; `services/users` ✓; `api/deps` + `routers/auth` ✓; `features/auth` ✓ | `integration/test_rbac` ✓, `unit/test_seed` ✓, `acceptance/test_fr11` | **WIP** |
| **FR-12** | Verify data before solving; report structural risks | Necessary | `preanalysis` ✓; `api` — `RunOut.preAnalysis`; `features/generation` ✓ | `unit/test_preanalysis` ✓, `integration/test_preanalysis_matches_verifier` ✓, `frontend PreAnalysisReport.test` ✓, `acceptance/test_fr12` | **WIP** |
| **FR-13** | Produce candidates under distinct weight profiles | Necessary | `services` — runs; `solver` | `unit/test_portfolio` ✓, `acceptance/test_fr13` ⚠️ | **WIP** |
| **FR-14** | Compare two candidates criterion by criterion | Necessary | `features/comparison` | `integration` | **WIP** |
| **FR-15** | State each criterion's contribution to the difference | Necessary | `analysis` — decomposition; `features/comparison` | `property` ✓, `frontend ContributionsTable.test` ✓, `acceptance/test_fr15` | **WIP** |
| **FR-16** | Recommend one candidate and state the rule | Expected | `analysis` — ranking | `unit/test_recommendation` ✓ | **WIP** |
| **FR-17** | Signal a recommended candidate that another dominates | Expected | `analysis` — dominance | `property` ✓ | **WIP** |
| **FR-18** | Display occupancy of each classroom and laboratory | Expected | `features/timetable` | `integration` | **WIP** |
| **FR-19** | Record every run with its data, seed, weights, results | Necessary | `db` ✓ — models, migrations, repositories; `services/stores` ✓; `services/publications` ✓; `features/publication` ✓ | `integration/test_store_contract` ✓, `integration/test_publication` ✓, `frontend TraceTable.test` ✓, `acceptance/test_fr19` | **WIP** |
| **FR-22** | Explain a candidate's quality from computed figures | Necessary | `assistant` | `acceptance/test_fr22` | — |
| **FR-23** | Regenerate from an accepted recommendation, preserving H1–H12 | Necessary | `recommendations` | `acceptance/test_fr23` | — |
| **FR-24** | Answer a question in ordinary language about a run | Necessary | `assistant` | `acceptance/test_fr24` | — |
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
