# Testing — how to run it, and what it covers

Practical companion to [`testing-strategy.md`](testing-strategy.md), which carries the *reasoning*
(what each layer is for, why acceptance tests are driven through HTTP, the mutation-testing
discipline). This file is the commands and the coverage map.

**Collected on 2026-08-13: 782 backend tests, 196 frontend tests, 245 acceptance tests** (a subset of
the 782, selected by marker).

---

## Commands

### Frontend — from `frontend/`

```bash
npm run test        # vitest, 196 tests, ~10-40 s
npm run typecheck   # tsc --noEmit
npm run build       # tsc -b && vite build
npm run dev         # :5173, proxies /api to :8000
npm run preview     # serve the production build
```

### Backend — from `backend/`

```bash
uv run pytest                                   # everything, 782 collected
uv run pytest -m "not solver"                   # skip the slow half
uv run pytest -m database                       # needs `docker compose up -d`
uv run pytest tests/acceptance                  # 245, one file per requirement
uv run pytest tests/property                    # property tests only
uv run pytest tests/unit/test_scoring.py        # one file
uv run pytest -k decomposition                  # by name
uv run ruff check . && uv run ruff format --check .
uv run mypy                                     # strict, 92 files
uv run lint-imports                             # 13 layer contracts
```

### Everything, from the repository root

```bash
docker compose up -d          # ⚠️ FIRST, or the database step silently skips
scripts/run-checks.ps1        # what CI would run — there is no CI, a person runs this
scripts/run-acceptance.ps1    # one test per requirement. -FastOnly skips solver-marked
scripts/verify-instance.ps1   # the instance against figures the documentation states
scripts/validate-itc2007.ps1  # 21 published instances, tens of minutes
```

⚠️ **`run-acceptance.ps1` takes 16–26 minutes** and the spread is machine load, not variance. Quote the
range or none.

⚠️ **`docker compose up -d` succeeds even when another PostgreSQL already owns 5432.** Confirm which
server you reached:
`docker exec optiedt-postgres psql -U optiedt -d optiedt -tAc "select version();"` — the container is
PostgreSQL 17.

---

## What the backend suite covers

| Layer | Directory | What it establishes |
|---|---|---|
| Unit | `tests/unit/` | Criteria arithmetic, scoring, ranking, the recommendation catalogue, the assistant's verifier and computed forms, the config guard, the examination model's *infeasibility* under each rule |
| Property | `tests/property/` | The four scoring properties, including that the decomposition is exact |
| Integration | `tests/integration/` | The API's shapes and statuses; **`test_objective_matches_analysis.py`** — the one thing keeping `analysis/criteria.py` and `solver/objective.py` in step |
| Database | `-m database` | 74 tests against real PostgreSQL 17, including 2 migration tests |
| Acceptance | `tests/acceptance/` | 245 tests over 23 requirements plus the student surface, each quoting its criterion at the head of the file and driven through HTTP |
| Validation | `optiedt/validation/` | ITC-2007. The fast half — reproducing the published cost of seven shipped solutions — runs in `run-checks.ps1` |

⚠️ **`validation/` runs *against* the product, not inside it.** ITC-2007 is a different problem and
shares no code with `solver/`; the eighth import contract fails the build if anything shipped imports
it. Do not describe its results as validating `optiedt.solver` — they validate the modelling approach
on instances the project did not design.

### Acceptance files

`test_fr01` `02` `03` `04` `05` `06` `07` `08` `09` `11` `12` `13` `14` `15` `16` `17` `18` `19` `20`
`22` `23` `24` `25`, plus `test_student_view`.

⚠️ Note the gaps: **FR-10 is verified in the frontend** (`printAndExport.acceptance.test.tsx`) because
its entire surface is the rendered DOM — Phase 9 delivered print and export without touching a backend
file. **FR-21 has no file because it is not started.**

---

## What the frontend suite covers

21 files, 196 tests, vitest + Testing Library in jsdom.

The rule the suite follows: **assert on what a reader sees**, not on implementation. The backend proves
the arithmetic; only the frontend can prove the arithmetic reached the screen intact.

| Area | Files | The property that matters |
|---|---|---|
| Sign-in | `LoginScreen.test.tsx` | The role buttons prefill a username and **grant nothing** — the chosen role reaches no request |
| Assistant | `AssistantPanel`, `Answer` | Computed and generated never look alike; `fallbackReason` is surfaced; the off-banner names the variable |
| Comparison | `ContributionsTable` | ⚠️ **The displayed contributions sum to the displayed difference at every precision** — rounding happens here, so only here can it be checked |
| Dominance / conflicts / regeneration | 3 files | The closed 3-action catalogue; a verdict that never reads as "no problem found" by accident |
| Timetable | `TimetableGrid`, `model`, `export`, `OccupancyView`, `PrintHeader` | Cells, continuations, closed slots; the occupancy denominator |
| **FR-10** | `printAndExport.acceptance.test.tsx` | **What leaves the screen is the displayed view** — the grid and the export compared as sets |
| Admin / dataset | `AccountsPanel`, `CalendarEditor`, `DatasetPanel` | Every rejected line keeps its file, line, column and value |
| Student | `StudentTimetable.test.tsx` | A printed sheet names its group; each role lands correctly |
| Errors | `errors.test.ts` | A user-facing message never leaks a status code or a class name |

⚠️ **These class names are coupled to tests and must not be renamed casually:**
`.assistant__origin`, `.assistant__origin--generated`, `.cell--busy`, `.cell__course`,
`.cell--continued`, `.cell--closed`, `.print-only`, `.print-header__trace`.

---

## Two things a green suite does **not** mean

1. ⚠️ **It does not mean the assistant was tested against a language model.** No test calls a live
   provider and none can — a model's output is not fixed by a seed (C-21). What is verified is the
   application's behaviour *around* a provider. See [`AI_BEHAVIOR.md`](AI_BEHAVIOR.md) §7.
2. ⚠️ **It does not mean the interface looks right.** jsdom has no layout engine. Geometry, contrast
   and overflow are verified by measuring the running application in a browser — which is how the time
   axis defect was found *after* 196 tests were green.

---

## Rules for adding a test

- **Any test that invokes the solver must fix the seed *and* use a deterministic budget.** A test
  bounded by wall clock passes on one machine and fails on another, and the failure looks like a solver
  bug.
- **Verify a new assertion fires before relying on it.** Break the thing it guards and watch it fail.
  Phase 11 found two tests passing for the wrong reason; Phase 12 found two more. Both times the *test*
  was defective, not the code.
- **Never narrow a criterion to match what the software does.** That is the one direction this project
  refuses — it is why FR-8 is still `WIP`.
