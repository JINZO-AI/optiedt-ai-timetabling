# Requirements traceability

FR-1 … FR-25 mapped to the module that implements each and the test that proves it.

**Update the Status column when you finish a requirement.** This table is how anyone answers "is FR-15
built?" without reading code.

Status: `—` not started · `WIP` in progress · `✓` implemented and tested

**Where the project actually is: 1 of 25 requirements is under way, none is finished.** Phase 2 built
the decision layer, which is the engine behind FR-3 and the precondition for FR-4, FR-5 and FR-8 — but
a requirement is only `✓` once a user can reach it, and there is no API or interface yet. Do not read
the run of `—` below as "nothing works": see [`docs/dashboard.md`](dashboard.md).

**FR-3 is `WIP`, not `✓`, deliberately.** H1–H12 are implemented and demonstrated on the reference
instance, with every hard constraint re-derived from the raw CSVs rather than trusted from CP-SAT's
status (`backend/tests/integration/test_h1_h12.py`). What is missing is the path *to* it: no endpoint,
no run record, no interface. H10 is also registered but dormant — `build_variables` refuses to run if
any session is locked, which is safe only because the reference instance has none.

---

## Increment 1

| FR | Requirement | Priority | Module | Test | Status |
|---|---|---|---|---|---|
| **FR-1** | Load and manage department data | Necessary | `api`, `db`, `services` | `acceptance/test_fr01` | — |
| **FR-2** | Teacher declares availability on a weekly grid | Necessary | `api`, `db`; `features/availability` | `acceptance/test_fr02` | — |
| **FR-3** | Generate a timetable respecting H1–H12 | Necessary | `solver` | `integration/test_h1_h12` ✓ | **WIP** |
| **FR-4** | Improve quality criteria within a time limit | Necessary | `solver` — objective | `integration` | — |
| **FR-5** | Produce several candidates, each scored out of 100 | Necessary | `analysis` — scoring | `acceptance/test_fr05` | — |
| **FR-6** | Order candidates by score | Necessary | `analysis` — ranking | `property` | — |
| **FR-7** | Display the timetable by teacher, group and room | Necessary | `features/timetable` | `integration` | — |
| **FR-8** | Report the rules in conflict when no timetable exists | Necessary | `preanalysis`, `solver` — diagnosis | `acceptance/test_fr08` | — |
| **FR-9** | Configure the calendar: holidays, closed slots, shortened day | Necessary | `db`, `features/admin` | `acceptance/test_fr09` | — |
| **FR-10** | Print or export a timetable view | Expected | `features/timetable` | `integration` | — |
| **FR-11** | Authenticate users and restrict access by role | Necessary | `core` — security; `api` — deps | `acceptance/test_fr11` | — |
| **FR-12** | Verify data before solving; report structural risks | Necessary | `preanalysis` | `acceptance/test_fr12` | — |
| **FR-13** | Produce candidates under distinct weight profiles | Necessary | `services` — runs; `solver` | `acceptance/test_fr13` ⚠️ | — |
| **FR-14** | Compare two candidates criterion by criterion | Necessary | `features/comparison` | `integration` | — |
| **FR-15** | State each criterion's contribution to the difference | Necessary | `analysis` — decomposition | `property`, `acceptance/test_fr15` | — |
| **FR-16** | Recommend one candidate and state the rule | Expected | `analysis` — ranking | `unit` | — |
| **FR-17** | Signal a recommended candidate that another dominates | Expected | `analysis` — dominance | `property` | — |
| **FR-18** | Display occupancy of each classroom and laboratory | Expected | `features/timetable` | `integration` | — |
| **FR-19** | Record every run with its data, seed, weights, results | Necessary | `db`, `services` | `acceptance/test_fr19` | — |
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
