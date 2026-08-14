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
   the thread is stopped wherever it had reached — and ⚠️ **nothing ever recovers a run left part-way**:
   there is no startup reaper and no timeout sweep, so the row keeps whatever state it had and the
   interface polls it forever. §2 A4 has the detail.
3. **Some state lives only in the process.** Weekly runs *are* persisted (`persistence` defaults to
   `database`), but `InMemoryExamRunStore` is the only examination store — those runs do not survive a
   restart, let alone a new invocation on a different instance.

Two further frictions worth knowing: the **single-worker pool is deliberate** (each solve already uses
every core, so two concurrent solves oversubscribe the machine — ADR-005), and **OR-Tools is ~81 MB
installed**, which is close to or over the bundle limits of several function platforms.

> Forcing this into serverless means rewriting the run lifecycle, and the run lifecycle is what
> ADR-005 decided. **Do not migrate the framework to suit a host.**

### CPU and memory

CP-SAT uses every core it is given. `OPTIEDT_SOLVER_WORKERS=0` means "all available"; cap it on a
shared host (`4` is what the demonstration machine used). Give the backend **at least 2 vCPU and 2 GB**.

---

## 2 · Vercel — the two options, reassessed 2026-08-13

Reassessed against the code rather than against a general belief about
serverless. Every claim below names the file it comes from.

### Option A — frontend *and* backend on Vercel: **UNSAFE**

FastAPI runs on Vercel; that is not the question. The question is whether *this*
backend's generation lifecycle survives there, and four findings say it does not.
Three are silent failures — the application would look like it works.

**A1 · `InMemoryExamRunStore` breaks outright, and this one is a correctness bug.**
`services/examinations.py` holds examination runs in a process dictionary — it is
the only implementation, and its own docstring says so. `POST /api/examinations`
returns an id; a following `GET /api/examinations/{id}` that lands on a different
instance returns **404 for a session that was generated successfully**. No
timeout, no error, just a result that has vanished.

**A2 · The background work races the response.** `POST /runs` returns 202 and
hands the solve to `RunExecutor.submit`, a `ThreadPoolExecutor(max_workers=1)` in
`tasks/executor.py`. The handler returns before the work starts. A serverless
instance is suspended once it responds, so the thread is frozen mid-solve. The
code registers nothing with a keep-alive primitive and could not without changing
the run lifecycle — which is what ADR-005 decided.

**A3 · "One solve at a time" silently stops holding.** `get_executor()` in
`api/deps.py` is `@lru_cache(maxsize=1)` — **one executor per process**. Across
several instances there are several single-worker pools, so two runs proceed at
once. That guarantee is not tidiness: `solver_workers=0` means each solve takes
every core, and overlapping two was measured to stall unrelated work for minutes.

**A4 · A recycled instance strands a run forever.** Run state *is* persisted —
`persistence` defaults to `database`, and the executor saves at every transition —
but **nothing ever recovers a run left in `SOLVING`.** Verified: no startup
reaper, no timeout sweep, no state repair anywhere in `api/main.py` or
`services/runs.py`. The row stays `SOLVING`, the interface polls it forever. On a
persistent host that needs a crash; on serverless, instance recycling is routine.

Two further frictions, neither decisive on its own: **OR-Tools is 81 MB
installed**, which is close to the package limits of several function platforms;
and a solve measured **122–150 s** on 4 dedicated workers, so on the smaller
shared vCPU allocation of a function it would run considerably longer against
whatever the platform's ceiling is.

> ⚠️ **What would make Option A viable is an architectural decision, not a
> configuration change**, and it is deliberately NOT implemented here: move
> examination runs into the database, replace the in-process executor with an
> external queue and worker, and add recovery for runs stranded in `SOLVING`.
> That is ADR-005 reversed. It belongs to the project owner, and it should be a
> new ADR rather than a quiet refactor.

### Option B — frontend on Vercel, backend on a persistent host: **SAFE**

Nothing in the repository stands in the way, and the one thing that did has been
fixed. Three properties make it work:

- **Product code writes nothing to disk.** Verified by search across
  `backend/src/optiedt/` — no `open(…, "w")`, no `write_text`, no `mkdir`, no
  `shutil.copy`. `data/instance/` is read-only at runtime by design, and a
  supplied dataset goes to the `department_dataset` table. So an ephemeral or
  read-only filesystem changes nothing.
- **The API is stateless per request apart from the two in-process caches above**,
  and a single persistent instance keeps both correct.
- **The frontend needs no configuration.** `src/api/client.ts` calls `/api` as a
  relative path.

**Two changes, one of which is already done:**

1. ✅ **CORS is now configurable** — `OPTIEDT_CORS_ALLOWED_ORIGINS`, comma-separated,
   defaulting to the Vite dev server. Verified with real preflight requests: a
   configured origin gets `200` with the matching `access-control-allow-origin`,
   localhost still works, and an unconfigured origin gets `400`.
2. **Add a Vercel rewrite** so the SPA and the API share an origin:

```json
// vercel.json — not in the repository; create it when Option B is executed
{
  "rewrites": [{ "source": "/api/:path*", "destination": "https://YOUR-BACKEND-HOST/api/:path*" }]
}
```

⚠️ **Prefer the rewrite over setting a cross-origin API base.** It keeps every
request same-origin, leaves `client.ts` untouched, and means the CORS setting is
never consulted at all — one fewer thing to get wrong at 2 a.m.

⚠️ **Run one full generation on the chosen host before believing it.** That single
test distinguishes a persistent host from a request-scoped one, and it is the only
test that does.

### ⚠️ One gap Option B does not close

**A backend restart during a solve still strands that run in `SOLVING`** (A4). It
is far rarer on a persistent host — a deploy or a crash rather than routine
recycling — but the failure is the same and there is no recovery. Until there is,
the operational answer is to notice and re-run. Worth an ADR before real users.

## 3 · Environment variables

Names only. ⚠️ **Never write a value into a tracked file.** The full table with descriptions is in
`.env.example` at the repository root.

**Required in production:** `OPTIEDT_DATABASE_URL`, `OPTIEDT_ENVIRONMENT=production`,
`OPTIEDT_SECRET_KEY`.

⚠️ **Start-up REFUSES the published default secret key when `OPTIEDT_ENVIRONMENT=production`**
(`Settings.require_deployable`, pinned by `unit/test_config_guard.py`). That guard is the only thing
standing between a deployment and forgeable tokens, because the default key is published in this
repository.

**Required if the SPA and the API are on different origins:** `OPTIEDT_CORS_ALLOWED_ORIGINS` —
comma-separated, no trailing-comma fuss, defaulting to the Vite dev server. ⚠️ Not consulted at all
behind a same-origin `/api/*` rewrite, which is the arrangement §2 recommends.

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
- [ ] `OPTIEDT_CORS_ALLOWED_ORIGINS` set to the deployed frontend origin — **or** a same-origin
      `/api/*` rewrite in place, in which case it is not needed at all
- [ ] `/api/*` reaching the backend from the SPA's origin
- [ ] `OPTIEDT_SOLVER_WORKERS` sized to the host
- [ ] The assistant key set only if written answers are wanted
- [ ] ⚠️ **`GET /runs/{id}` admits any of the three roles that work on timetables** — a signed-in
      teacher can read any run's drafts. A known property recorded at Phase 9's audit, not a
      regression, and worth a decision before the application faces real users.
