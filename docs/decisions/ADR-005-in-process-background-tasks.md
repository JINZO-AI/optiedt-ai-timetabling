# ADR-005 — In-process background task, not a message broker

**Status:** Accepted
**Date:** 2026-07-23 (specification phase)

## Context

A run produces several candidates under distinct weight profiles, solved one after the other. Total
duration is counted in minutes. The diagnosis run is slower still, since it is restricted to a single
worker.

**A browser request cannot be held open for that long.** Some asynchronous mechanism is required.

## Decision

**A background task in the same process as the server.**

A run is recorded in the database with its state, parameters and seed. A background task picks it up,
solves the profiles one after the other, and records each candidate as soon as it is obtained. The
interface polls the run's state at intervals and displays candidates as they appear.

```
POST /runs   → 202, { run_id }        immediately, no waiting
GET  /runs/{id}  → polled     PENDING → PREANALYSIS → SOLVING → SCORING → COMPLETED
                                                    └────────► INFEASIBLE → DIAGNOSING → DIAGNOSED
                                                    └────────► FAILED
```

## Consequences

- **No request is held open for the duration of a solve.** The interface follows progress instead.
- Candidates are visible as they are produced, not only when the whole portfolio finishes — which
  matters when the first profile completes in seconds and the third takes minutes.
- Run state lives in the database, so it survives a page reload and is inspectable.

> ⚠️ **Correction, 2026-08-01 (Phase 4 closing audit).** Two of those consequences are **not** what was
> built, and they are stated above as though they were:
>
> - **Candidates are not visible as they are produced.** `services/portfolio.py` returns the whole
>   portfolio at the end, so the run shows `SOLVING` for the full 105–150 s and every candidate appears
>   at once. The decision this ADR records — in-process rather than a broker — is unaffected; only this
>   claimed benefit is unrealised. Closing it means changing a Phase 3 module's contract.
> - **Run state does not live in the database.** It is in memory (`services/runs.py`), so a restart
>   loses every run and a page reload survives only because the browser is not the store. Persistence is
>   FR-19, Phase 5.
>
> The "cost" paragraph below therefore understates the position today: a restart loses **all** runs, not
> only in-flight ones.
- **The task shares the process with the server**, consistent with ADR-004: no serialisation of the
  problem, no second deployment artefact.

**The cost:** a server restart loses an in-flight run. Acceptable at a load of a few generations per
semester, where re-running is cheap and rare.

**When to revisit — recorded so it can be.** A broker would bring a component to install, secure and
monitor. That cost is not justified by a few generations per semester on a single server. **The decision
would have to be reconsidered if several departments generated at the same time**, which is the specific
condition that changes the answer.

## Alternatives considered

**Celery or RQ with Redis/RabbitMQ** — **set aside**: a component to install, secure and monitor, for a
load that does not need it. Reconsider under concurrent multi-department use.

**Synchronous solving inside the request** — **rejected**: minutes-long requests, browser and proxy
timeouts, and no way to show partial results.

**Polling replaced by WebSockets** — not decided here. Polling is specified and sufficient; a push
channel would be an optimisation, not a change of architecture.

## References

Project Plan and Methodology §5.6 · SRS §4.3 · Cahier des Charges §7.1
