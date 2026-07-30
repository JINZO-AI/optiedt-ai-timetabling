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

The engine is tested on the **curriculum-based track of ITC-2007**, for which results are published.

Two things are examined: that no timetable produced violates a hard constraint, and the distance
between the cost obtained and the best known results.

**The objective is not to beat published results** — that would not be realistic in four weeks. It is
to show that the engine produces valid timetables of reasonable quality **on instances it was not built
around**. An engine validated only on its own generated instance has demonstrated nothing.

For the examination module, the same procedure on Track 1 instances — after verifying them. Track 1 has
not been opened yet; **assume no property of it before that verification**.

Archives live in `data/reference/`, gitignored and **already present** — 21 ITC-2007 Track 3 instances
and 25 XHSTT instances, verified. Run `scripts/check-reference-data.ps1` to confirm, and see
[`PROVENANCE.md`](../data/reference/PROVENANCE.md) for what verification found.

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
| Detection of dominance | A candidate improved on every criterion is signalled |
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
```

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
