# ADR 0009 — Independent validator and metrics, separate from the solver

**Status:** Accepted

## Context

A solver bug that produces an invalid timetable is the most damaging possible defect. The
original project recomputed scores independently but trusted feasibility.

## Decision

- `optiedt.evaluation` checks every hard requirement and computes every objective metric
  directly from snapshot data and assignments. It shares no code with `optiedt.solver`
  beyond the snapshot data classes; `import-linter` forbids imports in either direction.
- Every solver result is validated before it is stored. A hard violation in a solver result is
  an internal error: the candidate is stored as invalid, the run is flagged, and the event is
  logged at error level.
- The solver's objective value per tier is compared with the evaluator's recomputation; a
  mismatch is logged as a modelling defect.
- Manual edits, rebases and repairs are validated by the same evaluator.

## Consequences

- Two implementations of each rule must be kept in step; property-based tests generate random
  instances and assignments and compare them.
