# Release-verification record — 2026-08-13

> ## ⚠️ This is not the state page
>
> **`docs/dashboard.md` is where project state lives** — phase, progress, next task, requirement
> status, open questions. This file records **what was measured at the release freeze, and when**.
>
> `CLAUDE.md` forbade a `PROJECT_STATUS.md` until 2026-08-13, for a good reason: two files claiming to
> be the state page is how a project acquires two answers to one question. The exception is documented
> in `CLAUDE.md` on one condition, repeated here: **if this file ever starts answering "what phase are
> we in?", it has become the second state page that rule exists to prevent, and that content should be
> cut out of it.**

---

## 1 · What this release is

The **V2 interface**, accepted by the project owner on 2026-08-13, over the backend delivered through
Phase 13. Two design passes: V1 built the information architecture, V2 rebuilt typography, tables and
surfaces after a screenshot review found the first pass still read as an internal tool.

**No solver, scoring, business rule or API contract was changed by either pass.**

---

## 2 · Verified at the freeze

Everything in this section was run on **2026-08-13** and the figure is the output, not a recollection.

| Check | Command | Result |
|---|---|---|
| Frontend tests | `npm run test` | **196 / 196 passed** |
| Frontend typecheck | `npm run typecheck` | clean |
| Frontend build | `npm run build` | clean — CSS 58.6 kB / **10.8 kB gzip**, JS 305.2 kB / **93.3 kB gzip** |
| Backend collected | `pytest --collect-only -q` | **782 tests** |
| Backend fast suite | `pytest -m "not solver and not database"` | **633 passed**, 149 deselected, 59 s |
| Backend database suite | `pytest -m database` (Docker up) | **74 passed**, 19 s — real PostgreSQL 17, includes 2 migration tests |
| Acceptance collected | `pytest tests/acceptance --collect-only -q` | **245 tests** over 23 requirements + the student surface |

⚠️ **The solver-marked tests were not run at the freeze.** They are the remaining ~75 of the 782 and
take minutes each; the last full sweep was `scripts/run-acceptance.ps1` on 2026-08-12 — **245 passed in
23 min 49 s**. Nothing in the V2 pass touched a backend source file that a solver test covers, but that
is an argument, not a measurement.

⚠️ The database suite **skipped silently** on the first attempt because Docker Desktop was not running —
`74 skipped`, exit code 0. A skipped suite reporting success is exactly the trap `CLAUDE.md` warns
about; start `docker compose up -d` and confirm the count before believing a green run.
| Secret scan | `git grep` for key patterns, tracked **and** untracked | **0 hits** |
| `.env` tracked? | `git ls-files --error-unmatch` | **not tracked**, both root and `backend/` |
| API surface | `GET /api/openapi.json` | **33 endpoints** |

### Measured in the running application

| Property | Measurement |
|---|---|
| **Contrast** | **0 failures** across **545 text nodes** on 7 routes, foreground composited against the real painted backdrop |
| **Time-axis overflow** | **0 of 5** labels overflow (79 px of ink in a 99 px box); every axis cell abuts its row's first cell at **exactly 0 px** |
| **Responsive** | 454 / 1280 / 1920 — no page overflow on any route; wide tables scroll inside their own container; page-bar action in view |
| **Focus** | `:focus-visible` paints a 2 px ring at 2 px offset; no focusable element clipped by an `overflow: hidden` ancestor |
| **Generation, end to end** | run `7a350473a2bb` — 122.6 s wall, 43.30 deterministic, 2 candidates (80.87 / 79.60), 5 of 5 data checks pass |
| **Ledger identity** | `Σ contributions = Δ score` exactly, at 3 decimals, on real data |
| **AI, live** | `generated: true`, `fallbackReason: null`, **1.05 s**, figures matching the context |
| **Roles** | All four sign in; each lands on its own screen; a teacher on Compare is refused regeneration politely rather than by a 403 |

---

## 3 · Two defects found and fixed at the freeze

### 3.1 · The test suite was not hermetic — **FIXED**

Switching the language service on for a demonstration turned **five acceptance tests red**
(`test_fr22` ×3, `test_fr24`, `test_fr25`). All five assert the *degraded* path — "with the service off,
an explanation is still returned" — and were obtaining that state from the developer's `backend/.env`
rather than establishing it. **The suite was passing for a reason it did not control.**

Fixed in `backend/tests/conftest.py` by forcing `OPTIEDT_ASSISTANT_ENABLED=false` for every test, beside
the identical precedent for `OPTIEDT_PERSISTENCE`. Verified both ways: 28 pass with the flag on in
`.env` where 5 failed, and the full fast suite is back to 633.

This is a strengthening, not a weakening: no test wants the service on — the ones exercising a working
provider inject a stub adapter — and it is now also structurally impossible for a test to reach a real
provider by accident, which is the property C-21 depends on.

### 3.2 · `*.tsbuildinfo` was not ignored — **FIXED**

`frontend/tsconfig.tsbuildinfo` was untracked but not ignored, so it would have been committed. It is
machine-local, changes on every build, and carries absolute paths. Added to `.gitignore`.

---

## 4 · Known issues

| | Severity | Detail |
|---|---|---|
| **CSV opens unparsed in some Excel installations** | Medium | The export uses `;`, correct for a French/European locale and wrong for one expecting `,`. Observed by the project owner. **Not changed** — it is a data-contract change with 22 tests behind it. The low-risk fix is a UTF-8 BOM plus a `sep=,` first line, which satisfies Excel without changing the delimiter |
| **CORS is hard-coded to `http://localhost:5173`** | Blocks deployment | `api/main.py`. Must accept the deployed origin, ideally from an environment variable |
| **No pixel-level visual QA** | Medium | The Browser pane never composited in any session, so `screenshot` was unavailable throughout. All visual verification is geometry, computed style and contrast — **measured, not looked at.** The V2 design was driven by screenshots the project owner supplied |
| **Print output not read on paper since the rules were rewritten** | Medium | The V2 print stylesheet is new and unverified against an actual print |
| **Examination runs are in memory** | By design | `InMemoryExamRunStore` — they do not survive a restart. No requirement asks for an examination run record |
| **The shortened-day shift is configured but not displayed** | Recorded | Phase 11's limitation. A department setting a Ramadan window and printing a timetable still sees 08:30 |
| **A slot whose index survives while its meaning changes is undetectable** | Recorded | Phase 12, C-22 |
| **`GET /runs/{id}` admits all three timetable roles** | Known property | A signed-in teacher can read any run's drafts. Recorded at Phase 9's audit; worth a decision before real users |
| **No screen-reader pass** | Open | Structural accessibility is in place; nobody has driven it with a screen reader |

---

## 5 · Development artefacts in the local database

The local demonstration database holds several runs created while testing, including
**`36e6d0ce2496`** and **`7a350473a2bb`**.

⚠️ **They are being left in place, and that is the correct answer rather than a shortcut.**

There is **no product-supported way to delete a run.** Verified against the live OpenAPI schema: the
only `DELETE` endpoints are `/api/calendar`, `/api/accounts/{username}` and `/api/dataset`. That is not
an omission — invariant 6 makes a candidate immutable once recorded, and a run record is the provenance
a publication points back at (FR-19). Removing one would mean raw SQL against tables the application
treats as an audit trail.

They live only in the local development database, are visible to the officer role only, and a fresh
deployment starts with none. **If a clean demonstration database is wanted, recreate it** —
`docker compose down -v && docker compose up -d && alembic upgrade head && seed` — rather than deleting
rows.

The four seeded accounts on this machine share the local demonstration password. ⚠️ It exists as a
database row only; it appears in no tracked file (verified) and must not travel to a deployment.

---

## 6 · Documentation written at the freeze

| File | For |
|---|---|
| `CLAUDE.md` | Extended, not replaced — added the frontend baseline, screens, data flow, environment table, deployment status |
| `docs/PROJECT_STATUS.md` | This file |
| `docs/DESIGN_SYSTEM.md` | What the V2 system is |
| `docs/UX_DECISIONS.md` | **Why** — several entries name a defect a plausible "improvement" would reintroduce |
| `docs/API_OVERVIEW.md` | 33 endpoints, read from the live schema |
| `docs/AI_BEHAVIOR.md` | Grounding, fallback, and what the AI must never claim |
| `docs/TESTING.md` | Commands and the coverage map |
| `docs/deployment.md` | Rewritten, including the Vercel assessment |
| `docs/RELEASE_CHECKLIST.md` | Ticked only where there is evidence |
| `docs/supervisor/INTERFACE_WALKTHROUGH.md` | A non-technical guide for the supervisor |
| `docs/supervisor/guide.html` → `OptiEDT_Supervisor_Interface_Guide.pdf` | The same guide typeset — **7 pages**, rendered by headless Chrome |

**On the PDF.** ⚠️ **Nine screenshot areas are marked, not filled.** No screenshot was captured because
the Browser pane never composited in any session, and each placeholder names the screen, the route and
the window size so the images can be dropped in without rewriting the text. **Nothing was simulated or
illustrated** — a picture that does not exactly match the product is worse than a gap that says so.

⚠️ Two rendering findings, both recorded in `guide.html` itself: this Chrome build **declines the
variable IBM Plex Sans woff2** and falls back to Segoe UI for prose (Plex Mono, which carries the
codes, embeds correctly); and an earlier revision pasted a regex containing `*/` into a CSS comment,
which closed it early and silently dropped **both** faces. **Verify the embedded font list after any
re-render — the file size did not change between a working and a broken font, so it proves nothing.**

⚠️ `ARCHITECTURE.md` and `DEPLOYMENT.md` were **not** created: the filesystem is case-insensitive and
they would have silently overwritten the existing `docs/architecture.md` and `docs/deployment.md`. The
lowercase files remain authoritative.

---

## 7 · Deployment

**⚠️ NOT DEPLOYED. Nothing has been deployed anywhere.** `docs/deployment.md` is a plan that has never
been executed.

**Vercel:** the frontend can go there. **The backend cannot** — a solve runs for minutes in an
in-process background thread after the response has already been sent, and examination state lives in
process memory. `deployment.md` §1–2 gives the evidence and the recommended shape.

---

## 8 · What remains before a real deployment

1. Make the **CORS origin** configurable and set it to the deployed frontend.
2. Provision PostgreSQL, run `alembic upgrade head`, set `OPTIEDT_ENVIRONMENT=production` with a real
   `OPTIEDT_SECRET_KEY`.
3. Choose a **persistent backend host** and confirm a full generation completes on it — that single
   test decides whether the host is suitable.
4. Seed accounts with `OPTIEDT_SEED_PASSWORD`, or create them through the Administration screen.
5. Run `scripts/run-acceptance.ps1` once against the deployed instance (16–26 min).
6. Print one timetable and read the sheet.
7. Decide the CSV delimiter question.

⚠️ **What phase comes next, and whether one opens at all, is the project owner's decision and lives in
`docs/dashboard.md`. It is deliberately not answered here.**
