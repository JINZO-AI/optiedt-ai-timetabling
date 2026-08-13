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
| 2 | **`docs/project-roadmap.md`** | **"What phase are we in?"** — the whole project as ONE continuous phase sequence, Phase 1 to the final phase. The project owner's tracking view. Answers *what is left before Phase N is complete* without needing increments, milestones or requirement codes |
| 3 | "The seven invariants" below | What you may never break |
| 4 | **"The frontend" below** | **The V2 interface is a FROZEN baseline.** Read before touching anything under `frontend/` |
| 5 | `docs/open-questions.md` | What is **not** decided. Do not silently pick an answer |
| 6 | `docs/status.md` | Detail behind the dashboard: blockers, measurements, phases, acceptance criteria |
| 7 | `docs/PROJECT_STATUS.md` | **The release-freeze record.** What was verified, when, and by what measurement. Not a second state page — see the note under the dashboard rule below |

`docs/history.md` is the session-by-session archive. **Do not read it to get oriented** — it is long
and it contains superseded conclusions kept on purpose. Open it only to check what was already tried
before repeating an experiment, or to understand why a past decision was taken.

⚠️ **Do not add a `PROJECT_STATE.md` or `TODO.md`.** Their jobs are already taken: `docs/dashboard.md`
is the state page and `docs/status.md`'s "Next, in order" is the task list. A fourth name for the same
content does not make the project easier to resume — it makes it impossible to tell which of two files
is lying when they disagree. **If the dashboard is hard to resume from, fix the dashboard.**

> ⚠️ **One documented exception, added at the release freeze on 2026-08-13 by the project owner:
> `docs/PROJECT_STATUS.md` exists.** This rule named it as forbidden until then, and the exception is
> recorded here rather than by quietly deleting the rule. It is admitted on one condition, which the
> file itself repeats at its head: **it is a dated release-verification record, not a state page.** It
> says what was measured and when. It does **not** carry phase, progress, next task or requirement
> status — those stay in `docs/dashboard.md`, which remains the single place project state lives. If
> `PROJECT_STATUS.md` ever starts answering "what phase are we in?", it has become the second state
> page this rule exists to prevent, and the fix is to cut that content out of it.

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
| **Showing the system to someone** — and the two acts only a person can perform: the timed FR-2 walkthrough (§2) and the **first live language-provider call** (§4) | `docs/demonstration.md` |

**Never** open `docs/specifications/*.pdf` to answer a question. If the answer is not in `docs/`, that
is a gap in `docs/` — fix the gap, then continue.

### Startup workflow — do this, in this order

1. **Read `docs/dashboard.md`. This step is not optional** — it is the *only* place the project's
   current state exists, deliberately. Its "At a glance" table gives the current phase, the milestone
   reached, the current goal and the next task. A session that skips it is working blind, because this
   file will not tell you what has been built.
2. **Derive the repository facts rather than reading them** — no document records a SHA or a commit
   count, deliberately, because neither can survive a push that does not touch the file recording it:
   `git fetch` · `git log -1 --oneline` · `git rev-list --count origin/main..HEAD`.
3. **Run `scripts/run-checks.ps1` before changing anything.** It is the ground truth for whether the
   repository is green, and it takes about a minute. ⚠️ Start `docker compose up -d` first, or the
   database step skips and FR-19's persistence is not covered.
4. **Check the dashboard's "Next task" row before writing code.** It says explicitly when the next
   action is a *decision* rather than an implementation.

> ⚠️ **No project state is recorded in this file — it lives in `docs/dashboard.md`'s "At a glance".**
> This file carries what is *permanently* true; the dashboard carries what is true *today*. Two places
> recording state is how a project acquires two answers to one question, and this repository has been
> bitten by exactly that: `README.md`'s Status section went stale in two successive phases, and the
> dashboard's own "Overall progress" row survived two closing audits while describing a phase that had
> already finished. **If you find state here, it is a bug — move it to the dashboard.**
>
> **Four standing rules that outlive any phase:**
>
> 1. **Do not open a new phase or increment without the project owner's approval.** Where remaining
>    work goes is their call, never a session's.
> 2. **If the next step is blocked on an open question, say so and stop rather than deciding it** —
>    the one failure mode this project cannot absorb quietly.
> 3. **Do not read a green suite as "the assistant was tested against a language model."** No test
>    calls a live provider and none can — a model's output is not fixed by a seed (**C-21**). What is
>    verified is the application's behaviour *around* a provider.
> 4. **A requirement is `✓` only once a user can reach it *and* it is tested end to end.** Do not
>    promote a status because a phase closed.

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
| `instance/` | Loads the 13 CSVs; **verifies a supplied department dataset (FR-1)** | `domain` |
| `preanalysis/` | The five checks. Stage 1 of every run | `domain` |
| `solver/` | Variables, constraints, objective, diagnosis — the WEEKLY model | `domain` |
| `examination/` | **FR-20's model, PARALLEL to `solver/` and sharing no variable schema with it.** An examination takes one or more rooms (R-6) over the examination period; a session takes one room over the week | `domain` |
| `analysis/` | Criteria, scoring, ranking, decomposition | `domain` |
| `recommendations/` | Closed catalogue, translation to solver input | `domain`, `analysis` |
| `assistant/` | Adapter, context builder, answer verifier, computed forms | `domain`, `analysis` |
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

Stages 1 and 2 always run. **Stage 3 runs only when stage 2 returns `INFEASIBLE`.** The stages are
specified in full in **`docs/architecture.md`**; what must be loaded at all times is the debugging rule
they exist to serve:

⚠️ **When a solve returns `UNKNOWN`, establish that a solution EXISTS before treating it as a
performance problem.** Run pre-analysis first, always, and read the **two-period-window** occupancy
(90.9 % on the reference instance, 8 spare in the whole week) rather than the period figure (a
reassuring 71.4 %). The period bound is necessary and **not sufficient**; reading it alone let a
genuinely infeasible instance pass verification and cost three sessions (**C-13**). An instant
`INFEASIBLE` is evidence of a too-tight model — its *absence* is not evidence of a sound instance.

```
POST /runs → 202 {run_id}   → background task → poll GET /runs/{id}
PENDING → PREANALYSIS → SOLVING → SCORING → COMPLETED
                              └→ INFEASIBLE → DIAGNOSING → DIAGNOSED
                              └→ FAILED
```

Solving takes minutes; no HTTP request is ever held open for it (ADR-005).

### Scoring — why linearity is load-bearing

`score(A) − score(B)` decomposes **exactly** into per-criterion contributions, because the score is a
weighted sum of normalised values. That identity *is* the explanation feature: what the user sees is
the score calculation read term by term, not an approximation of it.

⚠️ **Any change making the score non-linear destroys it** — a product term, a threshold or a `max`
removes the reason the ranking is defensible before a department. Bounds come from the *instance*,
never from the candidates a run produced (ADR-009). Formulas and the four required properties:
**`docs/scoring-and-explanation.md`**.

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

**Invariants 1 and 3 fail the build.** `backend/.importlinter` carries **thirteen** contracts and forbids
`analysis → solver`, `analysis → db`, `assistant → db`, `assistant → solver`, `recommendations → solver`,
`api → solver`, `api → db`, `api → examination`, `examination → solver`, and any product
package importing `optiedt.validation`; the recommendation catalogue is a union type so a fourth variant is a
type error. Every contract is verified to fire before being relied on. **Do not weaken either to make a
change compile.** The ninth (`api ⇸ solver`, Phase 4) earned that within one commit: it broke twice on
new code and both times the fix was to move the import, never to relax the rule. The eleventh
(`recommendations ⇸ solver`, Phase 7 M2) keeps FR-23's guarantee honest: a translator that could build
and run a `SolverInput` itself would turn "a new run through the same engine" into a private solve with
no run id, no seed and no trace. The **twelfth and thirteenth** (Phase 13) keep `api` off the
examination solver — same reason as the ninth — and keep the examination model off the weekly solver
and the analysis layer, which is what stops "parallel model" from quietly becoming "second entry point
into the weekly one" (R-6). Both were verified to fire by injecting a violation.

Invariant 1 earned its keep on 2026-07-31 in a way worth knowing: OR-Tools was found to report an
objective value that did not match the solution it returned. Nothing broke, because `analysis` cannot
read the solver's objective and must recompute the score from the placements. See ADR-011.

---

## The frontend

**React 18 + Vite 5 + react-router-dom 6 + TanStack Query 5. Plain CSS, no framework, no UI library.**
`npm run dev` needs the API on `:8000`, which `vite.config.ts` proxies.

### ⚠️ The V2 interface is a FROZEN baseline

It was accepted by the project owner on **2026-08-13** after two full design passes and is **not** to be
redesigned, restyled or migrated without their explicit instruction. That includes: do not introduce
Tailwind, shadcn, Material, Bootstrap or Next.js; do not change the palette, the typeface pairing or the
navigation model "to try something". `docs/DESIGN_SYSTEM.md` is what the system *is*;
`docs/UX_DECISIONS.md` is *why* — and several of its entries record a specific defect that a plausible
"improvement" would reintroduce. **Read `UX_DECISIONS.md` before changing a visual decision**; the
reasons are not aesthetic preferences and they are not recoverable by looking at the screen.

### The three rules a change must not break

1. **`--mono` is for FIGURES, CODES AND IDENTIFIERS ONLY** — a score, an hour, a run id, `S2`, `H9`,
   `X1`, a room code, an environment variable. Not labels, not headings, not navigation. V1 used mono
   for all of those and the product read as a terminal.
2. **`--ink-5` is borders, icons and marks. It is never text.** `--ink-4` is the faintest tone any text
   may use (5.6:1 on white). V2 broke this rule on its own first write and five elements measured
   2.55–2.64:1; an automated sweep caught them and visual judgement had not.
3. **COMPUTED BY OPTIEDT and EXPLAINED BY AI must stay visibly different.** See invariant 4 and
   `docs/AI_BEHAVIOR.md`. The assistant panel's origin label goes *above* the text it labels, never
   beside or below it.

### Layout

| Piece | What it is |
|---|---|
| `src/App.tsx` | The shell: a 244 px grouped rail (Timetabling / Inputs / Institution) and the route table. `NAV` declares which roles are *offered* each entry — ⚠️ **display only; the API checks the role itself (FR-11)** |
| `src/shell/Page.tsx` | Every screen's frame: a **sticky page bar** carrying the title, a one-line subtitle, live status, and **the screen's single primary action**. The header belongs to the screen, not the shell, so a screen rendered alone in a test is complete |
| `src/shell/icons.tsx` | The icon set and the brand mark, drawn from the product's own subject (a week of slots with sessions placed in it) |
| `src/styles.css` | A 33-line entry point. Six layers in `src/styles/`: `tokens` → `base` → `primitives` → `shell` → `patterns` → `print`. **Order is load-bearing** |

### Screens, and the route each answers

| Route | Screen | Roles offered it | Requirement |
|---|---|---|---|
| `/generate` | Launch a run; pipeline, run vitals, ranked candidates, pre-analysis | Officer | FR-13, FR-5, FR-6, FR-12 |
| `/timetables` | Four views of a candidate — by teacher, group, room, room occupancy | Officer, Admin, Teacher | FR-7, FR-18, FR-10 |
| `/compare` | Head-to-head, the decomposition ledger, dominance, regeneration, the assistant | Officer, Admin, Teacher | FR-14, FR-15, FR-17, FR-23 |
| `/examinations` | Generate and read an examination session | Officer | FR-20 |
| `/publications` | Published timetables with full provenance | Officer | FR-19 |
| `/data` | Replace the department dataset; the rejected-line report | Officer | FR-1 |
| `/availability` | A teacher's weekly declaration | Officer, Admin, Teacher | FR-2 |
| `/administration` | Academic calendar and accounts, on two tabs | Admin | FR-9, FR-11 |
| `/my-timetable` | A student's own group's published week | Student | SRS Table 2 |

`landingFor(role)` decides where `/` sends each role. ⚠️ `App.tsx` waits for `useCurrentUser` to
resolve before rendering the shell — the redirect used to fire on the fallback and land an officer on
the availability screen.

### Data flow

```
Screen (React)                      one hook per endpoint, in src/api/queries.ts
   │  useRun / useComparison / useAskAssistant …
   ▼
src/api/client.ts                   the ONLY module that knows the API is at /api
   │  bearer token from sessionStorage; ApiError on non-2xx
   ▼
Vite proxy (dev)  →  FastAPI  /api/*
   │
   ├─ api/routers/*        RBAC checked HERE, per endpoint (FR-11)
   ├─ services/*           use cases
   ├─ solver/ examination/ CP-SAT — the only thing that places a session
   ├─ analysis/            scores, ranking, decomposition, dominance
   ├─ assistant/           context in → text out. No database. No figure of its own
   └─ db/                  PostgreSQL via SQLAlchemy + Alembic
   ▼
JSON  →  TanStack Query cache  →  screen
```

⚠️ **The presentation layer may "display, filter, print, ask" and may not "compute a score, decide an
order"** (`docs/architecture.md`). Bar widths and the two ledger highlights are pixels and selections
derived from figures the API already sent; nothing in `frontend/` computes one.

### Long work: 202 and poll

`POST /runs` and `POST /examinations` answer immediately with an id; the screen polls `GET`. A solve
takes minutes and no HTTP request is held open for it (ADR-005). ⚠️ **Runs execute on a single-worker
pool** — a second run sits in `PENDING` until the first finishes, and `RunPipeline` says so, because an
unexplained "Queued" for two minutes reads as a hung application.

⚠️ **Both `/generate` and `/examinations` fall back to the newest run on the server** when their
component state is empty. Without it, navigating away and back loses a run the server still has.

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

**How many are open is NOT recorded here — `docs/open-questions.md` is the authority and
`docs/dashboard.md` carries the current summary.** ⚠️ **This paragraph said "Two questions are open"
until 2026-08-11 and was stale**, exactly as the SHA in the dashboard's repository row was stale five
times, and for the same reason: a count cannot survive a resolution that does not touch the file
recording it. The codes are not listed here either, so that there is exactly one place to update. What
belongs here is the rule, not the list:

> If your work touches an open question, **resolve it in `docs/open-questions.md` first, with the
> reason, then implement.** If it is not yours to decide, say so and stop. An assumption made in code
> and never written down is how this project acquires a defect that surfaces three weeks later — and
> C-13 is the proof: a plausible conclusion nobody tried to falsify cost three sessions of work.

**The resolved ones are NOT summarised here**, for the same reason the open ones are not: every code
belongs to exactly one file, and a second copy is a second thing to update. `docs/open-questions.md`
carries them all with their full reasoning — ⚠️ **and the number is deliberately not written here
either**, for the reason above; it went from twenty to twenty-one when Phase 12 raised C-22; `docs/constraint-model.md` owns the modelling facts
(C-6's four withdrawable rules, C-7's `y[s][t]` encoding), `docs/scoring-and-explanation.md` owns the
scoring ones (C-5, C-14), and `docs/data-and-instance.md` owns C-13's two occupancy bounds.

**One footgun does belong here, because it is a rule about writing code rather than a question:**

⚠️ **The same seven formulas are implemented twice, on purpose:** `analysis/criteria.py` over realised
placements, `solver/objective.py` as CP-SAT expressions. The solver may not import the analysis layer
(`docs/architecture.md`), so nothing but a test keeps them in step —
`tests/integration/test_objective_matches_analysis.py`. **Change one, change the other**, and mind the
units: the two layers must agree on scale, not just on shape (S6's did not, and the solver silently
priced it 28× too high until it was caught).

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
| **Everything CI would run** | `scripts/run-checks.ps1` — ⚠️ **there is no CI; a person runs this** |
| **The acceptance suite** | `scripts/run-acceptance.ps1` — one test per requirement, against its criterion. `-FastOnly` skips the solver-marked half. ⚠️ The full sweep takes **16–22 min** and the spread is load, not variance — quote the range or none (`docs/status.md`) |
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

### Traps that will waste your time

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

## Environment, and how to start the thing

**Three processes.** PostgreSQL in Docker, the API on `:8000`, Vite on `:5173`.

```
docker compose up -d                                          # PostgreSQL 17
cd backend  && uv run uvicorn optiedt.api.main:app --reload   # :8000
cd frontend && npm run dev                                    # :5173, proxies /api
```

Seed the first accounts once, on an empty system: `uv run python -m optiedt.services.seed`
(refuses if any account exists — C-18).

### Variables — NAMES ONLY. ⚠️ Never write a value into a tracked file

`backend/.env` and the root `.env` are gitignored and must stay so. Everything below is read by
`core/config.py` with the `OPTIEDT_` prefix.

| Variable | Side | Required | Controls |
|---|---|---|---|
| `OPTIEDT_DATABASE_URL` | backend | production | PostgreSQL DSN. Defaults to a local dev DSN |
| `OPTIEDT_ENVIRONMENT` | backend | production | `production` arms `Settings.require_deployable()` |
| `OPTIEDT_SECRET_KEY` | backend | production | Signs bearer tokens. ⚠️ **The default is published in this repository**; start-up REFUSES it when the environment is `production` |
| `OPTIEDT_ACCESS_TOKEN_EXPIRE_MINUTES` | backend | optional | Token lifetime; default 480 |
| `OPTIEDT_PERSISTENCE` | backend | optional | `database` (default) or in-memory, for tests |
| `OPTIEDT_SOLVER_WORKERS` | backend | recommended | `0` = every core. **Cap it on a shared host** |
| `OPTIEDT_SOLVER_DETERMINISTIC_BUDGET` | backend | optional | Work for a WHOLE run, split between profiles — not seconds (ADR-011) |
| `OPTIEDT_SOLVER_WALL_CLOCK_CEILING_SECONDS` | backend | optional | Hang backstop, not the primary bound |
| `OPTIEDT_SOLVER_SEED` | backend | optional | Default seed; the API takes one per run |
| `OPTIEDT_INSTANCE_PATH` | backend | optional | Where the 13 reference CSVs live |
| `OPTIEDT_CONSTRAINT_CATALOGUE_PATH` | backend | optional | The rule catalogue. ⚠️ Never importable (invariant 7) |
| `OPTIEDT_ASSISTANT_ENABLED` | backend | optional | `false` by default. **Everything works with it off — only prose disappears** (invariant 5) |
| `OPTIEDT_ASSISTANT_BASE_URL` | backend | with the assistant | Provider endpoint |
| `OPTIEDT_ASSISTANT_API_KEY` | backend | with the assistant | ⚠️ **Secret. Never commit it, never expose it to the browser** |
| `OPTIEDT_ASSISTANT_MODEL` | backend | with the assistant | Model name |
| `OPTIEDT_ASSISTANT_TIMEOUT_SECONDS` | backend | optional | Default 10; past it the computed form is shown |
| `OPTIEDT_POSTGRES_PORT` | root `.env` | local only | Host port for the container when 5432 is taken |
| `OPTIEDT_SEED_PASSWORD` | backend | local only | Sets the seeded password instead of a random one printed once |

**The frontend takes NO environment variables.** `src/api/client.ts` calls `/api` as a relative path.
In production, serve the SPA and the API from one origin, or rewrite `/api/*` to the backend — a
rewrite is preferable to a base URL because it keeps requests same-origin and leaves the client with
nothing to configure.

### ⚠️ Deployment status: NOT DEPLOYED

Nothing has been deployed anywhere. `docs/deployment.md` is a *plan* that has never been executed, and
`docs/RELEASE_CHECKLIST.md` records what is still unticked. **Do not describe the product as deployed,
live or in production.** ⚠️ The backend **cannot** run on short-lived serverless functions — a solve
takes minutes in an in-process background thread on a single-worker pool. `docs/deployment.md` §1 gives
the three reasons.

---

## How to do the things you will actually be asked to do

**Add a hard constraint.** Next free `H` code — codes are permanent, never reused. Add the row to
`data/instance/constraint_catalogue.csv` with its XHSTT reference if one exists. Implement in
`optiedt/solver/`. Decide whether it gets its own assumption literal — **it should not if it overlaps
another constraint** (C-6: redundant literals make the conflict report name a rule the user cannot act
on).

**Add an examination rule.** Next free `X` code. The examination model lives in `optiedt/examination/`
and is **parallel to `solver/`, never an extension of it** — R-6, and SRS §6.8 states it: an
examination may occupy several rooms at once, so room assignment is a capacity SUM and not a single
`room[s]`. ⚠️ **X1-X4 and SX1 are NOT in `constraint_catalogue.csv`** (SRS §6.8 keeps them separate,
and invariant 7 makes the catalogue unimportable anyway). ⚠️ **Examinations are DERIVED from the
instance, never supplied** — C-23 and ADR-013; a form collecting them would be the
examination-data upload FR-1 was scoped not to become.

**Add a soft criterion.** Next free `S` code — **`S1`, `S8`, `S9` are retired and must never be
reused.** Implement the `Criterion` Protocol, which requires `raw_value` *and* `bounds` together so a
criterion cannot be half-defined. Add its default weight to the catalogue; profile weights are
renormalised to sum to 1 before any score is computed.

**Touch the department data.** ⚠️ **`data/instance/` is READ-ONLY at runtime and nothing may write to
it** — `scripts/verify-instance.ps1` holds those files to figures the documentation states as facts, and
an application that edited them would make that check meaningless. A supplied dataset is recorded in
`department_dataset` and becomes the *base*, with FR-9's calendar and FR-2's declarations still layered
above it (`docs/architecture.md`). Two rules that fail a review if broken: **`constraint_catalogue.csv`
is never importable** (invariant 7 — an upload able to replace the catalogue could delete a hard rule),
and **a replacement that would orphan a declaration or a closure is refused rather than allowed to
delete one** (ADR-012, C-22).

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
