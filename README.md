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

**Increment 1 · COMPLETE. Phases 1–11 delivered. Phase 12 of 14 is next and has not started.**

📍 **A fresh session should read [`docs/dashboard.md`](docs/dashboard.md), then
[`docs/project-roadmap.md`](docs/project-roadmap.md) §5's Phase 12 subsection — that is the handoff.**

📍 **[`docs/project-roadmap.md`](docs/project-roadmap.md) is the phase view** — the whole project as one
continuous sequence, with what the specification calls increment 1 and increment 2 mapped into it.

The decision layer is built: all twelve hard constraints, a conflict-free timetable on the reference
instance in about three seconds, every constraint re-verified from the raw data rather than trusted
from the solver's own status. The analysis layer sits on top: seven quality criteria, an exact
weighted score, ranking, the term-by-term decomposition, Pareto dominance, and a portfolio returning
three distinct candidates reproducibly. The engine is validated on the 21 published ITC-2007 instances.
The web interface reaches all of it — availability grid, generation, four timetable views, comparison,
the conflict report and published timetables with their trace. **Phase 9 added the way out of the
screen** (FR-10): every timetable view prints as an identified sheet and downloads as a spreadsheet,
both carrying the run, seed and full weight vector that produced them. **Phase 10 closed five
requirements by evidence rather than by code** (FR-3, FR-4, FR-7, FR-14, FR-16), taking the count from
10 `✓` to 15 of 25. **Phase 11 added the administrative surfaces** (FR-9, FR-11 → 18 of 25, and 21 once C-9 closed): an
administrator configures the calendar — closed half-days, holidays and the shortened-day window — and
manages the accounts, and a student reaches the published timetable of their own group and nothing
else.

Phase 5 added the five pre-solve checks inside the application, a diagnosis run that names the rules
in conflict, the run record in PostgreSQL, authentication with rights, and publication. Phase 6 added
the acceptance suite — one test per requirement against its criterion — the instance generator and the
demonstration script. **Phase 7 closed increment 1**: an accepted recommendation now changes one
solver input and launches a **new run** through the same engine, and the language service explains,
answers and reports from figures the analysis layer computed, with every number it writes checked
against the context it was given.

**All nine acceptance criteria are met**, the ninth on 2026-08-07. ⚠️ **That one was reworded rather
than met as written** — it asked for the grid to be filled *"in under 5 minutes without training"* and
the run measured no time, so the wording dropped the clause the evidence could not support. The full
record, including what the run did **not** establish, is in
[`docs/demonstration.md`](docs/demonstration.md) §2.

⚠️ **The language service is off by default, and everything works with it off** — only text
disappears. **No test calls a live provider and none can**: a model's output is not fixed by a seed,
so what the suite verifies is the application's behaviour *around* a provider, never that any
particular one works. A first live call is a deployment step — **performed once, on 2026-08-07, and
recorded in [`docs/demonstration.md`](docs/demonstration.md) §4**, which is what moved FR-24 to `✓`.
That record is a dated observation, not automation: a green build is still no evidence about a model.

⚠️ **`scripts/run-checks.ps1` is run by a person, not by a pipeline.** There is no CI configuration in
this repository. The eleven `import-linter` contracts are real and do fire — but nothing runs them
automatically, so a violation is caught when someone runs the script, not when they push.

⚠️ **21 of 25 requirements are `✓`, and the last open question is closed.** The single remaining `WIP`
is **FR-8**, and it is a decision rather than an omission: promoting it would need its criterion
narrowed to match what the software cannot do, which this project refuses. The other three are not
started — FR-1 (Phase 12) and FR-20/FR-21 (conditional).

⚠️ **C-9 closed on 2026-08-11 as a project decision from repository evidence, because the supervisor
never answered** — the project owner granted that authority. FR-6's criterion turned out to be
supervisor-written all along (SRS §6.7). **FR-10's and FR-18's are project-authored, labelled as such
wherever cited, and therefore reversible**; a Table 35 row is still absent for both and none was
invented. ⚠️ **FR-18's figure was not missing but mislaid**: C-4 had defined it in 2026-07-30 as
occupied periods over open slots, and the screen had been showing exactly that.

⚠️ **One limitation of Phase 11 is recorded rather than absorbed.** ADR-003 gives the shortened-day
window one effect — *displayed and printed hours*. The window is configurable, persisted and previewed
on the administration screen; **the timetable views and the CSV export still print the ordinary hours.**
FR-9's acceptance criterion is exclusively about closing a half-day, so its `✓` stands on evidence — but
a department that sets a Ramadan window and prints a timetable will see 08:30.

⚠️ **Phase 10 found that four of its own five requirements had no acceptance criterion either**, and
closed them honestly rather than inventing one: SRS Table 35 has no row for FR-4, FR-7, FR-14 or FR-16,
but all four have a **detailed SRS §3.2 input/processing/output row**. That row is what each acceptance
file quotes, and all four are now transcribed into
[`docs/testing-strategy.md`](docs/testing-strategy.md) §4.

⚠️ **A pre-Phase-11 audit then narrowed C-9 from four requirements to two**, by checking something
nobody had: **SRS Table 36 names a specifying section for three of them**, and two of those sections
state testable behaviour — **FR-6 → §6.7** and **FR-17 → §6.7 and §8.4**. FR-17 is now `✓`; FR-6 needs
only an acceptance file. **FR-10 and FR-18 remain**, and FR-18's gap is the sharper one: no document
anywhere defines what its occupancy figure *is*. Both decisions were taken from repository evidence
because the supervisor was unavailable, and are labelled as such in
[`docs/open-questions.md`](docs/open-questions.md).

⚠️ *This Status section was two phases stale when Phase 6's audit found it, was corrected, and then
went stale again the moment Phase 6 closed — because the audit ran before the phase's own final state
was written. Phase 7's audit found it a second time. **A closing audit cannot verify the sentence that
records its own phase closing**; that line has to be written after.*

⚠️ **Still not deployable as it stands** — but it can no longer fail silently. `OPTIEDT_SECRET_KEY`
defaults to a value published in this repository, so tokens signed with it could be forged. **Since
2026-08-07, setting `OPTIEDT_ENVIRONMENT=production` makes start-up REFUSE that default**, so the
failure is loud instead of invisible. What remains genuinely unbuilt is account management through the
interface, and the seed command still gives every account the same password. Safe to demonstrate, not
to expose.

**[`docs/dashboard.md`](docs/dashboard.md) is the one page that answers "where is this project".**
`docs/status.md` holds the detail, `docs/open-questions.md` what is still undecided.

## Author

Mohamed Jawad Touir — company internship project, academic year 2025–2026.
