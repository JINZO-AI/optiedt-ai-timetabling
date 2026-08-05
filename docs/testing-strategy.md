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

| FR | Test | Expected result |
|---|---|---|
| FR-2 | Fill in the availability grid | Recorded in under 5 minutes |
| FR-3 | Generate on the reference instance | No hard-constraint violation |
| FR-5 | Read a candidate | Overall score and sub-scores displayed |
| FR-8 | Generate on a deliberately infeasible instance | Report naming the rules in conflict by code |
| FR-9 | Close a half-day in configuration | Those slots disappear from every timetable, **with no code change** |
| FR-11 | Connect with a teacher account | Access limited to own data |
| FR-12 | Verify an instance with insufficient rooms | The resource concerned and quantity missing are named |
| FR-13 | Run on the reference instance | Three distinct candidates ⚠️ *see C-5* |
| FR-15 | Compare two candidates | Sum of contributions equals the score difference |
| FR-19 | Repeat a run with the same seed and weights | Identical candidates in the same order |
| FR-23 | Accept a `weight_delta` recommendation | New run created; new candidate satisfies H1–H12; linked to the recommendation |
| FR-24 | Ask a question whose answer is not in the context | The assistant says it cannot answer, and **invents no figure** |
| FR-22, FR-25 | Switch the language service off in configuration | Explanations and reports fall back to computed form; **every other function unaffected** |

⚠️ **FR-13's test currently conflicts with the specification.** "Three distinct candidates" can fail
while the system behaves correctly, if two profiles converge and duplicates are removed. Resolve **C-5**
before writing it.

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
| `acceptance` | One test per FR criterion | Phase 6 |

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
