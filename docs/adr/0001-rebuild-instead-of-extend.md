# ADR 0001 — Rebuild the product instead of extending the internship code

**Status:** Accepted

## Context

The audit (`docs/audit/original-repository-audit.md`) found that the original code models a
single department whose data lives in CSV files, with institution-specific enumerations,
a closed catalogue of twelve hard and seven soft rules, solves inside the web process, no
manual editing, no versioned publication and in-memory examination results. Its tests pass
and several ideas are sound, but every layer embodies the single-department assumption.

## Decision

Replace the implementation. Keep the ideas that proved sound (independent recomputation of
results, reproducibility discipline, pre-analysis before solving, an LLM that decides
nothing) as principles of the new design. Keep the original specifications as archived
historical input. The original code stays reachable in git history (`main`, `4c9f933`).

## Alternatives considered

- **Incremental refactoring.** Rejected: moving academic data from CSV to relational tables
  changes the solver input, the API and every screen; there is no stable core to refactor
  around.
- **Keep the solver package and rebuild around it.** Rejected: it depends on the fixed enums
  and the 12-rule catalogue; the objective and room encodings would need rewriting anyway.

## Consequences

- No backward compatibility with the old API or CSV format. A CSV/XLSX import pipeline with
  column mapping replaces the fixed eleven-file format.
- The old documentation is removed rather than left to contradict the new system.
