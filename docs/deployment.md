# Deployment

> ## ⚠️ Status: NOT DEPLOYED
>
> **Nothing has been deployed anywhere. This document is a plan that has never been executed.** Every
> instruction below is untested against a real host. Do not describe OptiEDT as live, deployed or in
> production. [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) records what is still unticked.

Written from the repository, not from a template. Figures cited are measured — see
[`PROJECT_STATUS.md`](PROJECT_STATUS.md) and `status.md`.

---

## 1 · The shape, and the one constraint that decides it

| Piece | Target | Why |
|---|---|---|
| **Frontend** — React 18 + Vite 5 | **Any static host** (Vercel, Netlify, Cloudflare Pages, nginx) | `vite build` emits `frontend/dist/`, ~305 kB / 93 kB gzipped plus cached font files. No server needed |
| **Backend** — FastAPI + OR-Tools CP-SAT | **A persistent process** — Render, Railway, Fly.io, a VM, or a container anywhere | See below. This is the constraint that decides the whole shape |
| **Database** — PostgreSQL 17 | Managed PostgreSQL (Neon, Supabase, RDS, or the host's own) | Runs, candidates, placements, sub-scores, publications, the calendar, accounts, the dataset |
| **Language service** | The provider already configured | Reached over HTTPS **from the backend only**. The browser never sees the key |

### ⚠️ The backend cannot run on short-lived serverless functions

Three properties of this application are incompatible with a request-scoped function, and all three
are load-bearing rather than incidental. **This is not about a specific timeout number** — raising the
limit does not help, because the work happens *after* the response.

1. **A solve takes minutes.** Measured: the weekly portfolio is **147–150 s** at production settings;
   a budget-30 run measured **122.6 s** on 2026-08-13; an examination session ~32 s.
2. **`POST /runs` answers 202 immediately and the work continues in a background thread.**
   `tasks/executor.py` and `services/examinations.py` each hold a
   `ThreadPoolExecutor(max_workers=1)`. A function instance is frozen or destroyed once it responds, so
   the thread never finishes and the run stays `PENDING` forever.
3. **State lives in the process.** `InMemoryExamRunStore` is the only implementation — examination runs
   do not survive a restart, let alone a new invocation on a different instance.

Two further frictions worth knowing: the **single-worker pool is deliberate** (each solve already uses
every core, so two concurrent solves oversubscribe the machine — ADR-005), and **OR-Tools is ~81 MB
installed**, which is close to or over the bundle limits of several function platforms.

> Forcing this into serverless means rewriting the run lifecycle, and the run lifecycle is what
> ADR-005 decided. **Do not migrate the framework to suit a host.**

### CPU and memory

CP-SAT uses every core it is given. `OPTIEDT_SOLVER_WORKERS=0` means "all available"; cap it on a
shared host (`4` is what the demonstration machine used). Give the backend **at least 2 vCPU and 2 GB**.

---

## 2 · Vercel — the two options, assessed

**Option A — frontend *and* backend on Vercel: NOT VIABLE.** For the three reasons in §1. A Python
function can serve `GET /api/instance` perfectly well, but `POST /runs` would return a run id for work
that never runs, and the examination store would be empty on the next request. The product would appear
to work and then never finish a timetable — the worst possible failure mode.

**Option B — frontend on Vercel, backend on a persistent host, managed PostgreSQL: VIABLE, and
recommended.** Nothing in the repository stands in the way. Two changes are required, both small:

1. **CORS.** `api/main.py` hard-codes `allow_origins=["http://localhost:5173"]`. It must accept the
   deployed frontend origin — ideally from an environment variable rather than another literal.
2. **Routing.** Add a Vercel rewrite from `/api/*` to the backend host. ⚠️ **Prefer a rewrite over a
   base URL**: it keeps requests same-origin, leaves `src/api/client.ts` unchanged, and avoids CORS
   entirely.

```json
// vercel.json — not present in the repository; create it when Option B is executed
{
  "rewrites": [{ "source": "/api/:path*", "destination": "https://YOUR-BACKEND-HOST/api/:path*" }]
}
```

⚠️ Even under Option B, a solve outlives typical proxy timeouts — but that is fine, because **no
request is held open for one.** The client polls. Only make sure the proxy does not buffer or time out
the short `POST` and `GET` calls.

---

## 3 · Environment variables

Names only. ⚠️ **Never write a value into a tracked file.** The full table with descriptions is in
`CLAUDE.md` → "Environment, and how to start the thing".

**Required in production:** `OPTIEDT_DATABASE_URL`, `OPTIEDT_ENVIRONMENT=production`,
`OPTIEDT_SECRET_KEY`.

⚠️ **Start-up REFUSES the published default secret key when `OPTIEDT_ENVIRONMENT=production`**
(`Settings.require_deployable`, pinned by `unit/test_config_guard.py`). That guard is the only thing
standing between a deployment and forgeable tokens, because the default key is published in this
repository.

**Recommended:** `OPTIEDT_SOLVER_WORKERS`, `OPTIEDT_SOLVER_WALL_CLOCK_CEILING_SECONDS`.

**The assistant, optional and off by default:** `OPTIEDT_ASSISTANT_ENABLED`,
`OPTIEDT_ASSISTANT_BASE_URL`, `OPTIEDT_ASSISTANT_API_KEY`, `OPTIEDT_ASSISTANT_MODEL`,
`OPTIEDT_ASSISTANT_TIMEOUT_SECONDS`. Everything works with it off — only prose disappears (invariant 5).

**The frontend takes none.**

---

## 4 · Database

```bash
cd backend && uv run alembic upgrade head
```

The instance CSVs in `data/instance/` are **read-only at runtime** and ship with the application; they
are not database content. A department's own data arrives through FR-1 and is stored in
`department_dataset`.

---

## 5 · Accounts

⚠️ **The seed command generates a random password, prints it once and stores it nowhere**
(`services/seed.py`, `secrets.token_urlsafe(16)`). If that output is not kept, **those accounts cannot
be signed into by anyone** — which is exactly what happened on the demonstration machine.

```bash
OPTIEDT_SEED_PASSWORD=choose-a-password uv run python -m optiedt.services.seed
```

The seed **refuses to run on a populated system** (C-18). On a database that already has accounts, add
one through `POST /api/accounts` as an administrator, or the Administration screen.

⚠️ **The seed is a development and demonstration tool, not a deployment mechanism.**

---

## 6 · Health checks and post-deployment testing

`GET /api/health` → `{"status": "ok"}`. It does **not** check the database — a green health check with
a dead database is possible. Add a database probe if the host's health check is load-bearing.

After deploying, in a **fresh browser** on the deployed URL:

1. Sign in as each of the four roles; confirm each lands on its own screen.
2. Launch a generation and let it finish — this is the one that proves the host can hold a background
   thread for two minutes. **If the run sits at `PENDING` or `SOLVING` forever, the host is
   request-scoped and Option A has been chosen by accident.**
3. Open Compare; confirm `Σ contributions = Δ score`.
4. Publish a candidate; sign in as the student; confirm the published week appears.
5. Print a timetable and read the sheet.
6. If the assistant is on, ask one question and confirm the answer is labelled *Written by the language
   service*.

---

## 7 · Before going live

- [ ] `OPTIEDT_ENVIRONMENT=production` and a real `OPTIEDT_SECRET_KEY`
- [ ] `alembic upgrade head` against the production database
- [ ] CORS origin set to the deployed frontend, not `localhost:5173`
- [ ] `/api/*` reaching the backend from the SPA's origin
- [ ] `OPTIEDT_SOLVER_WORKERS` sized to the host
- [ ] The assistant key set only if written answers are wanted
- [ ] ⚠️ **`GET /runs/{id}` admits any of the three roles that work on timetables** — a signed-in
      teacher can read any run's drafts. A known property recorded at Phase 9's audit, not a
      regression, and worth a decision before the application faces real users.
