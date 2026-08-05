# Frontend

React + TypeScript + Vite. One feature directory per screen of SRS §4.1.

```bash
npm install
npm run dev        # needs the API on :8000 — vite.config.ts proxies /api
npm run typecheck
npm run test
```

`scripts/run-checks.ps1` runs `typecheck` and `test` from the repository root.

## Screens

⚠️ **Read the State column before believing a row.** **Nine** directories are listed; **seven carry a
screen** and the other two hold a `.gitkeep`.

⚠️ *Both numbers were wrong until 2026-08-05 — the line said seven listed and six with a screen. The
Phase 5 audit corrected this row once already, from "four", and corrected it to a figure that was also
wrong. **Derive it rather than editing it:** `Get-ChildItem src/features -Directory` for the first, and
the count of non-test `.tsx` files under them for the second.*

| Directory | Screen | Requirements | State |
|---|---|---|---|
| `features/auth/` | Sign in. No registration — accounts come from the seed command (C-18) | FR-11 | ✅ Phase 5 M4 |
| `features/availability/` | Weekly grid, each open slot available **or unavailable**. A teacher edits **their own**, taken from the token | FR-2, FR-11 | ✅ Phase 4, scoped in M4 |
| `features/generation/` | Weight profiles, deterministic budget, launch, run state, candidates with sub-scores, the pre-analysis report, publish | FR-13, FR-5, FR-6, FR-12 | ✅ Phase 4, extended M1 and M5 |
| `features/timetable/` | Weekly grid by teacher, group or room, plus room occupancy | FR-7, FR-18 | ✅ Phase 4 |
| `features/comparison/` | Two candidates side by side, criteria table, contributions, **dominance** | FR-14, FR-15, FR-17 | ✅ Phase 4, dominance added Phase 6 M1 |
| `features/conflicts/` | Rules named by the diagnosis run, and what an empty set means | FR-8 | ✅ Phase 5 M2 |
| `features/publication/` | Published timetables with the trace back to run, seed and weights | FR-19 | ✅ Phase 5 M5 |
| `features/admin/` | Holidays, closed half-days, shortened-day window, **account management** | FR-9 | ⬜ not built. ⚠️ FR-11's *authentication* is done; the administrator's **account management** from SRS Table 2 is not, and C-18 records why |
| `features/assistant/` | Free-text question on the current run, explanation, report | FR-22, FR-24, FR-25 | ⬜ unscheduled (C-1) |

⚠️ **What the navigation hides is not what is forbidden.** `App.tsx` offers Génération and
Publications only to the person in charge, but every endpoint checks the role for itself — a client
that hides a control has not prevented the request. If the shell and the API disagree, the API is
right.

**Not built, and deliberately so:**

- ~~**No dominance signal** on the comparison screen (FR-17).~~ **Built in Phase 6 M1**, once C-14 was
  resolved. It reports dominance **portfolio-wide**, never at the top rank: the "dominated top
  candidate" indicator both specification documents asked for is *provably unreachable* — a dominated
  candidate cannot outscore its dominator — so it was the *specification wording* that was corrected,
  not the control that was built. `DominanceNotice.tsx`, eight display tests.
- **No preferred state** in the availability grid. `teacher_availability.csv` carries a boolean, so a
  third cell would collect an answer with nowhere to record it (C-12(a), decided 2026-08-01).
- **No printing or export** (FR-10), and **no regeneration from a recommendation** (FR-23).

## What the interface must get right

**Runs are asynchronous.** Launching returns a run id immediately; the client polls `GET /runs/{id}`.

⚠️ **Candidates do NOT appear as they are produced.** `services/portfolio.py` returns the whole
portfolio at the end, so the screen shows `SOLVING` for the full 105–150 s and every candidate arrives
at once. `docs/architecture.md` and ADR-005 describe incremental reporting as the intent; it is not
implemented, and both now say so. Do not write copy that promises it.

**The interface computes no score and decides no ranking.** Rank order is the array order the API
returns and every figure arrives already computed — `docs/architecture.md` lets this layer "display,
filter, print, ask" and forbids it to "compute a score, decide an order". Arranging for display is
fine: grid axes, rooms alphabetically, and the largest-remainder rounding that makes a contributions
column add up.

**Contributions are shown, never summarised.** The sum of the displayed contributions equals the
difference between the two scores, exactly. That identity *is* the explanation — a user who adds up the
column must get the number at the bottom, so the comparison screen uses one precision throughout.
Rounding for display is fine; hiding a term is not.

**The conflict report will say "sufficient", not "minimal".** The subset returned by the diagnosis run
is heuristically reduced and is **not** guaranteed smallest. Wording that implies otherwise is a defect.

**A suggestion that is not an action carries no button.** The assistant's suggestions are matched
against the three-action catalogue; one that matches nothing is shown as a **remark**, with no control
to act on it (ADR-007).

## Degraded mode

The assistant is optional and off by default. With it disabled, every screen except the assistant panel
must work unchanged, and explanations fall back to their computed form. This is an acceptance test
(FR-22, FR-25), not a nicety. It holds trivially today: no screen consults the assistant.

## Time limits are estimates

The budget the user sets is **deterministic time**, not wall-clock seconds (ADR-011). The generation
screen labels it as such and shows elapsed wall clock separately. Do not promise wall-clock precision
the solver does not offer.

⚠️ **There is no authentication yet** (FR-11, Phase 5). Every endpoint is open and the teacher whose
availability is edited is chosen from a dropdown, not from a session. Do not expose this beyond a
development machine.
