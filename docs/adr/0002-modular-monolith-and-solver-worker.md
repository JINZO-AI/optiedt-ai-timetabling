# ADR 0002 — Python modular monolith with a separate solver worker process

**Status:** Accepted

## Context

Optimization runs take seconds to many minutes and use every CPU core. The web API must stay
responsive, survive a solver crash, and let users leave and return to a running job. The
expected load is a handful of solves per day per institution, plus interactive editing.

## Decision

One Python codebase (`optiedt`), deployed as two process types from one image:

- `api` — FastAPI application: authentication, CRUD, editing, validation, publication,
  exports. Never runs a full solve in a request.
- `worker` — claims solver runs from PostgreSQL, compiles, solves, validates and persists.
  Several worker processes may run; each claims one run at a time.

Internally the code is organised by domain module (organisation, people, academic data,
terms, scheduling, solver, evaluation, publication, imports, exports, assistant) with
import rules enforced by `import-linter`.

Python is chosen because OR-Tools CP-SAT's first-class API is Python, and the same language
serves data import (openpyxl), documents (WeasyPrint) and the web layer (FastAPI, Pydantic,
SQLAlchemy 2), all mature and widely staffed.

## Alternatives considered

- **Microservices** (separate solver service with its own API). Rejected: network contracts and
  deployment units without a scaling or ownership reason; the worker already isolates CPU
  load and crashes.
- **Java + Timefold or UniTime cpsolver.** Strong local search, but no infeasibility proofs,
  and a second language for the data and document tooling.
- **Solving in API threads** (the original design). Rejected: no isolation, no recovery,
  contention with request handling.

## Consequences

- Each run is solved in a child process the worker starts for it (`spawn`), so a native crash,
  runaway memory or a hung search ends that child only: the worker records the failure with
  its exit code and keeps serving the queue. The child receives the run's snapshot and
  configuration and returns plain JSON; it never touches the database. (Measured need:
  OR-Tools 9.15 aborts the process on one cancellation path; see ADR 0018 and
  `solver/engine.py`.)
- If the worker itself dies, the run lease expires and the run is requeued once, then
  failed. A worker asked to stop (SIGTERM) stops its child and puts the run back in the
  queue without counting the attempt.
- Long computations are job-shaped everywhere: request → persisted job → progress → result.
- Interactive operations that need optimization (move suggestions with chained repairs) run as
  short worker jobs; pure evaluations (validating a move) run in the API because they are
  milliseconds of Python.
