# Frontend

React + TypeScript + Vite. One feature directory per screen of SRS §4.1.

```bash
npm install
npm run dev
```

## Screens

| Directory | Screen | Requirements |
|---|---|---|
| `features/availability/` | Weekly grid — each slot marked available, unavailable or preferred | FR-2 |
| `features/generation/` | Pre-analysis report, weight profiles, time budget, launch, run state, candidates as they appear | FR-3, FR-12, FR-13 |
| `features/comparison/` | Two candidates side by side, criteria table, contributions, dominance, attached recommendations | FR-14, FR-15, FR-16, FR-17, FR-23 |
| `features/timetable/` | Weekly grid filtered by teacher, group, classroom or laboratory; printing | FR-7, FR-10, FR-18 |
| `features/conflicts/` | Rules named by the data checks and the diagnosis run, each with its code and statement | FR-8 |
| `features/assistant/` | Free-text question on the current run, explanation, report | FR-22, FR-24, FR-25 |
| `features/admin/` | Accounts, holidays, closed half-days, shortened-day window | FR-9, FR-11 |

## Four things the interface must get right

**Runs are asynchronous.** Launching returns a run id immediately; the client
polls `GET /runs/{id}`. Candidates appear as they are produced, not when the
whole portfolio finishes — the first profile may complete in seconds while the
third takes minutes.

**Contributions are shown, never summarised.** The sum of the displayed
contributions equals the difference between the two scores, exactly. That
identity *is* the explanation — a user who adds up the column must get the
number at the bottom. Rounding for display is fine; hiding a term is not.

**The conflict report says "sufficient", not "minimal".** The subset returned by
the diagnosis run is heuristically reduced and is **not** guaranteed to be the
smallest set. Wording that implies otherwise is a defect.

**A suggestion that is not an action carries no button.** The assistant's
suggestions are matched against the three-action catalogue. One that matches
nothing is shown as a **remark**, with no control to act on it (ADR-007).

## Degraded mode

The assistant is optional and off by default. With it disabled, every screen
except the assistant panel must work unchanged, and explanations fall back to
their computed form. This is an acceptance test (FR-22, FR-25), not a nicety.

## Time limits are estimates

The budget the user sets is **deterministic time**, not wall-clock seconds
(ADR-011). Show it as an estimate and show elapsed time separately. Do not
promise wall-clock precision the solver does not offer.
