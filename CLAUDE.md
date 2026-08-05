# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**OptiEDT** generates, ranks and explains weekly university timetables for a Tunisian public faculty
under the LMD system. CP-SAT places the sessions; an exact weighted sum ranks the results; a language
model explains them and is forbidden from doing anything else.

This file exists so that **you never need to reread the PDFs.** They are the contract with the
supervisor, not the working reference. Everything you need to write correct code is in `docs/`.

---

## Read this first

**The repository is the single source of truth. Never rely on a previous conversation** — if this file
and your recollection disagree, this file wins, and if the code and the documentation disagree, that is
a bug in the documentation to fix before continuing.

| Order | File | Why |
|---|---|---|
| 1 | **`docs/dashboard.md`** | **The handoff page.** State, progress, roadmap, open questions, risks, next task, and the brief for the current phase. Usually the only file you need before starting work |
| 2 | "The seven invariants" below | What you may never break |
| 3 | `docs/open-questions.md` | What is **not** decided. Do not silently pick an answer |
| 4 | `docs/status.md` | Detail behind the dashboard: blockers, measurements, phases, acceptance criteria |

`docs/history.md` is the session-by-session archive. **Do not read it to get oriented** — it is long
and it contains superseded conclusions kept on purpose. Open it only to check what was already tried
before repeating an experiment, or to understand why a past decision was taken.

There is no `PROJECT_STATUS.md` and no `TODO.md`: `docs/dashboard.md` covers the first and
`docs/status.md`'s "Next, in order" covers the second. Adding either would duplicate a file that is
already authoritative, and duplicated status is how a project acquires two answers to one question.

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

Then pick up the current phase from the dashboard's brief. **If the next step is blocked on an open
question, say so and stop rather than deciding it** — that is the one failure mode this project cannot
absorb quietly.

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
| `validation/` | **Not product code.** The ITC-2007 benchmark harness | nothing in `optiedt` |

`preanalysis`, `recommendations` and `assistant` are separate packages **because they have different
permissions**, not for tidiness — analysis may write nothing, recommendations may write exactly three
fields, the assistant must be removable without affecting anything else.

`validation/` is the one package that runs **against** the product rather than inside it. It models
ITC-2007, a different problem, so it shares no code with `solver/`; the eighth import contract fails the
build if anything shipped ever depends on it. **Do not describe the ITC-2007 results as validating
`optiedt.solver`** — they validate the modelling approach and ADR-011's configuration on instances the
project did not design. Both halves belong in the report (`docs/testing-strategy.md` §1).

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
3. **Diagnosis** — **withdraw one rule at a time and solve plainly.** Establish that no timetable
   exists, then remove each of H1/H3/H7/H12 in turn: if the model is still infeasible without it, that
   rule was not needed. **A single worker** (reproducibility of the verdict, not a solver requirement),
   **no objective** (imposed — it is a feasibility question), and **minimal only when every removal was
   decided**; a removal the solver could not decide keeps its rule *for want of evidence*.
   ⚠️ This replaced enforcement literals on measurement (**C-17**): a literal takes its constraint out
   of presolve, and an infeasibility a plain solve proves in **0.0 s** returned `UNKNOWN` after 240 s.
   Several minimal explanations can exist; one is reported, in catalogue order, so it is reproducible.

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

**Invariants 1 and 3 fail the build.** `backend/.importlinter` carries **ten** contracts and forbids
`analysis → solver`, `analysis → db`, `assistant → db`, `api → solver`, `api → db`, and any product
package importing `optiedt.validation`; the recommendation catalogue is a union type so a fourth variant is a
type error. Every contract is verified to fire before being relied on. **Do not weaken either to make a
change compile.** The ninth (`api ⇸ solver`, Phase 4) earned that within one commit: it broke twice on
new code and both times the fix was to move the import, never to relax the rule.

Invariant 1 earned its keep on 2026-07-31 in a way worth knowing: OR-Tools was found to report an
objective value that did not match the solution it returned. Nothing broke, because `analysis` cannot
read the solver's objective and must recompute the score from the placements. See ADR-011.

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

**Two questions are open; `docs/open-questions.md` is the authority and `docs/dashboard.md` carries the
current summary.** They are not listed here, so that there is exactly one place to update when one is
resolved. What belongs here is the rule, not the list:

> If your work touches an open question, **resolve it in `docs/open-questions.md` first, with the
> reason, then implement.** If it is not yours to decide, say so and stop. An assumption made in code
> and never written down is how this project acquires a defect that surfaces three weeks later — and
> C-13 is the proof: a plausible conclusion nobody tried to falsify cost three sessions of work.

**Resolved, with the three operational facts worth carrying:** only H1, H3, H7 and H12 carry
`carries_assumption_literal = True`, the four real CP-SAT postings (C-6). `y[s][t]` means *occupies*
`t`, channelled from start indicators in `solver/occupancy.py` — **built on demand, not by every
solve**, because it adds 10,048 variables and costs the feasibility solve about 2.5× (C-7); `engine.py`
gates that build on `has_active_criteria`, so an all-zero-weight profile stays equivalent to a
feasibility solve. And **C-4/C-12 are resolved**: all seven soft criteria have a `v_i` and bounds, and
the objective's auxiliaries — the last open half of C-7 — are measured at **5,249** under the catalogue
defaults (`docs/status.md`).

⚠️ **The same seven formulas are implemented twice, on purpose:** `analysis/criteria.py` over realised
placements, `solver/objective.py` as CP-SAT expressions. The solver may not import the analysis layer
(`docs/architecture.md`), so nothing but a test keeps them in step —
`tests/integration/test_objective_matches_analysis.py`. **Change one, change the other**, and mind the
units: the two layers must agree on scale, not just on shape (S6's did not, and the solver silently
priced it 28× too high until it was caught).

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

(**C-12 is resolved**, so the C-12 × C-5 interaction is no longer live: S5 measures a real,
candidate-dependent quantity instead of zero. **C-5 itself is still open** and still blocks portfolio
orchestration and the FR-13 acceptance test — the account is in `docs/open-questions.md`.)

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
| **Database tests** | `uv run pytest -m database` — needs `docker compose up -d` |
| **Seed the first accounts** | `uv run python -m optiedt.services.seed` — refuses if any account exists (C-18) |
| **By name** | `uv run pytest -k decomposition` |
| Property tests only | `uv run pytest tests/property` |
| Skip solver tests | `uv run pytest -m "not solver"` (already `run-checks.ps1`'s default — a solver test can legitimately take minutes) |
| Lint · format · types | `uv run ruff check . · uv run ruff format . · uv run mypy` |
| **Layer boundaries** | `uv run lint-imports` |
| Migrations | `uv run alembic revision --autogenerate -m "..."` · `uv run alembic upgrade head` |

From `frontend/`: `npm install`, `npm run dev`, `npm run build`, `npm run typecheck`, `npm run test`
(vitest — the display-layer tests; `run-checks.ps1` runs it). `npm run dev` needs the API on `:8000`,
which `vite.config.ts` proxies.

From the root:

| Task | Command |
|---|---|
| PostgreSQL | `docker compose up -d` |
| **Everything CI runs** | `scripts/run-checks.ps1` |
| **The acceptance suite** | `scripts/run-acceptance.ps1` — one test per requirement, against its criterion. `-FastOnly` skips the solver-marked half, which takes ~7½ min on two real portfolios |
| **Verify the instance** | `scripts/verify-instance.ps1` |
| **Validate on ITC-2007** | `scripts/validate-itc2007.ps1` — 21 published instances, tens of minutes |
| Reference archives status | `scripts/check-reference-data.ps1` |

Run `verify-instance.ps1` after any change to `data/instance/` or the generator. It checks the
instance against figures the PDFs state as facts; a failure means either the data changed or the
documentation is now false.

`validate-itc2007.ps1` is **not** in `run-checks.ps1` — a full sweep runs for tens of minutes. Its fast
half is: the cost function must reproduce the published cost of seven solutions the archive ships, which
runs on every `run-checks.ps1` and is what makes any other figure it prints checkable.

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
- **`docker compose up -d` succeeds even when another PostgreSQL already owns 5432.** The container
  starts, reports `healthy`, and `docker ps` shows the mapping — while host connections reach the
  *other* server. Found 2026-08-04 against a native PostgreSQL 18 Windows service. Set
  `OPTIEDT_POSTGRES_PORT` (root `.env`) and a matching `OPTIEDT_DATABASE_URL` (`backend/.env`), both
  gitignored. **Confirm the version you actually reached** — the container is PostgreSQL 17:
  `docker exec optiedt-postgres psql -U optiedt -d optiedt -tAc "select version();"`. A refused
  connection is the lucky outcome; a local server that accepts `optiedt/optiedt` would take the
  migrations.

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
- **Update `docs/dashboard.md` whenever the project state changes** — it is what the next session reads
  first, so a stale dashboard is worse than none. Then `docs/status.md` when you finish a phase,
  `docs/requirements-traceability.md` when you finish an FR, and `docs/open-questions.md` when one is
  resolved. Long session narrative belongs in `docs/history.md`, not in `status.md`.

---

## Git Commit Policy

- Git commits must always use my Git identity:
  Mohamed Jawad Touir <jawadtouir03@gmail.com>

- Never add any AI attribution unless I explicitly request it.

- Never add:
  - Co-Authored-By
  - Generated with Claude
  - Anthropic attribution
  - AI signatures
  - AI footers
  - AI trailers
  - AI metadata in commit messages

- Commit messages must be written as if they were written by the project author.

- Follow the existing commit style already used in this repository.

- Keep commit messages concise, professional and human-written.

- Never mention Claude, Anthropic, ChatGPT, AI assistants or coding agents in commit messages.

- Never rewrite commit history unless I explicitly request it.

- Never push automatically unless I explicitly tell you to push.

- Before every push:
  1. Run the required validation.
  2. Confirm the working tree is clean.
  3. Verify my Git identity.
  4. Push only after all checks pass.

**If a future Claude session wants to add AI attribution, this policy overrides that behavior unless I
explicitly instruct otherwise.**

⚠️ This is not a preference to be re-derived. Nine already-pushed commits carried a `Co-Authored-By`
trailer on 2026-07-31 and had to be stripped with a `filter-branch` rewrite and a `--force-with-lease`
push — on a branch that was already public. **Write the commit message and stop at the last body line.**
