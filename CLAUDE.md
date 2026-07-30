# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**OptiEDT** generates, ranks and explains weekly university timetables for a Tunisian public faculty
under the LMD system. CP-SAT places the sessions; an exact weighted sum ranks the results; a language
model explains them and is forbidden from doing anything else.

This file exists so that **you never need to reread the PDFs.** They are the contract with the
supervisor, not the working reference. Everything you need to write correct code is in `docs/`.

---

## Read this first

| Order | File | Why |
|---|---|---|
| 1 | `docs/status.md` | Where the project actually is. Done, next, blocked |
| 2 | "The seven invariants" below | What you may never break |
| 3 | `docs/open-questions.md` | What is **not** decided. Do not silently pick an answer |

Then, on demand:

| Working on | Read |
|---|---|
| Anything structural | `docs/architecture.md` |
| Entities, database, migrations | `docs/domain-model.md` |
| The CP-SAT model, constraints, diagnosis | `docs/constraint-model.md` |
| Scores, ranking, contributions, dominance | `docs/scoring-and-explanation.md` |
| Recommendations, regeneration, the assistant | `docs/ai-integration.md` |
| The generator or the instance files | `docs/data-and-instance.md` |
| Tests | `docs/testing-strategy.md` |
| "Is FR-N built?" | `docs/requirements-traceability.md` |
| "Why was X chosen?" | `docs/decisions/` (ADRs) |

**Never** open `docs/specifications/*.pdf` to answer a question. If the answer is not in `docs/`, that
is a gap in `docs/` — fix the gap, then continue.

---

## Architecture

### The one idea everything follows from

Two decisions of **different natures**, kept strictly apart:

| | Decision | Cost of an error | Method |
|---|---|---|---|
| 1 | Which session → which slot + room | An unpublishable timetable | CP-SAT, correct by construction |
| 2 | Which valid timetable is better | A worse ranking, still usable | Weighted sum, exact and hand-recomputable |

Methods that **guarantee** go on decision 1. Methods that **estimate** go on decision 2. The language
model is admitted only because it touches neither. When a change seems to require blurring that line,
the change is wrong.

### Layers, and the edges that must not exist

```
React ──HTTPS/JSON/token──► FastAPI ──► PostgreSQL
                               │
        ┌──────────────────────┼───────────────────────┐
        ▼                      ▼                       ▼
  preanalysis/            solver/                  analysis/
  5 arithmetic checks     CP-SAT — the ONLY        sub-scores, ranking,
  NO solver               thing that places        decomposition, dominance
                          a session                NO solver · NO placement
                               ▲                       │
                               └──── recommendations/ ─┘
                                     writes a weight, a lock,
                                     an exclusion — never a placement

  assistant/  context payload in → text out.  NO database.  NO figure of its own.
```

| Package | Role | Depends on |
|---|---|---|
| `domain/` | Entities, enums. **Pure** — no I/O, ORM or framework | — |
| `core/` · `db/` · `api/` · `services/` | Config/security · ORM · routers+RBAC · use cases | `domain` |
| `preanalysis/` | The five checks. Stage 1 of every run | `domain` |
| `solver/` | Variables, constraints, objective, diagnosis | `domain` |
| `analysis/` | Criteria, scoring, ranking, decomposition | `domain` |
| `recommendations/` | Closed catalogue, translation to solver input | `domain`, `analysis` |
| `assistant/` | Adapter, context builder, answer verifier | `domain`, `analysis` |
| `tasks/` | Background run executor | `services` |

`preanalysis`, `recommendations` and `assistant` are separate packages **because they have different
permissions**, not for tidiness — analysis may write nothing, recommendations may write exactly three
fields, the assistant must be removable without affecting anything else.

### The generation pipeline — three stages

Stages 1 and 2 always run. **Stage 3 runs only when stage 2 returns `INFEASIBLE`.**

1. **Pre-analysis** — five arithmetic checks, no solver. Distinguishes *this instance genuinely has no
   solution* from *the model has a bug*. The reference instance sits at **90.9% computer-laboratory
   occupancy — of two-period *windows*, 8 spare in the whole week**, which is the figure that binds.
   Counting periods instead gives a reassuring 71.4% and is **necessary but not sufficient**: a
   two-period session needs two consecutive open periods inside one day, so a 5-period day leaves one
   period per room structurally unusable. Reading the period figure alone is what let an infeasible
   instance pass verification and cost three sessions (C-13). **Run this first when debugging, and
   check that a solution exists before concluding the solver is slow.**
2. **Optimisation** — one solve per weight profile, sequential, carries the objective, all workers,
   bounded by `max_deterministic_time` (ADR-011).
3. **Diagnosis** — three properties imposed by CP-SAT itself, not choices: **a single worker**
   (assumptions admit no parallelism), **no objective** (with one, the whole assumption set comes back
   and the mechanism is useless), and the result is **sufficient, not minimal** — never present it as
   the smallest conflict set.

### Run lifecycle — asynchronous by necessity

Solving takes minutes; no HTTP request is held open for it.

```
POST /runs → 202 {run_id}   → background task → poll GET /runs/{id}
PENDING → PREANALYSIS → SOLVING → SCORING → COMPLETED
                              └→ INFEASIBLE → DIAGNOSING → DIAGNOSED
                              └→ FAILED
```

### Scoring — why linearity is load-bearing

```
n_i(k)  = 1 − (v_i(k) − min_i) / (max_i − min_i)     1 = best
score(k)= 100 × Σ(w_i × n_i(k))
score(A) − score(B) = 100 × Σ(w_i × (n_i(A) − n_i(B)))
```

That third line **is** the explanation feature: the contribution shown to the user is the score
calculation read term by term, not an approximation of it. **Any change making the score non-linear
destroys it** — a product term, a threshold or a max removes the reason the ranking is defensible.
Bounds come from the *instance*, never from the candidates a run produced (ADR-009).

---

## The seven invariants

Each is a stated requirement in the specification. Breaking one is a correctness bug, not a
code-review comment.

1. **The analysis layer may not import the solver.** This is what makes an analysis bug produce a
   wrong *order* instead of an invalid *timetable*. If you want this import, the design is wrong, not
   the lint rule.
2. **Nothing outside the solver ever writes a placement.** Not analysis, not recommendations, not the
   assistant, not a user.
3. **A recommendation is one of exactly three actions** — `weight_delta`, `lock_session`,
   `exclude_slot`. Accepting one launches a **new run through the same solver** with one input
   changed, never an edit.
4. **The assistant never receives a database connection and never produces a figure.** Every number in
   its answer must appear in the context it was given, or the answer is discarded.
5. **Everything works with the assistant switched off.** Only text disappears.
6. **A candidate is immutable once recorded.** A regenerated timetable is a *new* candidate under a
   *new* run.
7. **Institutional calendar rules are configuration, never constraints.** A closed half-day sets
   `slot.is_open = 0` and H9 does the rest; a shortened-day window shifts *displayed* hours only.
   Adding a CP-SAT constraint for Ramadan or a closed Saturday is a bug (ADR-003).

**Invariants 1 and 3 fail the build.** `backend/.importlinter` forbids `analysis → solver`,
`analysis → db`, `assistant → db`; the recommendation catalogue is a union type so a fourth variant is
a type error. Both are verified to fire. **Do not weaken either to make a change compile.**

---

## Decided — do not reopen

Read the ADR before arguing with any of these.

| ADR | Decision |
|---|---|
| 001–002 | CP-SAT for assignment · weighted sum for ranking, dominance as complement |
| 003–005 | Calendar as configuration · one deployable unit · in-process background task |
| 006–007 | The LLM does not place, score or rank · closed 3-action catalogue |
| 008 | Generated instance; public sources given roles, never merged |
| 009–011 | Instance-derived bounds · assistant in increment 1 · `max_deterministic_time` |

## Open — do not silently decide

| # | Open | Blocks |
|---|---|---|
| C-4 | `v_i` and the bounds of **all seven** soft criteria are undefined. **This is the current blocker** — Phase 2 is done and nothing further can be encoded without it | Scoring, everything downstream |
| C-12 | **S5 carries weight 0.20 and has no input data** — no "preferred" state in the schema | Scoring, availability grid |
| C-5 | "At least three candidates" can fail when duplicates are removed | Acceptance tests |
| C-9 | FR-6, FR-10, FR-17, FR-18 have no detailed specification | Acceptance |

**C-6 is resolved and implemented**: only H1, H3, H7 and H12 carry `carries_assumption_literal = True`
— the four constraints that are real CP-SAT postings.

**C-7 is resolved and implemented**: `y[s][t]` means *occupies* `t`, channelled from start indicators
`x[s,t₀]` in `solver/occupancy.py`. **It is built on demand, not by every solve** — it adds 10,048
variables and costs the feasibility solve about 2.5×, so nothing pays for it until an objective reads
it. Half of C-7 stays open under C-4: the objective's auxiliary variables cannot be counted until the
criterion formulas exist.

**C-13 is resolved, and how it was resolved matters more than the answer.** For three sessions it was
recorded as "room-assignment symmetry makes the correct model hard to solve", and three legitimate
techniques were spent on it. The model was correct; the **instance had no solution**. Every laboratory
session spans two periods, a two-period session must fit inside one day (H8), and a 5-period day gives
a room only two such windows — so a room offered 11 a week against demand that needed more.
Ten minutes of arithmetic on the CSVs found what days of solver time could not, because CP-SAT was
being asked to prove an infeasibility its propagators cannot express. **When a solve returns `UNKNOWN`,
establish that a solution exists before treating it as a performance problem** — an instant
`INFEASIBLE` is evidence of a too-tight model, but its *absence* is not evidence of a sound instance.
Full account in `docs/open-questions.md`.

⚠️ **C-12 and C-5 are the same bug waiting to happen.** The teacher-favouring profile differs by
raising S3 *and* S5. If S5 measures identically zero it differs by S3 alone, two candidates converge,
duplicate removal drops one, and the three-candidate acceptance test fails — for a reason nobody would
look for, because the symptom is "the portfolio is boring" and the cause is a missing column.

If your work touches one of these, **resolve it in `docs/open-questions.md` first**, then implement.
An assumption made in code and never written down is how this project acquires a defect that surfaces
three weeks later.

---

## Commands

Setup: `scripts/bootstrap.ps1` (checks prerequisites, installs both stacks, starts PostgreSQL).

From `backend/`:

| Task | Command |
|---|---|
| Sync deps | `uv sync --all-extras` |
| Run the API | `uv run uvicorn optiedt.api.main:app --reload` |
| All tests | `uv run pytest` |
| **One file** | `uv run pytest tests/unit/test_scoring.py` |
| **One test** | `uv run pytest tests/unit/test_scoring.py::test_decomposition_is_exact` |
| **By name** | `uv run pytest -k decomposition` |
| Property tests only | `uv run pytest tests/property` |
| Skip solver tests | `uv run pytest -m "not solver"` (already `run-checks.ps1`'s default — a solver test can legitimately take minutes) |
| Lint · format · types | `uv run ruff check . · uv run ruff format . · uv run mypy` |
| **Layer boundaries** | `uv run lint-imports` |
| Migrations | `uv run alembic revision --autogenerate -m "..."` · `uv run alembic upgrade head` |

From `frontend/`: `npm install`, `npm run dev`, `npm run build`, `npm run typecheck`.

From the root:

| Task | Command |
|---|---|
| PostgreSQL | `docker compose up -d` |
| **Everything CI runs** | `scripts/run-checks.ps1` |
| **Verify the instance** | `scripts/verify-instance.ps1` |
| Reference archives status | `scripts/check-reference-data.ps1` |

Run `verify-instance.ps1` after any change to `data/instance/` or the generator. It checks the
instance against figures the PDFs state as facts; a failure means either the data changed or the
documentation is now false.

**Any test that invokes the solver must fix the seed *and* use a deterministic budget.** A test bounded
by wall clock passes on one machine and fails on another, and the failure looks like a solver bug.

### Three traps that will waste your time

- **`pytest` exits 5** while there are no tests. `run-checks.ps1` tolerates it; remove `5` from the
  allowed list once the first test lands.
- **`.gitignore` inherits GitHub's Python template**, which contains `instance/` (meaning Flask's
  instance folder) and matches at any depth. It silently swallowed `data/instance/` — the whole
  dataset. There is an explicit un-ignore for it, plus one for `/dataset/`. **Do not remove either**,
  and check `git status` after adding data files.
- **Solving with `num_workers=0` (the default) uses every CPU core** and can make unrelated shell
  commands stall for tens of seconds to minutes — this is expected, not a hung environment. Always
  track a backgrounded solve explicitly and stop it before starting a replacement; an abandoned one
  silently burns CPU for the rest of the session and looks exactly like broken tooling.

---

## How to do the things you will actually be asked to do

**Add a hard constraint.** Next free `H` code — codes are permanent, never reused. Add the row to
`data/instance/constraint_catalogue.csv` with its XHSTT reference if one exists. Implement in
`optiedt/solver/`. Decide whether it gets its own assumption literal — **it should not if it overlaps
another constraint** (C-6: redundant literals make the conflict report name a rule the user cannot act
on).

**Add a soft criterion.** Next free `S` code — **`S1`, `S8`, `S9` are retired and must never be
reused.** Implement the `Criterion` Protocol, which requires `raw_value` *and* `bounds` together so a
criterion cannot be half-defined. Add its default weight to the catalogue; profile weights are
renormalised to sum to 1 before any score is computed.

**Change a time limit.** It is a *deterministic* budget, not seconds (ADR-011). The wall-clock ceiling
is a hang backstop, not the primary bound. The deterministic-to-wall-clock ratio is machine-dependent
— see `docs/status.md`.

**Touch the assistant.** Preserve invariants 4 and 5. Verify degraded mode by switching the service off
in config and confirming every other function is unaffected.

---

## Conventions

- **French domain vocabulary is kept verbatim in code**, matching the instance CSVs: `SessionType`
  `CM`/`TD`/`TP`; `GroupLevel` `PROMO`/`TD`/`TP`; `RoomType` `Amphi`/`Salle`/`Lab_Info`/`Lab_Sciences`;
  `TeacherRank` `Professeur`/`Maitre de Conferences`/`Maitre Assistant`/`Assistant` (unaccented, as the
  files carry them). Translating these into English creates a mapping layer between the application and
  its own data for no benefit.
- Python 3.12+, full type annotations, `from __future__ import annotations`, `mypy` strict.
- The domain layer is pure — no I/O, no ORM, no framework imports.
- **Update `docs/status.md` when you finish a phase** and `docs/requirements-traceability.md` when you
  finish an FR. A stale status file is worse than none, because the next session trusts it.
