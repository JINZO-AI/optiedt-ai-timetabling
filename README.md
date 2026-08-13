# OptiEDT

**Automatic generation, ranking and explanation of university timetables** — for a Tunisian public
faculty under the LMD system.

Live: **https://optiedt-ai-timetabling.vercel.app**

---

## The problem, in one paragraph

A department builds its weekly timetable by hand in a spreadsheet. It takes two to three weeks, it
depends on one person who knows how, and clashes are usually discovered *after* publication — a
teacher booked in two rooms at once, a group with two lectures in the same hour. There are 218
sessions to place across 44 teachers, 51 student groups, 20 rooms and 30 weekly slots. The number of
possible arrangements is far beyond what anyone can search by hand.

OptiEDT does it automatically, produces **several** valid timetables instead of one, and states in
arithmetic anyone can recheck why one is ranked above another.

---

## The one idea the whole project is built on

There are two very different decisions hiding inside "make me a timetable", and the project keeps
them strictly apart:

| | The decision | What it costs if wrong | Method |
|---|---|---|---|
| **1** | Which session goes in which slot and room | A timetable you cannot publish | **Constraint solving** — correct by construction |
| **2** | Which valid timetable is *better* | A worse ranking — still usable | **Weighted sum** — exact, checkable by hand |

Methods that **guarantee** handle decision 1. Methods that **estimate** handle decision 2.

That single separation is the answer to most "why did you do it that way?" questions. A wrong answer
on decision 1 is a broken product; a wrong answer on decision 2 is a matter of taste. So they get
different tools, and neither is allowed to touch the other.

**The language model touches neither** — which is exactly why it was allowed into the project at all.

---

## How I approached it

**1. I wrote the contract before writing code.** Three documents, delivered to my supervisor on
29 July 2026 and kept in [`docs/specifications/`](docs/specifications/):

- *Cahier des Charges* — what the product must do and, importantly, what it must **not**
- *Software Requirements Specification (SRS)* — the requirements, numbered FR-1 … FR-25
- *Project Plan and Methodology* — how the work would be sequenced

**2. I decided what to exclude, and wrote down why.** Drag-and-drop editing, re-solving after
publication, constraints typed in ordinary language, timetable *generation* by a learned model, an
Arabic interface, several faculties at once, a mobile app. Every exclusion has a recorded reason. A
scope you can defend is worth more than a scope that sounds impressive.

**3. I picked the algorithm to fit the guarantee I needed, not the other way round.** I needed "no
clashes, ever" — not "usually no clashes". That rules out genetic algorithms and anything learned,
and points at constraint programming. I used Google OR-Tools' CP-SAT solver.

**4. I made the ranking hand-checkable on purpose.** The score is a plain weighted sum. No
thresholds, no multiplied terms, no model. That is a real constraint on the design and I accepted it
deliberately — because it means the difference between two timetables decomposes *exactly* into
per-criterion contributions, and a department head can verify the ranking with a calculator.

**5. I added the AI last, and on a short leash.** It explains. It never decides.

**6. I validated against a problem I did not design.** The scoring engine reproduces the published
costs of solutions from ITC-2007, an international timetabling competition. That checks the modelling
approach against someone else's data rather than only my own.

---

## How a timetable is actually produced

Three stages. The first two always run; the third only runs when there is no solution.

**Stage 1 — Data checks.** Five arithmetic checks ask "is this even possible?" before any solving
starts. For example: are there enough room-hours in the week for the sessions demanded? No solver
involved.

**Stage 2 — Optimisation.** CP-SAT places all 218 sessions under twelve mandatory rules. It runs
three times under three different weightings, producing three genuinely different valid timetables to
choose between.

**Stage 3 — Diagnosis (only on failure).** If the rules cannot all be satisfied, the system reports
the smallest set of conflicting requirements instead of a bare "impossible" — so the user knows what
to change.

A solve takes minutes, so no web request ever waits for one. Asking for a timetable returns
immediately with a reference number, and the screen polls:

```
PENDING → PREANALYSIS → SOLVING → SCORING → COMPLETED
                     └→ INFEASIBLE → DIAGNOSING → DIAGNOSED
```

### The twelve rules that are never broken

| | | | |
|---|---|---|---|
| **H1** No teacher overlap | **H2** No group overlap | **H3** No room overlap | **H4** Room type matches |
| **H5** Room big enough | **H6** Teacher availability | **H7** Each session placed once | **H8** No day-boundary crossing |
| **H9** Closed slots blocked | **H10** Locked sessions fixed | **H11** Aggregate capacity | **H12** Group hierarchy |

A timetable breaking any one of these is not produced at all — it is not scored down, it is
impossible by construction.

**The academic calendar is configuration, not a rule.** A closed Saturday or a Ramadan schedule is
expressed by marking slots closed; H9 then handles it. No code changes when the calendar changes.

### The seven quality criteria

| Code | Criterion | Weight |
|---|---|---|
| S2 | Student idle time — gaps in a group's day | 0.25 |
| S5 | Teacher preference — preferred windows honoured | 0.20 |
| S3 | Teacher idle time | 0.15 |
| S4 | Extra working day — fewer days on site | 0.10 |
| S6 | Room efficiency | 0.10 |
| S7 | Subject spread across the week | 0.10 |
| S10 | Lunch break preserved | 0.00 |

### Why the score is defensible — the thing to show a sceptic

The top-ranked timetable in the live system scores **81.4384272710004**. That number is not an
opinion. Recompute it from the seven published criterion values:

```
S2   1.000000 × 0.25/0.90  =  0.2777777778
S3   0.981383 × 0.15/0.90  =  0.1635638298
S4   0.622093 × 0.10/0.90  =  0.0691214470
S5   0.550459 × 0.20/0.90  =  0.1223241590
S6   0.861985 × 0.10/0.90  =  0.0957761636
S7   0.772388 × 0.10/0.90  =  0.0858208955
S10  0.233333 × 0.00/0.90  =  0.0000000000
                              ─────────────
                        × 100 = 81.4384272710004
```

Identical to the figure the application reports, to the last digit. The same property makes the
comparison screen work: the contributions of a difference between two timetables sum **exactly** to
the difference in score — verified in production at zero error.

---

## The AI, and its leash

| It may | It may not |
|---|---|
| Explain why one timetable scores above another | Place or move a session |
| Answer questions about a run in plain language | Calculate or change any score |
| Summarise a candidate's strengths | Change the ranking |
| Suggest a change for a human to approve | Touch the database at all |

Every number in an AI answer must already appear in the material it was handed. If it does not, the
answer is discarded and the raw figures are shown instead.

**Tested live in production.** Asked *"why is the first candidate ranked above the others?"* — a
question its context did not cover — the deployed assistant replied that the context did not contain
ranking information and it therefore could not answer. It refused rather than inventing something
plausible. That refusal is the guarantee working.

**And with the AI switched off entirely, everything else still works** — generation, scoring, ranking,
comparison, publishing. Only the prose disappears, replaced by the same figures in a computed form.
The AI is an explanation layer, not a dependency.

---

## Problems I hit, and what I did about them

This section is the honest one. Each of these cost real time and changed how I work.

**A plausible conclusion nobody tried to disprove cost three days.** I checked whether the timetable
was feasible by looking at how full the week was — 71.4% of slots occupied, comfortable. It was
wrong. The right measure looks at *two-period windows*, where occupancy is 90.9% with only 8 spare
slots in the entire week. The instance was genuinely almost-infeasible and I had convinced myself it
was fine. **What changed:** I now write down what would prove me wrong before I accept a reassuring
number.

**The solver reported an objective value that did not match the solution it returned.** Nothing broke
— because the analysis layer is architecturally forbidden from reading the solver's objective and has
to recompute the score from the actual placements. A separation I had introduced for design reasons
caught a real bug in a third-party library.

**One criterion was priced 28× too high for weeks.** The same seven formulas exist twice on purpose —
once over finished timetables, once as solver expressions — because the solver may not import the
analysis layer. They agreed on shape but not on *units*. **What changed:** a test now forces the two
implementations to produce the same number, not just the same structure.

**Git silently swallowed the entire dataset.** The `.gitignore` inherited from GitHub's Python
template contains `instance/` — meaning Flask's instance folder — and it matched `data/instance/` at
any depth. **What changed:** an explicit un-ignore, and I check `git status` after adding data files.

**Docker reported success while connecting me to the wrong database.** `docker compose up -d` started
the container, reported healthy, showed the port mapping — while every connection from the host
reached a *different* PostgreSQL already on 5432. A refused connection would have been the lucky
outcome; a local server that accepted the same credentials would have taken the migrations.
**What changed:** the port is configurable, and I verify which server version I actually reached.

**Five pieces of text failed accessibility contrast and I could not see it.** They measured
2.55–2.64:1 against a 4.5:1 requirement. They looked fine to me. An automated sweep across 545 text
nodes found them. **What changed:** I do not trust visual judgement for contrast.

**One hard-coded line made the whole application undeployable.** The list of browser origins allowed
to call the API was a literal in the source. It worked perfectly on my machine and could never work
anywhere else. **What changed:** it is configuration now — and that was the single blocker between
"it runs" and "it is deployed".

**The obvious hosting choice was the wrong one.** I planned to put everything on Vercel. Vercel runs
code in short-lived functions that stop after seconds; a solve takes minutes in a background thread.
I checked this against Vercel's current documentation rather than assuming, found four specific ways
it would fail, and split the deployment instead — interface on Vercel, solver on a server that stays
alive. **It required one new configuration file and no change to any application code**, which is the
sign the architecture was right.

---

## Architecture

Four layers, one deployable unit:

| Layer | Technology | Responsibility |
|---|---|---|
| Presentation | React 18 + TypeScript + Vite | Grids, comparison, timetable views |
| Application | FastAPI + PostgreSQL | REST API, data, runs, publication |
| Decision | OR-Tools CP-SAT | Assigns a slot and room to each session. **Nothing else may** |
| Analysis | Python, no solver access | Sub-scores, ranking, exact decomposition, dominance |

### The rules that fail the build

The separation between the decision layer and the analysis layer is a **requirement, not a
description**. Thirteen import contracts enforce it automatically — the analysis layer cannot import
the solver, the AI cannot import the database, the API cannot import the solver, and so on. A
violation fails the check rather than a code review.

Every contract was verified to actually fire by deliberately introducing a violation. One of them
broke twice on new code within a week of being added, and both times the fix was to move the import,
never to relax the rule.

⚠️ **These checks are run by a person** — `scripts/run-checks.ps1`. There is no CI in this repository.

### Scale of the reference instance

218 sessions · 44 teachers · 51 groups · 20 rooms · 425 students · 32 courses · 30 slots (28 open)

---

## Deployment

Three services, each chosen for one reason:

| Part | Runs on | Why |
|---|---|---|
| Interface (React) | **Vercel** | Compiles to static files; served worldwide free, redeploys on push |
| Application + solver (Python) | **Render** | A solve runs for minutes in a background process — it needs a server that stays alive |
| Database (PostgreSQL 17) | **Supabase** | Managed Postgres in the EU; runs, candidates, accounts and publications persist here |

The browser always calls `/api` on its own address, and Vercel forwards those requests to the solver
server. Nothing about the application's behaviour differs between a developer machine and production.

### Try it

**https://optiedt-ai-timetabling.vercel.app**

| Username | Role | Can do |
|---|---|---|
| `responsable` | Timetable Officer | Generate, compare, publish, load data |
| `administrateur` | Administrator | Academic calendar, user accounts |
| `t001` | Teacher | Declare availability, read own timetable |
| `etudiant` | Student | Read their group's published week |

A completed timetable with three ranked candidates is already loaded.

⚠️ **Honest limits of the free hosting tier**, none of which are limitations of the software:

- **First page load takes up to a minute** — the server sleeps when idle and must wake.
- **Generating a *new* timetable takes 20 minutes or more** — the free instance provides one tenth of
  a processor, and the solver is built to use many. On the development machine the same code produces
  all three candidates in **287 seconds**.
- **Examination calendars are not stored** — by design, no requirement asked for it. They live only
  while the server runs, so generate and view one in a single sitting.
- **All accounts share one password** — demonstration seeding only.

---

## Running it locally

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+, Docker.

```bash
scripts/bootstrap.ps1
```

Creates the virtualenv, installs both dependency sets, copies `.env.example` to `.env`, starts
PostgreSQL. Then:

```bash
docker compose up -d
```

⚠️ **If this machine already runs PostgreSQL on 5432, that command appears to work and does not** —
see "Problems I hit" above. Move the host port and point the URL at it:

```bash
echo OPTIEDT_POSTGRES_PORT=5433 >> .env
```

Set `OPTIEDT_DATABASE_URL=postgresql+psycopg://optiedt:optiedt@localhost:5433/optiedt` in
`backend/.env`, then confirm which server you reached — the container is PostgreSQL **17**:

```bash
docker exec optiedt-postgres psql -U optiedt -d optiedt -tAc "select version();"
```

```bash
cd backend && uv run alembic upgrade head && uv run uvicorn optiedt.api.main:app --reload
```

```bash
cd frontend && npm run dev
```

There is no registration screen — accounts come from a seed command, which **refuses to run if any
account already exists**:

```bash
cd backend && uv run python -m optiedt.services.seed
```

⚠️ Set `OPTIEDT_SECRET_KEY`. Its default is published in this repository, so tokens signed with it
could be forged by anyone who has read the source. With `OPTIEDT_ENVIRONMENT=production` the
application **refuses to start** on that default, so the failure is loud instead of invisible.

The API serves its own interactive documentation at `http://localhost:8000/docs`. That generated page
**is** the API reference — there is no hand-written copy to fall out of date with it.

---

## Repository layout

```
docs/            Working documentation. Start at CLAUDE.md, then docs/dashboard.md
  specifications/  The three PDFs — the contract. Not the working reference
  decisions/       Thirteen ADRs. Read before reopening a settled question
backend/         FastAPI app, CP-SAT model, analysis layer
  src/optiedt/validation/   ITC-2007 benchmark harness. Runs against the product,
                            never inside it — no shipped code imports it
frontend/        React interface
data/            Instance generator, the 13 instance files, verification checks
scripts/         Bootstrap, checks, verification
```

## The interface

React 18 + Vite 5, plain CSS in six token-driven layers, no UI framework. IBM Plex Sans for the
interface and IBM Plex Mono for figures and codes, both **self-hosted** — no CDN, so it renders
identically on a machine with no internet.

The signature surface is the **decomposition ledger** on the Compare screen: because the score is a
weighted sum of normalised values, the difference between two candidates decomposes exactly, and the
ledger draws each term either side of a zero axis with the sum landing on the difference.

⚠️ **This interface is a frozen baseline, accepted 2026-08-13.** Read
[`docs/UX_DECISIONS.md`](docs/UX_DECISIONS.md) before changing a visual decision — several entries
record a specific defect that a plausible "improvement" would bring back.

## Documentation

**[`CLAUDE.md`](CLAUDE.md) is the entry point for anyone about to change code.** It carries the
read-order, the seven invariants, the frontend baseline, what is decided and what is still open.

| Read this | For |
|---|---|
| [`docs/dashboard.md`](docs/dashboard.md) | **Where the project is.** The one page that answers it |
| [`docs/architecture.md`](docs/architecture.md) · [`docs/domain-model.md`](docs/domain-model.md) | How it is built |
| [`docs/constraint-model.md`](docs/constraint-model.md) · [`docs/scoring-and-explanation.md`](docs/scoring-and-explanation.md) | The solver and the score |
| [`docs/AI_BEHAVIOR.md`](docs/AI_BEHAVIOR.md) | Grounding, fallback, what the AI must never claim |
| [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) · [`docs/UX_DECISIONS.md`](docs/UX_DECISIONS.md) | The interface, and why |
| [`docs/API_OVERVIEW.md`](docs/API_OVERVIEW.md) | 33 endpoints, read from the live schema |
| [`docs/TESTING.md`](docs/TESTING.md) | Commands and the coverage map |
| [`docs/deployment.md`](docs/deployment.md) | How it is deployed, and the reasoning |
| [`docs/supervisor/INTERFACE_WALKTHROUGH.md`](docs/supervisor/INTERFACE_WALKTHROUGH.md) | A non-technical guide to the screens |
| [`docs/decisions/`](docs/decisions/) | Thirteen ADRs — read one before arguing with it |

The three PDFs in `docs/specifications/` are the contractual specification: authoritative on *what was
promised*. The working documents in `docs/` are authoritative on *how it is built* — including several
places where the PDFs contradict each other or leave something undefined. Those are catalogued in
`docs/open-questions.md` rather than resolved silently.

## Status

**Deployed for evaluation** — interface on Vercel, application and solver on Render, PostgreSQL 17 on
Supabase. The production database holds one completed run with three ranked candidates and one
published timetable.

At the release freeze on **2026-08-13**: frontend **196/196** tests, typecheck and production build
clean; backend **633** fast tests and **74** database tests against real PostgreSQL 17; **245**
acceptance tests collected over 23 requirements; **0** contrast failures across 545 text nodes;
**0** secrets tracked.

> ⚠️ **This section deliberately carries no phase, progress or requirement count.**
> [`docs/dashboard.md`](docs/dashboard.md) is the only place project state lives. This section said
> something stale in four successive phases, because a closing audit cannot verify the sentence
> recording its own phase closing. The fix was to stop keeping a second copy here.

## Author

Mohamed Jawad Touir — company internship project, academic year 2025–2026.
