# Release checklist

**Independently re-verified 2026-08-13.** Nothing here is ticked because a previous session said so —
every `[✓]` was re-run in this session and the evidence is on the line. Where a claim could not be
re-established it was **downgraded**, not carried forward.

```
[✓] VERIFIED      re-run in this session, evidence on the line
[ ] NOT VERIFIED  not done, or not attempted
[!] BLOCKED       cannot be done yet; the reason is stated
```

---

## Repository and secrets

- [✓] **No secrets tracked** — `git grep` for `gsk_*`, `sk-*`, `AKIA*`, `ghp_*`, private-key headers and
      `password|secret|api_key|token = "…"` across tracked **and** untracked files: **0 hits**
- [✓] **`.env` untracked** — root and `backend/`, both confirmed by `git ls-files --error-unmatch`
- [✓] **Build artefacts ignored** — `*.tsbuildinfo`, `dist/`, `node_modules/`
- [✓] **The demo password appears in no file** — it exists only as a database row
- [✓] **Branch and remote** — `main` → `github.com/JINZO-AI/optiedt-ai-timetabling`, clean, in sync

## Static checks

- [✓] **mypy strict** — no issues in **92** source files
- [✓] **ruff** — all checks passed; **165** files formatted
- [✓] **Import contracts** — **13 kept, 0 broken**
- [✓] **Frontend typecheck** — clean
- [✓] **Frontend production build** — clean; CSS 58.6 kB / **10.8 kB gzip**, JS 305.2 kB / **93.3 kB gzip**

## Tests

- [✓] **Frontend** — **196 / 196** passed, 21 files
- [✓] **Backend fast** — **638 passed**, 149 deselected (was 633; +5 new CORS tests)
- [✓] **Backend database** — **74 passed** against real PostgreSQL 17 with Docker confirmed up
- [✓] **Backend solver-marked** — **75 passed** in 21 min 23 s
- [✓] **THE WHOLE BACKEND SUITE RAN, WITH NOTHING SKIPPED** — 787 collected, and the three tiers
      partition it exactly: 638 + 74 + 75 = 787, with each tier's passed + deselected also 787. That
      arithmetic is the proof every test ran **exactly once**; a tier that silently skipped would not
      add up
- [ ] **`scripts/run-acceptance.ps1`** — full sweep 16–26 min. Last complete run 2026-08-12, 245 passed
- [✓] **New guard verified to fire** — reverting `api/main.py` to the hard-coded origin list fails
      `test_the_middleware_is_installed_with_the_configured_origins`, as this project requires of a guard

⚠️ **A skipped test is not a passed test.** The database suite reported `74 skipped` and exit code 0
when Docker was not running. Start `docker compose up -d` and check the count, not the exit code.

## Application behaviour — exercised through the API in this session

- [✓] **Authentication** — all four roles obtain a token; wrong password `401`; no token `401`
- [✓] **Role permissions — 8 / 8** — student refused `/runs` (403) and given `/me/timetable` (200);
      teacher refused `POST /runs` (403) and `/accounts` (403); admin refused `/dataset` (403)
- [✓] **Runs and candidates** — 7 runs, 6 comparable; run detail `COMPLETED`, 2 candidates
- [✓] **Pre-analysis** — 5 checks present, 5 passed
- [✓] **Comparison** — `Σ contributions` matches `Δ score` to **1e-9** on real data
- [✓] **Dominance · recommendation · publications · availability · instance** — all `200`
- [✓] **AI** — `generated: true`, `fallbackReason: null`, grounded answer against a live provider
- [ ] **Timetable generation, start to finish** — not re-run in this session; a full solve was driven
      end to end on 2026-08-12 (run `7a350473a2bb`, 122.6 s, 2 candidates)
- [ ] **Examination generation** — 0 examination runs exist on this machine; not exercised here
- [ ] **Publishing a candidate** — the existing publication was created in an earlier session
- [ ] **CSV export opened in a spreadsheet** — see the known issue in `PROJECT_STATUS.md`
- [ ] **Print output produced and read on paper** — the V2 print rules have never been printed

## Database

- [✓] **Connectivity** — PostgreSQL 17 container healthy; 74 database tests pass against it
- [✓] **Migrations** — `alembic current` = `1e28bf61664e (head)`; **exactly one head**; 6 migrations,
      linear history
- [ ] **Production database provisioned and migrated**

## Quality gates

- [✓] **Contrast** — 0 failures across 545 text nodes on 7 routes, composited against real backdrops
- [✓] **Responsive** — 454 / 1280 / 1920: no page overflow; wide tables scroll inside their container
- [✓] **Focus visible** — 2 px ring at 2 px offset; no focusable element clipped
- [✓] **Reduced motion** — every keyframe guarded; duration tokens collapse to zero
- [!] **Pixel-level visual QA** — **BLOCKED. The Browser pane has never composited in any session, so
      screenshots are unavailable.** Everything above is geometry and computed style: measured, not
      looked at. This cannot be closed by this environment
- [ ] **Screen-reader pass** — never attempted

## Deployment

- [✓] **CORS is configurable** — `OPTIEDT_CORS_ALLOWED_ORIGINS`. Proven with live preflights: a
      configured origin `200` + matching header, localhost still `200`, unconfigured origin `400`
- [✓] **Frontend needs no build-time API URL** — `client.ts` calls `/api` relatively; a rewrite is
      enough, and avoids CORS entirely
- [✓] **No filesystem writes in product code** — verified by search; an ephemeral or read-only
      filesystem changes nothing
- [✓] **Vercel assessed against this code** — Option A **unsafe** (four findings), Option B **safe**.
      `deployment.md` §2
- [ ] **Production environment variables configured**
- [ ] **`OPTIEDT_ENVIRONMENT=production` with a real `OPTIEDT_SECRET_KEY`**
- [ ] **A persistent backend host chosen**
- [ ] **One full generation completed on that host** — the single test that decides whether a host is
      suitable
- [ ] **`/api/*` reaching the backend from the SPA's origin**
- [ ] **Health check wired** (`GET /api/health`)
- [ ] **Production deployment tested**
- [ ] **Fresh-browser test on the deployed URL**
- [ ] **Supervisor test account prepared on the deployed instance**

⚠️ **Nothing has been deployed.** `deployment.md` is a plan that has never been executed.

## Known gaps carried forward, not fixed

- [!] **A restart during a solve strands that run in `SOLVING`** — there is no startup reaper and no
      timeout sweep. Rare on a persistent host, routine on serverless. Fixing it is an architectural
      decision (`deployment.md` §2 A4) and belongs to the project owner
- [!] **Examination runs live in process memory** — by design; no requirement asks for a record
- [ ] **CSV uses `;`** — correct for a French locale, unparsed in an Excel expecting `,`. Not changed:
      22 tests pin the format
- [ ] **The shortened-day shift is configured but not shown** in the timetable views (Phase 11)
- [ ] **`GET /runs/{id}` admits all three timetable roles** — a teacher can read any run's drafts

## Before the supervisor sees it

- [✓] **Walkthrough written** — `docs/supervisor/INTERFACE_WALKTHROUGH.md`
- [✓] **PDF produced** — 7 pages, `OptiEDT_Supervisor_Interface_Guide.pdf`
- [!] **Screenshots in the PDF** — **BLOCKED for the same reason as pixel QA.** Nine areas are marked
      with the screen, route and window size to capture. Nothing was simulated
- [ ] **Demonstration rehearsed** — `docs/demonstration.md` is the script
