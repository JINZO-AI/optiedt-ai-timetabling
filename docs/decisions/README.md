# Architecture decision records

Each ADR records one decision, the reasoning behind it, and what it costs. They exist so that a
settled question is not reopened by someone who does not know why it was settled.

**Read the ADR before arguing with a decision.** If the reasoning no longer holds — because a
constraint changed, not because it is inconvenient — write a new ADR that supersedes it. Do not edit an
accepted one; the record of what was believed at the time is the point.

| ADR | Decision | Status |
|---|---|---|
| [001](ADR-001-cp-sat-for-assignment.md) | CP-SAT for session assignment | Accepted |
| [002](ADR-002-weighted-sum-for-ranking.md) | Weighted sum for ranking, dominance as a complement | Accepted |
| [003](ADR-003-calendar-as-configuration.md) | Institutional calendar rules as configuration, not constraints | Accepted |
| [004](ADR-004-single-deployable-unit.md) | One deployable unit, not microservices | Accepted |
| [005](ADR-005-in-process-background-tasks.md) | In-process background task, not a message broker | Accepted |
| [006](ADR-006-llm-excluded-from-decisions.md) | The language model does not place, score or rank | Accepted |
| [007](ADR-007-closed-recommendation-catalogue.md) | Closed catalogue of three recommendation actions | Accepted |
| [008](ADR-008-generated-instance.md) | Generated instance; public sources given roles, never merged | Accepted |
| [009](ADR-009-instance-derived-bounds.md) | Normalisation bounds derived from the instance | Accepted |
| [010](ADR-010-assistant-in-increment-1.md) | The assistant is committed to increment 1 | Accepted |
| [011](ADR-011-deterministic-time-limit.md) | Solve under `max_deterministic_time`, not wall clock | Accepted · **amended 2026-07-30** |

ADRs 001–008 record decisions taken during the specification phase; their reasoning is drawn from the
three documents in `docs/specifications/`. ADRs 009–011 record decisions taken when those documents
were found to contradict each other or to leave something undefined — see `docs/open-questions.md`.

**ADR-011 is the only one amended so far**, and the distinction matters: its decision was never
reversed. Measurement showed it was *incomplete* — it named a mechanism (deterministic time) that bounds
the amount of work but does not order the race between parallel workers, and omitted the parameter that
does (`interleave_search`). Amending in place was right because the decision still stands; a superseding
ADR would have implied it did not. **If a future measurement refutes a decision rather than completing
it, write a new ADR instead.**

## Template

```markdown
# ADR-NNN — Title

**Status:** Proposed | Accepted | Superseded by ADR-NNN
**Date:** YYYY-MM-DD

## Context
What forced a decision.

## Decision
What was decided, stated so it can be checked against code.

## Consequences
What this costs, and what it makes possible. Include the bad parts.

## Alternatives considered
What was rejected and why. A rejected option with no stated reason invites re-litigation.
```
