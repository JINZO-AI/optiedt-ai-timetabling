# Release checklist

**A box is ticked only when the thing was actually done and the evidence is on the line.** An unticked
box is not a failure — it is work that has not happened yet, and saying so is the point of the file.

Last worked: **2026-08-13** (release freeze).

---

## Repository

- [x] **Repository clean of secrets** — `git grep` for `gsk_*`, `sk-*`, `AKIA*`, `ghp_*`, private-key
      headers and `password|secret|api_key|token = "…"` over tracked *and* untracked files: **0 hits**
- [x] **`.env` not tracked** — `backend/.env` and root `.env` both confirmed untracked; `.gitignore:247`
- [x] **Build artefacts ignored** — `*.tsbuildinfo` added at the freeze; `dist/`, `node_modules/` already
- [x] **Demo password absent from the repository** — it exists only as a database row
- [x] **Branch and remote confirmed** — `main` → `github.com/JINZO-AI/optiedt-ai-timetabling`

## Build and static checks

- [x] **Frontend typecheck** — `npm run typecheck`, clean
- [x] **Frontend tests** — `npm run test`, **196 / 196**
- [x] **Frontend production build** — `npm run build`, clean. CSS ~10.8 kB gzip, JS ~93 kB gzip
- [x] **Backend fast suite** — `pytest -m "not solver and not database"`, **633 passed**
- [x] **Backend database suite** — `pytest -m database`, **74 passed** against real PostgreSQL 17
- [x] **Test suite made hermetic** — five acceptance tests were reading the developer's `.env`; fixed
- [ ] **Backend solver-marked tests** — the remaining ~75 of 782, not run at the freeze
- [ ] **`scripts/run-checks.ps1` green across all steps** — needs `docker compose up -d` first
- [ ] **`scripts/run-acceptance.ps1`** — 16–26 min; last full sweep 2026-08-12, 245 passed

## Application behaviour — verified by driving it

- [x] **Authentication** — all four seeded roles sign in
- [x] **Role permissions** — each role's rail, landing route and refusals checked
- [x] **Generation** — a real run driven end to end: pipeline, vitals, 2 candidates
- [x] **Candidate ranking** — scores, fingerprints, expandable terms
- [x] **Comparison** — head-to-head, ledger, `Σ contributions = Δ score` exact
- [x] **AI** — live provider call, `generated: true`, grounded
- [x] **Timetables** — all three session types render; time axis measured, 0 overflow
- [x] **Availability** — grid renders, unsaved/saved states
- [x] **Examinations** — screen renders; rules named
- [x] **Publishing** — publication list with provenance
- [ ] **CSV export opened in a spreadsheet** — see the known issue in `PROJECT_STATUS.md`
- [ ] **Print output produced and read on paper** — rules rewritten but not printed since

## Quality gates

- [x] **Responsive** — 454 / 768 / 1280 / 1920 measured: no page overflow, grids scroll inside
- [x] **Contrast** — 0 failures across 545 text nodes on 7 routes, composited backdrops
- [x] **Focus visible** — `:focus-visible` ring confirmed, no clipping ancestors
- [x] **Reduced motion** — every keyframe guarded; duration tokens collapse to 0
- [ ] **Screen-reader pass** — never run
- [ ] **Pixel-level visual QA** — the Browser pane never composited; not done by this session

## Deployment

- [ ] **Production environment variables configured**
- [ ] **Production database provisioned and migrated** (`alembic upgrade head`)
- [ ] **`OPTIEDT_ENVIRONMENT=production` with a real `OPTIEDT_SECRET_KEY`**
- [ ] **`/api/*` reaching the backend from the SPA's origin**
- [ ] **CORS origin set to the deployed frontend** — currently hard-coded to `http://localhost:5173`
- [ ] **`OPTIEDT_SOLVER_WORKERS` sized to the host**
- [ ] **Health check wired** (`GET /api/health`)
- [ ] **Production deployment tested**
- [ ] **Fresh-browser test on the deployed URL**
- [ ] **Supervisor test account prepared on the deployed instance**

⚠️ **Nothing has been deployed.** `deployment.md` is a plan that has never been executed.

## Before the supervisor sees it

- [x] **Supervisor walkthrough written** — `docs/supervisor/INTERFACE_WALKTHROUGH.md`
- [ ] **Walkthrough re-read against the running app** after any further UI change
- [ ] **Screenshots captured** for the walkthrough PDF
- [ ] **Demonstration rehearsed** — `docs/demonstration.md` is the script
