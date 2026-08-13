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

## The interface

React 18 + Vite 5, plain CSS in six token-driven layers, no UI framework. IBM Plex Sans for the
interface and IBM Plex Mono for figures and codes, both **self-hosted** — no CDN, so it renders
identically on a machine with no internet.

A grouped left rail, a sticky page bar carrying each screen's single primary action, and a content
region that has a real layout rather than a stack of cards. The signature surface is the **decomposition
ledger** on Compare: because the score is a weighted sum of normalised values, the difference between
two candidates decomposes *exactly*, and the ledger draws each term either side of a zero axis with the
sum landing on the difference.

⚠️ **This interface is a frozen baseline, accepted 2026-08-13.** Read
[`docs/UX_DECISIONS.md`](docs/UX_DECISIONS.md) before changing a visual decision — several entries
record a specific defect that a plausible "improvement" would bring back.

## Documentation

**`CLAUDE.md` is the entry point for anyone — human or model — about to change code.** It carries the
read-order, the seven invariants, the frontend baseline, what is decided and what is still open.

| Read this | For |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | The contract: invariants, architecture, commands, what must not change |
| [`docs/dashboard.md`](docs/dashboard.md) | **Where the project is.** The one page that answers it |
| [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) | The release-verification record — what was measured, when |
| [`docs/architecture.md`](docs/architecture.md) · [`docs/domain-model.md`](docs/domain-model.md) | How it is built |
| [`docs/constraint-model.md`](docs/constraint-model.md) · [`docs/scoring-and-explanation.md`](docs/scoring-and-explanation.md) | The solver and the score |
| [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) · [`docs/UX_DECISIONS.md`](docs/UX_DECISIONS.md) | The interface, and why |
| [`docs/API_OVERVIEW.md`](docs/API_OVERVIEW.md) | 33 endpoints, read from the live schema |
| [`docs/AI_BEHAVIOR.md`](docs/AI_BEHAVIOR.md) | Grounding, fallback, and what the AI must never claim |
| [`docs/TESTING.md`](docs/TESTING.md) | Commands and the coverage map |
| [`docs/deployment.md`](docs/deployment.md) · [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) | Deploying it, and what is still unticked |
| [`docs/supervisor/INTERFACE_WALKTHROUGH.md`](docs/supervisor/INTERFACE_WALKTHROUGH.md) | A non-technical guide to the screens |
| [`docs/decisions/`](docs/decisions/) | Thirteen ADRs — read one before arguing with it |

The three PDFs in `docs/specifications/` are the contractual specification. They are authoritative on
*what was promised*, and the working documents in `docs/` are authoritative on *how it is built* —
including several places where the PDFs contradict each other or leave something undefined. Those are
catalogued in `docs/open-questions.md` rather than resolved silently.

## Status

**Not deployed.** The application runs locally and is verified there; nothing has been deployed
anywhere. See [`docs/deployment.md`](docs/deployment.md) for the shape a deployment would take, and
[`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) for what is still unticked.

At the release freeze on **2026-08-13**: frontend **196/196** tests, typecheck and production build
clean; backend **633** fast tests and **74** database tests against real PostgreSQL 17; **245**
acceptance tests collected over 23 requirements; **0** contrast failures across 545 text nodes; **0**
secrets tracked.

> ⚠️ **This section deliberately carries no phase, progress or requirement count.**
> [`docs/dashboard.md`](docs/dashboard.md) is the only place project state lives. This section said
> something stale in **four** successive phases — twice found by an audit that then went stale itself,
> because a closing audit cannot verify the sentence recording its own phase closing. The fix was to
> stop keeping a second copy here.

📍 **A fresh session should read [`CLAUDE.md`](CLAUDE.md), then
[`docs/dashboard.md`](docs/dashboard.md), then [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).**

📍 **[`docs/project-roadmap.md`](docs/project-roadmap.md) is the phase view** — the whole project as one
continuous sequence.

⚠️ **Deployable only once configured, and it can no longer fail silently.** `OPTIEDT_SECRET_KEY`
defaults to a value published in this repository, so tokens signed with it could be forged. Setting
`OPTIEDT_ENVIRONMENT=production` makes start-up **refuse** that default, so the failure is loud instead
of invisible. The seed command is a development and demonstration tool, not a provisioning mechanism.


## Author

Mohamed Jawad Touir — company internship project, academic year 2025–2026.
