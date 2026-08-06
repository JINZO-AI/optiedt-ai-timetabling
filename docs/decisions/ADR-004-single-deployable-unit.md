# ADR-004 — One deployable unit, not microservices

**Status:** Accepted
**Date:** 2026-07-23 (specification phase)

## Context

The system has four layers — presentation, application, decision, analysis — with a genuine and
strictly enforced separation between the last two. That separation might suggest deploying them
separately.

## Decision

**A single deployable unit.** The server and the solving engine share one execution environment; the
generation runs as a background task in the same process.

## Consequences

- **The whole problem is not serialised between two programs at every generation.** With 218 sessions,
  51 groups, 44 teachers and 20 rooms, sending the instance across a process boundary for each run would
  add cost and a failure mode for no benefit.
- Simpler to develop, test and install — which matters in a four-week project delivered to a department
  without a platform team.
- The solving engine being written in Python, the server is written in Python too, so it calls the
  engine directly rather than exchanging data between two programs.

**The separation of layers is preserved by module boundaries and by `import-linter`, not by process
boundaries.** ⚠️ *Corrected 2026-08-06: this said `in CI`. There is no CI configuration in the
repository — the contracts run in `scripts/run-checks.ps1`, which a person invokes. The argument
below is unaffected, because it rests on the check being STATIC rather than on who triggers it.* This is the important point: the invariant that the analysis layer cannot reach
the solver is enforced statically, at build time, which is *stronger* than a network boundary and costs
nothing at runtime. A deployment split would have enforced the same rule more expensively and less
reliably.

**When to revisit.** Separate services are useful when several teams work in parallel, or when parts of
the system must scale separately. Neither applies here. If several departments ever generate timetables
simultaneously, this decision — and ADR-005 — should be reconsidered together.

## Alternatives considered

**Solver as a separate service** — **rejected**: transmits the whole problem at each generation, adds a
component to deploy and monitor, and buys an isolation the import linter already provides.

**Full microservice decomposition** — **rejected**: appropriate to parallel teams and independent
scaling, neither of which describes a solo four-week project on one server.

## References

Project Plan and Methodology §5.4 · Cahier des Charges §7.1 · SRS §2.1
