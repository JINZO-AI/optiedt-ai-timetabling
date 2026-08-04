# Architecture

## The idea the system is built on

The specification separates **two decisions of different natures** and refuses to let them mix.

| | Decision | Nature | Cost of an error | Method |
|---|---|---|---|---|
| 1 | Which session goes in which slot and room | Satisfaction — a rule holds or it does not | An unpublishable timetable | CP-SAT, correct by construction |
| 2 | Which valid timetable is better | Compromise between criteria that cannot all improve together | A worse ranking, still usable | Weighted sum, exact and hand-recomputable |

Methods that *guarantee* go on decision 1. Methods that *estimate* go on decision 2. The language model
is admitted only because it touches neither.

Every structural choice below follows from this. When a change seems to require blurring the line,
the change is wrong.

---

## The four layers

```
┌──────────────────────────────────────────────────────────────┐
│  PRESENTATION — React + TypeScript                           │
│  Availability grid · generation screen · comparison screen   │
│  Timetable views · conflict report · assistant panel · admin │
└───────────────────────┬──────────────────────────────────────┘
                        │  HTTPS · JSON · bearer token
┌───────────────────────▼──────────────────────────────────────┐
│  APPLICATION — FastAPI                                       │
│  REST surface · RBAC · run lifecycle · publication           │
│                            │                                 │
│                            ▼                                 │
│                      PostgreSQL                              │
│                                                              │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  PRE-ANALYSIS  │  │   DECISION   │  │    ANALYSIS      │  │
│  │  5 arithmetic  │  │   CP-SAT     │  │  sub-scores      │  │
│  │  checks        │  │              │  │  ranking         │  │
│  │  NO SOLVER     │  │  the only    │  │  decomposition   │  │
│  │                │  │  thing that  │  │  dominance       │  │
│  │                │  │  places a    │  │  NO SOLVER       │  │
│  │                │  │  session     │  │  NO PLACEMENT    │  │
│  └────────────────┘  └──────▲───────┘  └────────┬─────────┘  │
│                             │                   │            │
│                    ┌────────┴───────────────────▼─────────┐  │
│                    │  RECOMMENDATIONS                     │  │
│                    │  closed catalogue of 3 actions       │  │
│                    │  writes a weight, a lock, an         │  │
│                    │  exclusion — never a placement       │  │
│                    └──────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  ASSISTANT — optional, switchable off                   │ │
│  │  context builder → LLM over HTTPS → numeric verifier     │ │
│  │  NO DATABASE ACCESS · NO FIGURE OF ITS OWN              │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### What each layer may and may not do

| Layer | May | May **not** |
|---|---|---|
| Presentation | Display, filter, print, ask | Compute a score, decide an order |
| Application | Persist, authorise, orchestrate runs, publish | Place a session |
| Pre-analysis | Read the instance, report structural risk | Call the solver |
| Decision | Assign slots and rooms | Read a score, know a weight profile's *name* |
| Analysis | Read candidates as plain data, compute figures | Import the solver, write a placement, mutate a candidate |
| Recommendations | Write a weight, a lock, an exclusion; launch a new run | Write a placement |
| Assistant | Receive a built payload, return text | Reach the database, state an unverified figure |

The forbidden edges are the point. **An error in the analysis layer produces a wrong ranking and never
an invalid timetable** — that is the whole reason the boundary exists, and it only holds while the
boundary does.

### Enforcement

`backend/.importlinter` turns **ten** of these into build failures:

- `optiedt.analysis` ⇸ `optiedt.solver` — invariant 1
- `optiedt.analysis` ⇸ `optiedt.db`
- `optiedt.assistant` ⇸ `optiedt.db` — invariant 4
- `optiedt.assistant` ⇸ `optiedt.solver`
- `optiedt.preanalysis` ⇸ `optiedt.solver` — stage 1 independence
- `optiedt.domain` ⇸ every other package, and ⇸ `fastapi`, `sqlalchemy`, `ortools` — purity
- `optiedt.instance` ⇸ the decision and application layers — the loader is a leaf
- every product package ⇸ `optiedt.validation` — the benchmark harness is not product code
- `optiedt.api` ⇸ `optiedt.solver` — added Phase 4, verified to fire before being relied on
- `optiedt.api` ⇸ `optiedt.db` — added Phase 5 M3, likewise verified by injecting a violation

⚠️ The ninth names the **solver only, not the analysis layer**. The comparison endpoint has to type its
response against `analysis.interfaces` (`Decomposition`, `Contribution`, `DominanceVerdict`), which are
plain frozen dataclasses; forbidding that import would force those shapes to be duplicated in the API
for no gain. What the contract actually prevents is a router launching a solve inside a request
handler — the shape ADR-005 and the run lifecycle exist to rule out.

`api → preanalysis.checks` (`CheckResult`, added Phase 5 M1) is the same kind of import and is
permitted for the same reason: a frozen dataclass typed into a response. The line the module map draws
is about *calling* a layer, not about naming its data shapes.

Run with `uv run lint-imports`. A specification sentence that is only prose decays; one that fails CI
does not.

⚠️ **Keep this list and `backend/.importlinter` in step.** This section said "three" until 2026-08-01,
by which time the file carried eight (and "nine" until 2026-08-04, by which time it carried ten) — a contract that exists but is not documented gets weakened by
someone who never knew it was load-bearing. The file is the authority; this list restates it.

---

## The generation pipeline — three stages

A run always passes through stage 1 and stage 2. It enters stage 3 **only** when stage 2 returns
`INFEASIBLE`.

### Stage 1 — Pre-analysis

Five arithmetic checks, no solver involved. Their purpose is to tell apart two situations a solver
reports identically: *this instance genuinely has no solution* and *the model has a bug*.

**Implemented in `optiedt.preanalysis.verifications` (Phase 5 M1).** Every run records the five
results, passing or failing, and `GET /runs/{id}` returns them. Two consequences worth stating:

- **A failing check does not stop the run.** Stage 1 then stage 2, always. Reporting a structural
  proof of infeasibility *and* the solver's conflict set is more useful than either alone — and when
  CP-SAT returns `UNKNOWN` on an infeasibility it cannot prove (the C-13 shape), the pre-analysis
  report is the only thing that says why.
- **An empty check list means the stage did not run**, never "verified, nothing wrong".

They run in milliseconds and they are the primary debugging instrument for this project, because the
reference instance sits at **91% computer-laboratory occupancy** (of two-period windows — the figure
that binds; see `docs/data-and-instance.md`). At that saturation a modelling regression surfaces as
`INFEASIBLE`, not as a slow solve — and without stage 1 you cannot tell which you are looking at.

⚠️ **A check that is necessary but not sufficient is worse than no check**, because a false pass sends
the next failure to the wrong suspect. Verification 2 originally compared period totals, passed an
infeasible instance, and cost three sessions of debugging aimed at the model (C-13). Every check must
state which kind it is.

Checks and their expected results on the reference instance are in `docs/data-and-instance.md`.

### Stage 2 — Optimisation

- One solve **per weight profile**, executed one after the other, not concurrently.
- Carries the objective. Uses all workers.
- Bounded by `max_deterministic_time` — **not** wall-clock (ADR-011). A wall-clock ceiling exists only
  as a hang backstop; reaching it is an anomaly to log, not a normal exit.
- Each candidate is recorded and scored as soon as it is obtained, so the interface can show it while
  the remaining profiles are still solving.

⚠️ **That last point is the intended design and is NOT implemented.** `services/portfolio.py` scores
each candidate as it is obtained, exactly as written — but it returns the whole portfolio in one
`PortfolioReport` at the end, so `tasks/executor.py` can only store them together and the run moves
`SOLVING → SCORING → COMPLETED` with all candidates appearing at once. On the reference instance that
means roughly 105–150 s of a screen showing `SOLVING` and nothing else.

Nothing is wrong: the candidates are correct and the states are honest. What is missing is
*incremental* reporting, which needs `generate_portfolio` to publish each candidate through a callback
or the store rather than in its return value. Recorded here rather than fixed because it changes a
Phase 3 module's contract. **Do not describe the interface as showing candidates as they appear** —
`frontend/README.md` did, and it was false for the whole of Phase 4.

### Stage 3 — Diagnosis

Entered only on `INFEASIBLE`. **Built in Phase 5 M2** (`CpSatSolver.diagnose`), through the *same*
constraint builders stage 2 uses — a separate diagnosis model could name a conflict that does not
exist in the model actually solved.

**The mechanism: withdraw one rule at a time and solve plainly.** Establish first that no timetable
exists. Then, for each rule that may be withdrawn — H1, H3, H7, H12 (C-6) — solve without it: if the
model is *still* infeasible, that rule was not needed for the contradiction and is dropped for good.
What survives is the report.

**This only works if the withdrawable set is 1:1 and non-redundant.** See C-6: H2 is subsumed by H12
and H11 is implied by H3, so a report could otherwise name a rule the user cannot act on independently.

Three properties, and **only the second is imposed by CP-SAT**:

1. **A single worker** — kept for **reproducibility of the verdict**, not because the solver requires
   it. `max_deterministic_time` is a per-worker budget, so more workers do more total work and could
   flip an `UNKNOWN` into an `INFEASIBLE` between machines. A report naming different rules on
   different machines would be worse than none.
2. **No objective** — imposed. A feasibility question is being asked; occupancy and the objective are
   not built at all.
3. **Minimal only when proved.** Every removal is tested, so the surviving set is normally irreducible
   and `is_minimal` says so. A removal the solver could not decide keeps its rule *for want of
   evidence*, and the flag goes false. ⚠️ "Minimal" means irreducible **among the four withdrawable
   rules**, never in general.

⚠️ **Several minimal explanations can exist and exactly one is reported.** When two rules both forbid
the same placement, either alone explains the conflict. Rules are withdrawn in catalogue order, so the
answer is arbitrary between them but **reproducible**.

⚠️ **This replaced the enforcement-literal mechanism this section used to specify, on measurement —
C-17, resolved 2026-08-04.** Attaching an enforcement literal to `no_overlap` or `cumulative` takes it
out of presolve: an area contradiction a plain solve proves in **0.0 s** returned **`UNKNOWN` after
240 s** under assumptions. The mechanism now answers `('H3',)`, minimal, in **1.9 s** on that same
instance. Two of the three properties above changed with it, and the "imposed by CP-SAT" framing was
part of what made the old design look unarguable — it was imposed by the *assumption mechanism*.

---

## The run lifecycle

Solving takes minutes. No HTTP request is held open for it.

```
POST /runs                → 202, { run_id }        (returns immediately)
        │
        ▼
   run recorded with state=PENDING, its seed, profiles, budget
        │
        ▼
   background task picks it up  ─── stage 1 ──► stage 2 (per profile) ──► stage 3 if needed
        │                                          │
        │                                    candidate recorded + scored
        │                                          │
GET /runs/{id}   ◄──── polled at intervals ────────┘
        │
        ▼
   states: PENDING → PREANALYSIS → SOLVING → SCORING → COMPLETED
                                            └────────► INFEASIBLE → DIAGNOSING → DIAGNOSED
                                            └────────► FAILED
```

The task runs **in-process**, not behind a message broker. A broker would add a component to install,
secure and monitor for a load of a few generations per semester on one server (ADR-005). That decision
is recorded so it can be revisited if several departments ever generate at once — which is the
condition that would change the answer.

---

## Module map

| Package | Holds | Depends on |
|---|---|---|
| `optiedt.core` | Config, security, logging | — |
| `optiedt.domain` | Entities, enums, value objects. **Pure** — no I/O, no ORM, no framework | — |
| `optiedt.db` | SQLAlchemy models, session, repositories | `domain` |
| `optiedt.api` | Routers, schemas, dependencies, RBAC | `domain`, `services` |
| `optiedt.services` | Use cases: runs, comparison, publication | everything below |
| `optiedt.preanalysis` | The five checks | `domain` |
| `optiedt.solver` | Variables, constraints, objective, diagnosis | `domain` |
| `optiedt.analysis` | Criteria, scoring, ranking, decomposition, dominance | `domain` |
| `optiedt.recommendations` | Catalogue, translation to solver input | `domain`, `analysis` |
| `optiedt.assistant` | Adapter, context builder, verifier | `domain`, `analysis` |
| `optiedt.tasks` | Background run executor | `services` |
| `optiedt.validation` | **Not product code.** The ITC-2007 benchmark harness | nothing in `optiedt` |

Five boundaries carry design weight rather than convenience:

- **`preanalysis` is not inside `solver`.** It needs no solver by definition, it is stage 1 of every
  run, and it is how a near-critical instance stays debuggable.
- **`recommendations` is not inside `analysis`.** Different permissions: analysis writes nothing;
  recommendations write exactly three fields. That difference is testable, so it gets a boundary.
- **`assistant` is separate and flagged off-able.** Degraded mode is a requirement — switching it off
  must remove text and nothing else.
- **`domain` is pure.** It is imported by the solver, the analysis layer and the ORM alike; a framework
  import there would leak into all three.
- **`validation` runs *against* the product, never inside it.** It models ITC-2007 — a different
  problem, with room capacities instead of room types, curricula instead of a group hierarchy and four
  soft costs that are none of S2–S10 — so it shares no code with `solver`, and the contract
  `benchmark-validation-is-not-product-code` fails the build if anything shipped comes to depend on it.
  It sits under `src/` rather than under `tests/` for one reason: mypy strict and ruff cover `src/`, and
  a validation harness whose arithmetic is wrong reports a wrong verdict with full confidence.

## Deployment

One unit. The server and the engine share an execution environment, which avoids serialising the whole
problem between two processes at every generation (ADR-004). Development uses `docker compose` for
PostgreSQL and runs the API and frontend natively for reload speed.

⚠️ **The compose host port is configurable and defaults to 5432.** A machine already running its own
PostgreSQL there makes `docker compose up -d` succeed while every host connection reaches the *other*
server — container healthy, mapping shown, nothing wrong at the Docker layer. Set
`OPTIEDT_POSTGRES_PORT` and a matching `OPTIEDT_DATABASE_URL`; see `README.md`.

**Which store a process uses is configuration** (`persistence`), never detection. `services/stores.py`
is the factory, so `optiedt.api` never imports `optiedt.db` — the tenth contract. A store that fell
back to memory when the database was unreachable would lose every run while the application looked
healthy, which is the precise opposite of what FR-19 asks for.
