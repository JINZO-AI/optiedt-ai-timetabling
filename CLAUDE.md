# CLAUDE.md — how to work on OptiEDT

**OptiEDT** generates, ranks and explains weekly university timetables for a Tunisian public faculty
under the LMD system. CP-SAT places the sessions; an exact weighted sum ranks the results; a language
model explains them and is forbidden from doing anything else.

This file exists so that **you never need to reread the PDFs.** They are the contract with the
supervisor, not the working reference. Everything you need to write correct code is in `docs/`.

---

## Read this first, in this order

| Order | File | Why |
|---|---|---|
| 1 | `docs/status.md` | Where the project actually is. What is done, next, blocked |
| 2 | This file, section "The seven invariants" | What you may never break |
| 3 | `docs/open-questions.md` | What is **not** decided. Do not silently pick an answer |
| 4 | The `docs/` file for your area | See the map below |

Everything else is on demand:

| If you are working on | Read |
|---|---|
| Anything structural | `docs/architecture.md` |
| Entities, database, migrations | `docs/domain-model.md` |
| The CP-SAT model, constraints, diagnosis | `docs/constraint-model.md` |
| Scores, ranking, contributions, dominance | `docs/scoring-and-explanation.md` |
| Recommendations, regeneration, the assistant | `docs/ai-integration.md` |
| The generator or the 13 instance files | `docs/data-and-instance.md` |
| Tests | `docs/testing-strategy.md` |
| "Is FR-N built?" | `docs/requirements-traceability.md` |
| "Why was X chosen?" | `docs/decisions/` (ADRs) |

**Never** open `docs/specifications/*.pdf` to answer a question. If the answer is not in `docs/`, that
is a gap in `docs/` — fix the gap, then continue.

---

## The seven invariants

These are not style preferences. Each one is a stated requirement in the specification, and breaking
any of them is a correctness bug, not a code-review comment.

1. **The analysis layer may not import the solver.** `optiedt.analysis` must never reach
   `optiedt.solver`. This is what makes an analysis bug produce a wrong *order* instead of an invalid
   *timetable*. Enforced by `backend/.importlinter` in CI — if you find yourself wanting this import,
   the design is wrong, not the lint rule.

2. **Nothing outside the solver ever writes a placement.** Not the analysis layer, not the
   recommendation module, not the assistant, not a user. A session gets a slot and a room from CP-SAT
   or not at all.

3. **A recommendation is one of exactly three actions.** `weight_delta`, `lock_session`,
   `exclude_slot`. A fourth action is a type error, not a feature. Accepting one launches a **new run
   through the same solver** with one input changed — never an edit to an existing timetable.

4. **The assistant never receives a database connection, and never produces a figure.** It gets a
   built context payload and returns text. Every number in its answer must already appear in that
   context, or the answer is discarded and the computed form is shown instead.

5. **Everything works with the assistant switched off.** Generation, scoring, ranking, comparison,
   regeneration and publication are all available in degraded mode. Only text disappears.

6. **A candidate is immutable once recorded.** Its sub-scores describe its content; editing it would
   make them describe something that no longer exists. A regenerated timetable is a *new* candidate
   under a *new* run.

7. **Institutional calendar rules are configuration, never constraints.** A closed half-day sets
   `slot.is_open = 0` and H9 removes it from every domain. A shortened-day window shifts *displayed*
   hours only — the slot index never changes, so the model is untouched. Adding a CP-SAT constraint
   for Ramadan or a closed Saturday is a bug. See ADR-003.

---

## Two mechanisms make invariants 1 and 3 fail the build

Both are already configured. Do not weaken them to make a change compile.

- **`backend/.importlinter`** — forbids `analysis → solver`, `analysis → db`, `assistant → db`.
  Runs in CI. Invariant 1.
- **The recommendation union type** in `optiedt.recommendations` — the catalogue is
  `WeightDelta | LockSession | ExcludeSlot`. Adding a fourth variant breaks type checking everywhere
  the union is exhaustively matched. Invariant 3.

---

## Decided — do not reopen

Read the ADR before arguing with any of these. Each records reasoning that already survived a review.

| ADR | Decision |
|---|---|
| 001 | CP-SAT, not metaheuristics / ILP / learning |
| 002 | Weighted sum for ranking; dominance as a complement |
| 003 | Calendar rules as configuration, not constraints |
| 004 | One deployable unit, not microservices |
| 005 | In-process background task, not a message broker |
| 006 | The LLM does not place, score, or rank |
| 007 | Closed 3-action recommendation catalogue |
| 008 | Generated instance; public sources given roles, never merged |
| 009 | Normalisation bounds are **instance**-derived, stable across runs |
| 010 | The assistant is committed to **increment 1** |
| 011 | Solve under `max_deterministic_time`, not wall clock |

---

## Open — do not silently decide

Full detail, with options and consequences, in `docs/open-questions.md`. The short version:

| # | Open | Blocks |
|---|---|---|
| C-4 | The raw value `v_i` and the bounds of **all seven** soft criteria are undefined | Scoring, and everything downstream |
| C-7 | The `y[s][t]` channelling constraint for 2-period sessions is unwritten | The model |
| C-12 | **S5 carries weight 0.20 and has no input data** — the schema has no "preferred" state | Scoring, the availability grid |
| C-6 | Which of H2 / H11 get their own assumption literal | The diagnosis report |
| C-5 | "At least three candidates" can fail when duplicates are removed | Acceptance tests |
| C-9 | FR-6, FR-10, FR-17, FR-18 have no detailed specification | Acceptance |

⚠️ **C-12 and C-5 are the same bug waiting to happen.** The teacher-favouring profile is supposed to
differ by raising S3 *and* S5. If S5 measures identically zero, that profile differs by S3 alone, two
candidates may converge, duplicate removal drops one, and the "at least three candidates" acceptance
test fails — for a reason nobody would look for, because the symptom is "the portfolio is boring" and
the cause is a missing column.

**C-11 is resolved:** the reference instance exists in `data/instance/` and every documented figure
verifies. Run `scripts/verify-instance.ps1`.

If your work touches one of these, **resolve it explicitly in `docs/open-questions.md` first**, then
implement. An assumption made in code and not written down is how this project acquires a defect that
surfaces three weeks later.

---

## Commands

```bash
scripts/bootstrap.ps1
```

Then, from `backend/`:

⚠️ **`uv` is not installed on this machine.** Get it from
<https://docs.astral.sh/uv/getting-started/installation/>; node, docker and git are already present.

| Task | Command |
|---|---|
| Install / sync deps | `uv sync` |
| Run the API | `uv run uvicorn optiedt.api.main:app --reload` |
| Tests | `uv run pytest` |
| Property tests only | `uv run pytest tests/property` |
| Lint + format | `uv run ruff check . && uv run ruff format .` |
| **Layer boundaries** | `uv run lint-imports` |
| New migration | `uv run alembic revision --autogenerate -m "..."` |
| Apply migrations | `uv run alembic upgrade head` |

From `frontend/`: `npm install`, `npm run dev`, `npm run build`, `npm run typecheck`.

From the root:

| Task | Command |
|---|---|
| PostgreSQL | `docker compose up -d` |
| **Everything CI runs** | `scripts/run-checks.ps1` |
| **Verify the instance** | `scripts/verify-instance.ps1` |
| Reference archives status | `scripts/check-reference-data.ps1` |

Run `verify-instance.ps1` after any change to `data/instance/` or the generator. It checks the
instance against the figures the PDFs state as facts; a failure means either the instance changed or
the documentation is now false.

---

## How to do the things you will actually be asked to do

**Add a hard constraint.** Give it the next free `H` code — codes are permanent identifiers and are
never reused. Add the row to `data/instance/constraint_catalogue.csv` with its XHSTT reference if one
exists. Implement it in `optiedt/solver/constraints/`. Decide whether it gets its own assumption
literal for the diagnosis run — **it should not if it overlaps another constraint** (see C-6, and
`docs/constraint-model.md` on why redundant literals corrupt the conflict report).

**Add a soft criterion.** Give it the next free `S` code. **`S1`, `S8` and `S9` are retired and must
never be reused.** Implement the `Criterion` Protocol — which requires `raw_value` *and* `bounds`
together, deliberately, so a criterion cannot be half-defined. Add its default weight to the catalogue,
and remember that profile weights are renormalised to sum to 1 before any score is computed.

**Change a time limit.** It is a *deterministic* budget, not seconds (ADR-011). The wall-clock ceiling
is a safety net for hangs, not the primary bound. The deterministic-to-wall-clock ratio is
machine-dependent — check `docs/status.md` for the calibration measured on this machine.

**Touch the assistant.** Any change must preserve invariants 4 and 5. Verify degraded mode still works
by switching the service off in config and confirming every other function is unaffected.

---

## Conventions

- **French domain terms keep their French names in code** — `Promotion`, `CM`/`TD`/`TP`. They are
  precise LMD terms with no clean English equivalent, and translating them invites drift. The canonical
  list is in `docs/domain-model.md`.
- Python: `ruff` defaults, full type annotations, `from __future__ import annotations`.
- Domain layer is pure — no I/O, no ORM, no framework imports.
- Commits: imperative mood, reference the FR or ADR when one applies.
- **Update `docs/status.md` when you finish a phase**, and
  `docs/requirements-traceability.md` when you finish an FR. A stale status file is worse than none —
  the next session trusts it.
