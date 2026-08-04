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

The separation between the last two is a requirement, not a description. It is enforced in CI by
`import-linter`, so a violation fails the build rather than a review.

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

**Increment 1 of 2 · Phases 1–3 complete.** The decision layer is built: all twelve hard constraints
are implemented and the reference instance produces a conflict-free timetable in about three seconds,
with every constraint re-verified from the raw data rather than trusted from the solver's own status.
The analysis layer is built on top of it: seven quality criteria, an exact weighted score, ranking,
the term-by-term decomposition, dominance, and a portfolio that returns three distinct candidates
reproducibly. The engine is also validated on the 21 published ITC-2007 instances.

**Phase 4 — the web interface — is next**, and is what turns all of the above into something a user
can reach. Nothing is blocked.

**[`docs/dashboard.md`](docs/dashboard.md) is the one page that answers "where is this project".**
`docs/status.md` holds the detail, `docs/open-questions.md` what is still undecided.

## Author

Mohamed Jawad Touir — company internship project, academic year 2025–2026.
