# ADR 0003 — PostgreSQL as system of record and as the job queue

**Status:** Accepted

## Context

All institutional data is relational (rooms belong to buildings, activities reference
courses, groups and instructors) and needs foreign keys, uniqueness and transactions. Jobs
must be durable, visible to users, cancellable and recoverable after crashes.

## Decision

- PostgreSQL 16 is the only stateful service.
- Schema changes go through Alembic migrations; the API refuses readiness when the database is
  not at the expected revision.
- The solver run row **is** the job. Workers claim runs with
  `SELECT … FOR UPDATE SKIP LOCKED`, hold a lease renewed by heartbeats, and write progress
  events to `solver_run_events`. A run whose lease expires is requeued once, then failed.
- Cancellation is a flag on the run, polled by the worker and propagated to CP-SAT's
  `stop_search`.

## Alternatives considered

- **Redis + Celery/RQ/Dramatiq.** Adds a second stateful service to install, secure and back
  up; jobs and domain records could diverge (job lost while run row says "queued").
- **Procrastinate** (PostgreSQL task library). Viable, but the product has essentially one job
  type whose state *is* domain data shown to users; a separate generic job table would
  duplicate it.

## Consequences

- Enqueueing is transactional with the run record: a run cannot exist without its job.
- Throughput is bounded by PostgreSQL row locking, orders of magnitude above the need.
- The UI polls run progress (1 s interval while running); no WebSocket infrastructure.
