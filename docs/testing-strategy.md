# Testing strategy

Four verifications of different natures, each answering a distinct question. They are not four levels
of the same pyramid — they establish different kinds of claim.

| Verification | Question it answers |
|---|---|
| Published instances | Is the model correct? |
| The five data checks | Is the instance solvable? |
| Properties of the analysis layer | Is the ranking exact and stable? |
| Acceptance tests | Does the application do what was promised? |

---

## 1 · Validation on published instances

**Built 2026-07-31, closing Phase 3.** `backend/src/optiedt/validation/itc2007/`, run by
`scripts/validate-itc2007.ps1`.

The engine is tested on the **curriculum-based track of ITC-2007**, for which results are published.

Two things are examined: that no timetable produced violates a hard constraint, and the distance
between the cost obtained and the best known results.

**The objective is not to beat published results** — that would not be realistic in four weeks. It is
to show that the engine produces valid timetables of reasonable quality **on instances it was not built
around**. An engine validated only on its own generated instance has demonstrated nothing.

### What is validated, and what is not

⚠️ **This is a separate model of a different problem, not `optiedt.solver` pointed at foreign data.**
ITC-2007 has room *capacities* where OptiEDT has room *types*, curricula where OptiEDT has a
promotion → TD → TP hierarchy, per-course lecture counts and minimum working days where OptiEDT has
individual sessions, and four soft costs none of which is one of S2–S10. Forcing the reference
instance's schema onto it would have validated an adapter and been reported as validating an engine.

**Validated:** the modelling approach (ADR-001 — CP-SAT for assignment, correct by construction), the
solve configuration ADR-011 fixes (deterministic budget, `interleave_search`, fixed seed), and the
discipline of re-deriving every constraint from the instance rather than trusting the solver's status.
**Not validated:** `optiedt.solver`'s own H1–H12 code paths — those are covered by
`tests/integration/test_h1_h12.py` on the reference instance. Quote both halves.

### Why the cost figures can be trusted

The cost function is not asserted, it is **checked against the archive's own published results**. The
archive ships seven solutions produced by a third-party solver years before this project existed, and
`cost.py` re-evaluates them to exactly the cost the bundled report records — all four components, all
seven instances. That test needs no solver and therefore runs on every `scripts/run-checks.ps1`
(`tests/integration/test_itc2007_validation.py`). Without it, every number the harness prints would be
merely self-consistent.

The harness checks its own model the same way the product does: **the value CP-SAT gives each auxiliary
must equal the component `cost.py` derives from the placements**, component by component, because a
total can agree while two components cancel. That check found nothing wrong with the encoding — but it
did surface something about the solver, recorded in ADR-011: under `interleave_search`,
`CpSolver.objective_value` can sit a few units above the objective at the solution actually returned.
No figure here depends on it; every one is re-derived from the placements.

`published.py` transcribes the reference costs from
`data/reference/itc2007-cct-master/.../docs/latex/itc2007.tex` — the report bundled with the archive,
which cites the competition finalists' page and Müller (2008). **The archive publishes figures for
`comp01`–`comp07` only**; the other fourteen are solved and reported on validity alone rather than
compared against a number nobody can trace.

### What it found, 2026-07-31

**21 of 21 timetables violate no hard constraint.** That is the claim this section makes first, and it
holds on every competition instance, judged by re-deriving all four ITC-2007 constraints rather than
trusting CP-SAT's status.

**The cost gap is large and expected.** Against the seven instances the archive gives figures for, the
gap runs 255 %–9985 %, median 1269 %, at a deterministic budget of 60 per instance. The references are
metaheuristics tuned for this exact problem — several with no time limit at all — against roughly fifty
seconds of exact search. **The objective was never to beat them.**

**The model itself is demonstrably right**, which is what makes the gap interpretable: `comp11` solved
to **cost 0 and proven optimal**, and `comp01` reaches the published optimum of **5** when the same
model is given more search. The distance on the larger instances is search budget, not modelling.
Per-instance figures are in [`docs/status.md`](status.md). **Quote validity first, cost second, and
always with the budget.**

For the examination module, the same procedure on Track 1 instances — after verifying them. Track 1 has
not been opened yet; **assume no property of it before that verification**.

Archives live in `data/reference/`, gitignored and **already present** — 21 ITC-2007 Track 3 instances
and 25 XHSTT instances, verified. Run `scripts/check-reference-data.ps1` to confirm, and see
[`PROVENANCE.md`](../data/reference/PROVENANCE.md) for what verification found. Because they are
gitignored, **every test that touches them skips when they are absent** — a suite that failed on a
fresh clone would teach the next reader to ignore it.

---

## 2 · Verification of the data

The five checks of `docs/data-and-instance.md`, applied before any solving, with the expected results
recorded there.

Their purpose is to distinguish **an instance that genuinely has no solution** from **an error in the
model** — two situations a solver reports identically.

This is also the project's primary debugging instrument. At 91% computer-laboratory occupancy (of
two-period windows), a modelling regression surfaces as `INFEASIBLE`, not as a slow solve. Without
these checks you cannot tell which you are looking at. **Run them first, always** — and be sure a check
that passes is actually *sufficient*, not merely necessary. C-13 was a genuinely infeasible instance
that passed verification, so the `UNKNOWN` it produced was blamed on the model for three sessions.

A failing check must name the **resource concerned and the quantity missing**, not return a boolean —
that is the content FR-12 requires.

### Two implementations, compared numerically · Phase 5 M1

The checks exist **twice**, deliberately, and the duplication is guarded the same way the objective's
is.

| Where | What it is for | May depend on |
|---|---|---|
| `data/verification/verify_instance.py` | Guards the contract between the generator and the application. Runs in `run-checks.ps1` | **Nothing** — not the backend, not a third-party package |
| `optiedt.preanalysis.verifications` | Stage 1 of every run; reports structural risk through the API (FR-12) | `optiedt.domain` only |

The standalone checker cannot import the application, because the 13 CSVs *are* the contract and a
checker that guards a contract must not depend on either side of it. So the same arithmetic is written
twice, and **`tests/integration/test_preanalysis_matches_verifier.py` requires the two to agree figure
for figure** — re-deriving every figure from the raw CSVs rather than comparing against a constant
transcribed from a document, which would prove the transcription and not the arithmetic.

That test is the counterpart of `test_objective_matches_analysis.py`: two implementations of one
definition agreeing *in shape* is not evidence they agree *in value*, and the analysis/solver pair
proved it by disagreeing 28×.

⚠️ **One half of verification 5 is deliberately absent from the in-application check**, and it says so
in its own report: `Instance` excludes `Student` (increment 2), so "425 students match the declared
subgroup sizes" stays with `scripts/verify-instance.ps1`. A narrower check must not pass for the
documented one.

⚠️ **`test_the_original_room_mix_is_caught` is the C-13 regression test.** It reconstructs the room mix
as it was before the 2026-07-30 repair and requires the contiguity bound to name both shortfalls —
computer laboratories short by 14 windows, science laboratories by 2 — on an instance the period bound
passes at a comfortable 95.2 %. **If that test ever passes trivially, the blind spot is back inside the
product.**

---

## 3 · Properties of the analysis layer

Verified by **property-based testing on randomly generated candidates**, using `hypothesis`.

The reason is worth stating, because it is unusual enough to be undone by someone who thinks unit tests
would be simpler: **a property holds for every input, an example holds for one.** The claims this layer
makes — that a decomposition is exact, that an order is stable — are universal claims. Testing them by
example would demonstrate something weaker than what is promised to the department.

| Property | Statement tested |
|---|---|
| Exactness of decomposition | The sum of the contributions equals the difference of the two scores |
| Invariance of order | The order does not depend on the order candidates are read in |
| Monotonicity | Reducing violations of one criterion never lowers the score |
| Detection of dominance | A candidate another matches on every criterion and beats on at least one is signalled (Pareto — C-14) |
| Fidelity of formulation | Every figure in the model's sentence appears in the structured explanation |

Two notes:

- **Exactness and floating point.** Assert to *display precision*, which is what the acceptance
  criterion actually promises ("to the precision of the display"), not to exact equality.
- **Monotonicity is tested because the weight fitting of increment 2 could break it.** It follows from
  weight non-negativity, which the fitting must preserve.

These tests need **no solver**. Candidates are written by hand or generated — which is one of the
reasons the analysis layer is isolated in the first place. Tests live in `backend/tests/property/`.

---

## 4 · Functional and acceptance tests

Each requirement is verified against **the acceptance criterion written at the same time as the
requirement itself**. Tests live in `backend/tests/acceptance/`, one per criterion, named for its FR.

⚠️ **The specification states a requirement's promise in TWO places, and they cover different sets.**
Phase 10 found this by checking rather than assuming, and it is what the table below is now organised
around — read this before adding or moving a row:

| Source | What it gives | Which requirements it covers |
|---|---|---|
| **SRS §8.6, Table 35 — "Acceptance tests"** | A test and an expected result, in the supervisor's own words | **13 rows over 14 requirements** — FR-2, 3, 5, 8, 9, 11, 12, 13, 15, 19, 23, 24, and one row shared by FR-22 and FR-25. **The upper table below is a transcription of it** |
| **SRS §3.2 — "Detailed specification"** | An **input / processing / output** row per requirement | **21 requirements**, Tables 4–24. Absent for exactly FR-6, FR-10, FR-17 and FR-18 — that absence **is C-9** |

The two are not nested. **FR-4, FR-7, FR-14 and FR-16 have a §3.2 row and no Table 35 row**, which is
the opposite shape from C-9's four and needs the opposite treatment: there *is* a promise written by
the supervisor to quote, so an acceptance file can open with it and the requirement can be verified
against something it did not write itself. Those four are the **lower** table.

> **Do not merge the two tables.** A reader must be able to tell a criterion the supervisor wrote as a
> *test* from one derived from the supervisor's *specification of behaviour*, and both from a criterion
> this project authored for itself (FR-17, via C-14). All three are legitimate; they are not equally
> strong, and flattening them would hide which is which.

**Verified against SRS §8.6 Table 35** — the supervisor's own acceptance tests:

| FR | Test | Expected result | State |
|---|---|---|---|
| FR-2 | Fill in the availability grid | Completed unaided by a user who had not seen it | ⚠️ **not automatable — still true, and the criterion was REWORDED rather than automated.** Run 2026-08-07; the original wording asked for *"under 5 minutes"* and **the run measured no time**, so the clause was dropped by project-owner decision. Record and limitations: `docs/demonstration.md` §2. **A timed run with a naive participant would still be strictly better evidence** |
| FR-3 | Generate on the reference instance | No hard-constraint violation | ✅ `test_fr03`, `solver` — **all twelve codes since Phase 10**; see the note below |
| FR-5 | Read a candidate | Overall score and sub-scores displayed | ✅ `test_fr05` |
| FR-8 | Generate on a deliberately infeasible instance | Report naming the rules in conflict by code | ✅ `test_fr08`, `solver` — ⚠️ **both shapes**, and the criterion holds on only one |
| FR-9 | Close a half-day in configuration | Those slots disappear from every timetable, **with no code change** | ✅ `test_fr09`, `solver` — ticks criterion 7 |
| FR-11 | Connect with a teacher account | Access limited to own data | ✅ `test_fr11`, real tokens |
| FR-12 | Verify an instance with insufficient rooms | The resource concerned and quantity missing are named | ✅ `test_fr12` |
| FR-13 | Run on the reference instance | **Three distinct candidates on the reference instance at production settings** (C-5, resolved 2026-08-05) | ✅ `test_fr13`, `solver` |
| FR-15 | Compare two candidates | Sum of contributions equals the score difference | ✅ `test_fr15` |
| FR-19 | Repeat a run with the same seed and weights | Identical candidates in the same order · **and** every published timetable traces back to its run, seed and weights | ✅ `test_fr19`, `solver` |
| FR-23 | Accept a `weight_delta` recommendation | New run created; new candidate satisfies H1–H12; linked to the recommendation | ✅ `test_fr23`, 14 tests — ten about the application, **four `solver`-marked** at production settings |
| FR-24 | Ask a question whose answer is not in the context | The assistant says it cannot answer, and **invents no figure** | ✅ `test_fr24`, 9 tests — **both** ways it can be met: a model that declines, and a model that does not and is stopped |
| FR-22, FR-25 | Switch the language service off in configuration | Explanations and reports fall back to computed form; **every other function unaffected** | ✅ `test_fr22` (9) + `test_fr25` (10) — and the criterion needs **no provider, no key and no network**, because off is the default |

**Verified against SRS §3.2** — no Table 35 row exists, so the input/processing/output row *is* the
promise. Transcribed here **verbatim** in Phase 10, so no session ever needs the PDF again:

| FR | SRS table | Input | Processing | Output | State |
|---|---|---|---|---|---|
| FR-4 | Table 7 | Weights of the criteria and time limit | Minimisation of the weighted penalty within the limit | Best solution found when the limit is reached | ✅ `test_fr04` — 7 tests, **1 `solver`-marked** |
| FR-7 | Table 9 | Published timetable and chosen filter | Selection of the sessions concerning the resource | Weekly grid of the resource | ✅ `test_fr07` + `model.test.ts` + `TimetableGrid.test.tsx` — both halves, see below |
| FR-14 | Table 15 | Two candidates of the same run | Reading of the sub-scores recorded for each | Table of the criteria with the two values and their difference | ✅ `test_fr14` — 8 tests |
| FR-16 | Table 17 | Ordered candidates of a run | Selection of the first, then verification of dominance | Candidate recommended and statement of the rule applied | ✅ `test_fr16` — 6 tests |

**Verified against this project's own design document** — no SRS row of either kind:

| FR | Source | Expected result | State |
|---|---|---|---|
| **FR-17** | `docs/scoring-and-explanation.md` §Dominance, as C-14 reworded it | A candidate another matches everywhere and beats somewhere is signalled, **wherever it sits in the portfolio** | ✅ `test_fr17` — ⚠️ **passing, and FR-17 is still `WIP`.** Whether a project-authored criterion may tick a requirement is a **project-owner ruling that has not been taken**; `docs/dashboard.md` records it. Phase 10 did not take it |

⚠️ **FR-3's row was true and its test did not fully bear it out until Phase 10.** The file re-derived
seven of the twelve rules and **named two of them by the wrong code** — the room-type check was called
H5 (it is **H4**) and the availability check H7 (it is **H6**), against
`data/instance/constraint_catalogue.csv`, which is the authority. A test that says H5 while checking H4
cannot support a claim of the form "respecting H1–H12": a reader auditing the twelve would tick two
rules that were never checked and miss two that were. **Every code now appears by its catalogue name**,
and **eleven of the twelve are re-derived from the placements** — including H2 and H11, which the
solver does not post separately (H2 is a subset of H12, H11 a consequence of H3 and H7 —
`solver/constraints/noop.py`) and which are checked here anyway, because what the requirement promises
is the *statement*, not the posting. **H10 alone is vacuous**: the reference instance locks no session,
which the file **asserts rather than assumes**, and `tests/integration/test_h10_locks.py` is what
exercises it for real.

⚠️ **Written at Phase 6's close and now half superseded — kept because the reasoning is what Phase 7
answers.** It read: *"The four assistant and regeneration rows were out of Phase 6's scope by decision
of the project owner, 2026-08-05, and Phase 6 is now closed — so they are simply NOT DELIVERED, and no
phase remains in which they were going to be."* ADR-010 commits FR-22, FR-23 and FR-24 to increment 1;
PPM Table 8 budgets them into no phase, which is C-1's ~2.5 unbudgeted days.

✅ **Phase 7 was approved on 2026-08-06 and is where they land.** **FR-23 is delivered** — M1 filled
H10's dormant gap (C-19) and M2 built the regeneration. The three assistant rows are M3–M5.

⚠️ **A figure worth carrying: the ~2.5-day estimate never costed FR-23.** ADR-010 itemises it as
*adapter + context builder + verifier ≈ 1.5 d, panel ≈ 0.5, report ≈ 0.5* — every line of that is
assistant work, and regeneration appears in none of it. The overrun the project carried for eight days
was understated, and it was understated because a figure was repeated rather than re-derived. **Do not read their absence as an oversight, and do not
read Phase 6's completion as covering them** — Phase 6 closed on 2026-08-06 with these four still unbuilt, which is why increment 1 did not close with it (**C-1**).

✅ **FR-13's test no longer conflicts with the specification.** It did: "three distinct candidates" can
fail while the system behaves correctly, if two profiles converge and duplicates are removed. **C-5 was
resolved on 2026-08-05** by tying the criterion to the verified reference instance at production
settings and leaving `services/portfolio.py` alone. The test asserts **exactly three**, not "at least
two" — the measurement is 3 distinct / 0 removed, and a weaker assertion would hide a regression.

⚠️ **FR-6, FR-10, FR-17 and FR-18 have no criterion of EITHER kind in the specification** (C-9) — no
Table 35 row *and* no §3.2 row. FR-17 has a testable criterion only because C-14's resolution reworded
`docs/scoring-and-explanation.md` §Dominance, which is this project's document and not the supervisor's,
which is why it sits in its own table above. **C-9 remains open for the other three.**

⚠️ **Do not read the §3.2 table above as making C-9 smaller.** It does the reverse: it shows exactly
what C-9's four are missing. FR-4, FR-7, FR-14 and FR-16 could be closed in Phase 10 *because* a
supervisor-written row existed to quote; FR-6, FR-10 and FR-18 cannot be, and no amount of working
software changes that. **The remedy for C-9 is a document, and it is not this repository's to write.**

⚠️ **FR-10 was BUILT in Phase 9 and still has no row above, deliberately.** Its software is finished,
reachable and covered by **28 display-layer tests** — `frontend/src/features/timetable/export.test.ts`
(22) and `PrintHeader.test.tsx` (6) — but an acceptance file opens with the criterion it verifies,
**quoted**, and there is no criterion to quote. Writing one would mean this project inventing the
promise it then declares itself to have met, which is the opposite of what this table is for. **A built
requirement with no acceptance row is the correct shape of a C-9 requirement**, not an oversight.

### How the suite is built · Phase 6 M2

`backend/tests/acceptance/`, one file per requirement, each opening with the criterion it verifies
**quoted**, so a reader checks the test against the promise rather than against the code.

- **Everything is driven through the HTTP API.** A requirement is `✓` only once a user can *reach* it,
  so a test calling `services/` or `analysis/` directly would assert the arithmetic and skip the claim.
- **Two engines, chosen per criterion.** Criteria about the ENGINE take real CP-SAT at production
  settings and are marked `solver`; criteria about the APPLICATION take a fake solver, because the
  engine is not what they are about and a 150-second solve would make the suite too slow to run.
- **One portfolio is shared** by FR-3, FR-13 and FR-19's first run — three questions about one run.
  FR-19 solves a second, because "repeat a run" is not a question one run can answer.

Run it with `scripts/run-acceptance.ps1`; `-FastOnly` skips the solver-marked half.

---

## Evaluating the weight adjustment — increment 2

Separate from the four above, because it evaluates a *learned* component and needs a different standard.

**Leave-one-out**: predict each comparison with weights fitted on the others, and compare the resulting
accuracy against that of the weights in force on the same comparisons.

**Adjusted weights are adopted only if their accuracy exceeds the weights in force** and the number of
comparisons reaches a threshold fixed *before* the experiment. Otherwise the weights in force are kept
and the result is recorded as **not established**.

The criterion is stated in advance and **can be failed** — that is the condition for the conclusion to
mean anything. Do not weaken it after seeing the data.

---

## Test layout

```
backend/tests/
  unit/         Pure functions, domain logic. No database, no solver
  property/     Hypothesis. The analysis-layer properties. No solver
  integration/  API + database. Solver with a small deterministic budget
  acceptance/   One test per FR acceptance criterion

frontend/src/**/*.test.tsx
                vitest + @testing-library/react. The DISPLAY layer
```

**Three markers, declared in `pyproject.toml`, and each exists because a whole class of test cannot
share the fast suite's constraints:**

| Marker | Why | How it runs |
|---|---|---|
| `solver` | Invokes CP-SAT on the real instance; can legitimately take minutes | Excluded from `run-checks.ps1`; `uv run pytest -m solver` |
| `database` | Needs a live PostgreSQL | Its own `run-checks.ps1` step. **Fails if no database was reached** — a forgotten `docker compose up -d` is actionable. **Skips** if Docker is absent. ⚠️ This said "fails if Docker is up but the container is not", and until Phase 6 M1 that was a description of an intention: the step checked the *daemon*, so a stopped container let all 38 tests skip under a green tick. It now requires the run to report tests that **passed** |
| `acceptance` | One test per FR criterion | `scripts/run-acceptance.ps1`. **Its 71 solver-free tests also run in `run-checks.ps1`** — a criterion that needs no engine has no reason to wait for one. The **35** that solve for real carry `solver` as well. ⚠️ **Derive these rather than trusting them**: `uv run pytest tests/acceptance --collect-only -q` and the same with `-m solver`. The figures here read 25 and 17 until 2026-08-06 and were two phases out of date |

⚠️ **Every test runs against in-memory stores unless it asks for a database.** `tests/conftest.py`
forces `OPTIEDT_PERSISTENCE=memory`, and that is not tidiness: when the default became `database`,
`test_availability_api.py` kept passing *and quietly wrote two rows into the developer's own
database*. A green suite that silently depends on PostgreSQL and mutates it is worse than a failing
one — it hides both facts. The database tests take an explicit session factory against a database of
their own (`optiedt_test`).

**What Phase 5 added, and the question each answers:**

| File | The question no other test answers |
|---|---|
| `unit/test_preanalysis.py` | Does SLOT_COVERAGE apply the **contiguity** bound? The C-13 regression reconstructs the pre-repair room mix and requires both shortfalls to be named |
| `integration/test_preanalysis_matches_verifier.py` | Do the two independent implementations of the five checks agree, figure for figure? |
| `unit/test_diagnosis.py` | Does the diagnosis name **exactly** the guilty rule — not "all four"? Asserts exact sets on instances where one rule can be at fault |
| `integration/test_store_contract.py` | Do the in-memory and PostgreSQL stores satisfy **one** contract? It caught a real divergence on its first run |
| `integration/test_rbac.py` | Does authentication work against **real tokens**? Every other API test overrides `current_user`; this one must not, or it would test the override |
| `integration/test_publication.py` | Does the trace match the **run** — rather than a second copy of the seed agreeing with itself? |
| `unit/test_seed.py` | Does the seed command **refuse** an installation that already has accounts? |

⚠️ **The frontend tests are not a fifth pyramid level; they answer a question no backend test can.**
Added in Phase 4 M5. The acceptance criterion is that the **displayed** contributions sum to the
**displayed** score difference — and rounding happens in the component, so a table could round each
term, print an unrounded total, and satisfy every backend test while failing the criterion on screen.
These render the table and read the figures back out of the DOM. They found exactly that defect on
their first run: rounding terms independently does not preserve the sum, and the column was out by one
unit of the last place. Fixed with largest-remainder rounding.

`tests/integration/test_api_runs.py` drives the run endpoints against a **fake solver**, so it stays in
the fast suite: what is under test there is the lifecycle and the wire format, not the engine. It waits
on the executor's `Future` rather than sleeping, so it carries no timing assumption.

The ITC-2007 harness itself lives in `backend/src/optiedt/validation/`, not under `tests/`, so that
mypy strict and ruff cover it — a validation harness whose arithmetic is wrong reports a wrong verdict
with full confidence. Its tests are in `tests/unit/test_itc2007_cost.py` (the rules, against
hand-computed values) and `tests/integration/test_itc2007_validation.py` (the archive's own solutions,
and a solve). The `benchmark-validation-is-not-product-code` import contract keeps the dependency
one-way.

Reproducibility note: every test that invokes the solver must fix the seed **and** use
`max_deterministic_time`, never a wall-clock bound (ADR-011). A test bounded by wall clock will pass on
one machine and fail on another, and the failure will look like a solver bug.

---

## What is never reduced

If the schedule slips, testing is cut in the order given in `docs/status.md`. These are never cut,
because they carry the demonstration that the application works **and that its results can be
justified**:

- The engine and its validation on published instances.
- Verification of the data before solving.
- Diagnosis of infeasible instances.
- The score and its decomposition.
