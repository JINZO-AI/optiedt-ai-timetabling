# ADR 0006 — Tiered lexicographic objectives; no composite score

**Status:** Accepted

## Context

Soft objectives are measured in different units (idle periods, preference violations, seats
wasted). A weighted sum forces users to choose weights whose effect they cannot predict, and
a normalised score out of 100 hides the trade-offs it encodes.

## Decision

- Every soft objective and every soft rule belongs to a **priority tier** (1 = most important)
  and carries a positive integer weight within its tier.
- The solver optimizes tier by tier: minimize tier 1; constrain tier 1 to the best value
  found; hint the incumbent; minimize tier 2; and so on. Tier 0 is reserved for the number of
  unscheduled sessions.
- Results are reported per objective in natural units, never as one number. Candidates are
  ordered by their tier-penalty vectors, and Pareto dominance between candidates is shown.
- Objective **profiles** (e.g. Balanced, Student-centred, Instructor-centred, Room-efficient) are
  named tier assignments; a run can produce one candidate per selected profile.

## Consequences

- The time budget is divided between tiers; a tier not proven optimal is constrained to its
  best found value, which the run report states.
- Weights inside a tier are still a weighted sum, but only between objectives the user
  placed at the same importance.
