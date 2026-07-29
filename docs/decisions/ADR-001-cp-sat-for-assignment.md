# ADR-001 — CP-SAT for session assignment

**Status:** Accepted
**Date:** 2026-07-24 (specification phase)

## Context

A timetable containing a conflict cannot be published, whatever its other qualities. The method that
assigns sessions to slots and rooms must therefore never be able to return one.

University course timetabling contains graph colouring as a special case, so no algorithm is known that
solves every instance quickly. A practical consequence follows and shapes the whole project: **no
honest bound on solving time can be announced in advance.**

Four criteria were fixed *before* comparing approaches, so the decision would not rest on an impression:
guarantee of validity, detection of impossibility, data required, and effort of implementation within
four weeks.

## Decision

**Constraint programming, implemented with the CP-SAT solver of OR-Tools.**

It is the only one of the four approaches satisfying all four criteria. Validity is guaranteed by
construction — the solver never produces an assignment violating a rule it was given. It can establish
that no solution exists rather than searching indefinitely. It accepts a time limit and returns the best
result found when the limit is reached.

CP-SAT specifically: free, maintained, Python interface callable directly by the server, and
constructions suited to scheduling — in particular non-overlap on intervals.

## Consequences

- **Rules are written close to the way the department states them**, which makes the model readable and
  correctable — the phase carrying the most uncertainty gets the most legible representation.
- **Model quality determines search speed.** A badly formulated constraint does not give a wrong result;
  it can make the search far slower. Five of twenty days are budgeted to writing the model for this reason.
- **The infeasibility mechanism has three properties that shape the architecture**, and ignoring them
  would have produced a defect discovered late: solving under assumptions admits no parallelism (one
  worker); an objective empties the mechanism of usefulness (the diagnosis run drops it); and the returned
  subset is reduced but **not guaranteed minimal** — it must be presented as *sufficient* to explain the
  conflict, never as the smallest such set.
- Hence the three-stage pipeline: arithmetic pre-analysis, optimisation run, diagnosis run.
- Constraint programming is itself artificial intelligence in the accepted sense — the symbolic branch,
  constraint satisfaction problems. The project uses AI at two levels, of two kinds, and names them
  separately rather than using one word for both.

## Alternatives considered

**Metaheuristics** (genetic algorithms, simulated annealing, tabu search) — frequently used and
relatively simple to program. **Rejected**: nothing guarantees the final timetable contains no conflict,
and when the algorithm finds nothing there is no way to distinguish a problem with no solution from a
search that was too short. For an application a department will rely on, that uncertainty is
disqualifying.

**Integer linear programming** — satisfies the first two criteria, and published work on
curriculum-based timetabling shows it produces optimal solutions and useful lower bounds. **Not
retained** (not rejected as incorrect): expressing non-overlap requires auxiliary variables and large
constants, the model grows heavier with the session count, and the promotion-to-subgroup hierarchy
constraints are less direct to write.

**Learning-based approaches** — would require a large set of validated timetables to learn from. No such
set exists for Tunisian faculties, which alone eliminates the approach here. A trained model also offers
no guarantee its output respects the rules, which reintroduces the metaheuristics problem.

## References

Project Plan and Methodology §4.1–4.5 · Cahier des Charges §7.2
