# OptiEDT

AI-assisted generation, ranking and explanation of university timetables for Tunisian public
universities under the LMD system.

A department currently builds its semester timetable by hand in a spreadsheet — two to three weeks of
work, dependent on one person, with conflicts discovered after publication. OptiEDT builds it
automatically, produces **several** valid timetables instead of one, and states in arithmetic anyone
can recheck why one is ranked above another.

---

## What it does

- Collects teacher availability through a web form instead of email.
- Verifies the data **before** solving and reports structural risks — so an instance that genuinely
  has no solution is never confused with a bug in the model.
- Generates several candidate timetables under distinct weight profiles, none of which can contain a
  conflict.
- Scores each candidate out of 100, orders them, and decomposes the difference between any two
  criterion by criterion. The decomposition is exact: it *is* the score calculation, read term by term.
- Names the rules in conflict when no timetable exists, rather than searching indefinitely.
- Explains all of this in ordinary language through a language model that is architecturally prevented
  from influencing any of it.

## What it deliberately does not do

Drag-and-drop editing of a published timetable, re-solving after publication, constraint entry in
ordinary language, timetable *generation* by a learned model, an Arabic interface, room-usage
statistics, multiple faculties at once, or a mobile app. Each exclusion has a reason recorded in the
Cahier des Charges §3.2 or in an ADR.

---

## How it is built

Four layers, one deployable unit:

| Layer | Technology | Responsibility |
|---|---|---|
| Presentation | React + TypeScript + Vite | Grids, comparison screen, timetable views |
| Application | FastAPI + PostgreSQL | REST API, data, runs, publication |
| Decision | OR-Tools CP-SAT | Assigns a slot and a room to each session. **Nothing else may** |
| Analysis | Python, no solver access | Sub-scores, ranking, exact decomposition, dominance |

The separation between the last two is a requirement, not a description. It is enforced by
`import-linter` in `scripts/run-checks.ps1`, so a violation fails the check rather than a review.
⚠️ **That check is run by a person — there is no CI in this repository.** The contracts are real and
fire; nothing runs them automatically.

The reference instance is 218 sessions across 51 groups, 44 teachers and 20 rooms, on a grid of 30
slots of which 28 are open.

---

## Getting started

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+, Docker.

```bash
scripts/bootstrap.ps1
```

That creates the virtualenv, installs both dependency sets, copies `.env.example` to `.env` and starts
PostgreSQL. Then:

```bash
docker compose up -d
```

⚠️ **If this machine already runs PostgreSQL on 5432, that command appears to work and does not.** The
container starts, reports `healthy`, and `docker ps` shows `0.0.0.0:5432->5432/tcp` — while every
connection from the host reaches the *other* server. Found on 2026-08-04 against a native PostgreSQL 18
service, which rejected the `optiedt` credentials; a local server that happened to accept them would
have had this project's migrations applied to it instead. Move the host side and point the URL at it:

```bash
echo OPTIEDT_POSTGRES_PORT=5433 >> .env
```

Then set `OPTIEDT_DATABASE_URL=postgresql+psycopg://optiedt:optiedt@localhost:5433/optiedt` in
`backend/.env`. Confirm which server you actually reached — the container is PostgreSQL **17**:

```bash
docker exec optiedt-postgres psql -U optiedt -d optiedt -tAc "select version();"
```

```bash
cd backend && uv run alembic upgrade head && uv run uvicorn optiedt.api.main:app --reload
```

```bash
cd frontend && npm run dev
```

The application requires a sign-in since Phase 5 (FR-11), and there is no registration screen —
accounts come from a seed command, which **refuses to run if any account already exists**:

```bash
cd backend && uv run python -m optiedt.services.seed
```

It creates `responsable`, `administrateur`, `etudiant` and one account per teacher (`t001` … lowercased
teacher ids), all sharing one password: `OPTIEDT_SEED_PASSWORD` if set, otherwise generated and printed
once. ⚠️ Development and demonstration only — and set `OPTIEDT_SECRET_KEY`, because its default is
published in this repository and tokens signed with it can be forged by anyone.

The API serves its own interactive documentation at `http://localhost:8000/docs`. That generated
OpenAPI page **is** the API reference — there is no hand-written copy to fall out of date with it.

---

## Repository layout

```
docs/            Working documentation. Start at CLAUDE.md, then docs/dashboard.md
  dashboard.md     State, roadmap, open questions, next task — the handoff page
  history.md       Session archive. Forensics only, not orientation
  specifications/  The three PDFs — the contract. Not the working reference
  decisions/       ADRs. Read before reopening a settled question
backend/         FastAPI app, CP-SAT model, analysis layer
  src/optiedt/validation/   The ITC-2007 benchmark harness. Runs against the
                            product, never inside it — no shipped code imports it
frontend/        React interface
data/            Instance generator, the 13 instance files, verification checks
  reference/       Published benchmark archives. Gitignored; see PROVENANCE.md
scripts/         Bootstrap and maintenance
```

## Documentation

**`CLAUDE.md` is the entry point for anyone — human or model — about to change code.** It carries the
read-order, the seven invariants, what is decided and what is still open.

The three PDFs in `docs/specifications/` are the contractual specification. They are authoritative on
*what was promised*, and the working documents in `docs/` are authoritative on *how it is built* —
including several places where the PDFs contradict each other or leave something undefined. Those are
catalogued in `docs/open-questions.md` rather than resolved silently.

## Status

**Increment 1 of 2 · COMPLETE. Phases 1–7 delivered.**

The decision layer is built: all twelve hard constraints, a conflict-free timetable on the reference
instance in about three seconds, every constraint re-verified from the raw data rather than trusted
from the solver's own status. The analysis layer sits on top: seven quality criteria, an exact
weighted score, ranking, the term-by-term decomposition, Pareto dominance, and a portfolio returning
three distinct candidates reproducibly. The engine is validated on the 21 published ITC-2007 instances.
The web interface reaches all of it — availability grid, generation, four timetable views, comparison,
the conflict report and published timetables with their trace.

Phase 5 added the five pre-solve checks inside the application, a diagnosis run that names the rules
in conflict, the run record in PostgreSQL, authentication with rights, and publication. Phase 6 added
the acceptance suite — one test per requirement against its criterion — the instance generator and the
demonstration script. **Phase 7 closed increment 1**: an accepted recommendation now changes one
solver input and launches a **new run** through the same engine, and the language service explains,
answers and reports from figures the analysis layer computed, with every number it writes checked
against the context it was given.

**Eight of the nine acceptance criteria are met**; the ninth is a timed walkthrough with a teacher,
which no automated check can replace ([`docs/demonstration.md`](docs/demonstration.md) §2).

⚠️ **The language service is off by default, and everything works with it off** — only text
disappears. **No test calls a live provider and none can**: a model's output is not fixed by a seed,
so what the suite verifies is the application's behaviour *around* a provider, never that any
particular one works. A first live call is a deployment step — **performed once, on 2026-08-07, and
recorded in [`docs/demonstration.md`](docs/demonstration.md) §4**, which is what moved FR-24 to `✓`.
That record is a dated observation, not automation: a green build is still no evidence about a model.

⚠️ **`scripts/run-checks.ps1` is run by a person, not by a pipeline.** There is no CI configuration in
this repository. The eleven `import-linter` contracts are real and do fire — but nothing runs them
automatically, so a violation is caught when someone runs the script, not when they push.

⚠️ *This Status section was two phases stale when Phase 6's audit found it, was corrected, and then
went stale again the moment Phase 6 closed — because the audit ran before the phase's own final state
was written. Phase 7's audit found it a second time. **A closing audit cannot verify the sentence that
records its own phase closing**; that line has to be written after.*

⚠️ **Not deployable as it stands.** `OPTIEDT_SECRET_KEY` defaults to a value published in this
repository, so tokens signed with it can be forged; account management through the interface is not
built; and the seed command gives every account the same password. Safe to demonstrate, not to expose.

**[`docs/dashboard.md`](docs/dashboard.md) is the one page that answers "where is this project".**
`docs/status.md` holds the detail, `docs/open-questions.md` what is still undecided.

## Author

Mohamed Jawad Touir — company internship project, academic year 2025–2026.
