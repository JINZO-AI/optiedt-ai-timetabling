# Demonstration

**A script anyone can execute, where every step states its expected result.**

That last clause is the point. A demonstration whose steps say only what to *do* can fail silently —
the presenter improvises around a blank screen and nobody watching knows whether they saw the product
or a recovery. Every step below says what should appear, so **a failed demonstration is visible**.

Two things live here:

- **§1 The demonstration script** — the whole path, twelve steps, about 12 minutes plus one solve.
- **§2 The FR-2 timed walkthrough** — the one acceptance criterion no automated check can replace,
  its protocol, and the table to record the result in.

⚠️ **Read §3 before presenting.** It lists what this demonstration deliberately does *not* show. A
question about the assistant or about regeneration has an honest answer, and improvising one in the
room is how a project acquires a claim it cannot support.

---

## 1 · The demonstration script

### Before the room

| # | Do | Expect |
|---|---|---|
| 0.1 | `docker compose up -d` | `Container optiedt-postgres Started`. ⚠️ Then **confirm which server you reached**: `docker exec optiedt-postgres psql -U optiedt -d optiedt -tAc "select version();"` must print **PostgreSQL 17**. A machine with its own PostgreSQL on 5432 makes `docker compose` succeed while every connection reaches the *other* server — see `README.md` |
| 0.2 | From `backend/`: `uv run alembic upgrade head` | `Running upgrade … 04462f0db630`, no error |
| 0.3 | From `backend/`: `uv run python -m optiedt.services.seed` | `Created 47 accounts: 3 staff + 44 teachers`, then **`PASSWORD (generated, shown once): …`**. **Write it down** — it is shown once and every account shares it. Set `OPTIEDT_SEED_PASSWORD` beforehand to choose it instead |
| 0.4 | From `backend/`: `uv run uvicorn optiedt.api.main:app --reload` | `Uvicorn running on http://127.0.0.1:8000` |
| 0.5 | From `frontend/`: `npm run dev` | `Local: http://localhost:5173` |
| 0.6 | `scripts/run-checks.ps1` | **`All checks passed.`** Nine steps. Run it before the room, not in it |

⚠️ **If step 0.3 refuses** with *"This installation already has accounts"*, the database is already
seeded. That is the command working as designed (C-18) — it will not re-provision a populated system.
Use the password from the first seed, or drop the `users` table.

### The demonstration

#### A teacher declares when they cannot teach — FR-2

| # | Do | Expect |
|---|---|---|
| 1 | Sign in as **`t001`** | The navigation offers **Disponibilités** and **Emplois du temps** — and **no Génération link**. A teacher may not launch a run, and the interface says so by not offering it |
| 2 | Open **Disponibilités** | The whole week on one screen. The teacher field reads **`T001` and is read-only** — which teacher you are comes from the token, never from a dropdown. Saturday afternoon is **not offered at all**: it is closed in configuration |
| 3 | Mark two slots unavailable — say Monday 08:30 and Wednesday 15:40 — and save | The cells change state and the rows come back marked **`TEACHER`**. Existing generated rows are marked **`SYNTHETIC`**, so a declaration a person made is distinguishable from one the generator invented |
| 4 | Try to reach another teacher's grid (`/api/teachers/T002/availability`) | **403**, not an empty grid. A teacher must not be left thinking a colleague declared nothing |

#### The person in charge generates — FR-12, FR-13, FR-5

| # | Do | Expect |
|---|---|---|
| 5 | Sign out; sign in as **`responsable`** | The full navigation appears, including **Génération** and **Publications** |
| 6 | Open **Génération**, leave seed 42 and the default budget, launch | The run appears immediately in **`PENDING`** — the request returns a run id and does not hold the connection open. Solving takes minutes |
| 7 | Watch the **pre-analysis report** while it solves | Five checks, shown as **figures rather than ticks**: Amphi 57.1 %, `Lab_Info` 71.4 % of periods **and 90.9 % of two-period windows**, heaviest teacher load 12 periods (18 h), smallest margin 11 free slots. ⚠️ **Say the 90.9 % out loud.** The period figure is the reassuring one and it is the one that hid an infeasible instance for three sessions (C-13) |
| 8 | Wait for **`COMPLETED`** (measured 147–150 s at budget 90) | **Three distinct candidates**, each with an overall score /100 and all **seven** sub-scores including the zero-weight S10. `0 duplicates removed`. ⚠️ Candidates arrive **all at once** at the end, not as they are produced — a known, recorded limitation |

#### Two candidates, compared term by term — FR-14, FR-15, FR-17

| # | Do | Expect |
|---|---|---|
| 9 | Open **Comparaison**, pick the top two | Both candidates side by side with their sub-scores, then the contributions table |
| 10 | **Add up the contributions column by hand** | It equals the score difference **exactly**, to the displayed precision. This is the demonstration's strongest moment: the explanation *is* the score calculation read term by term, not a summary of it. Three decimals are shown deliberately — at two, a reader subtracting the scores gets a different answer from the column |
| 11 | Read the **Dominance** panel | Either a candidate named as dominated by another, or **"Aucun candidat de cette exécution n'est dominé"** — a finding, not a blank space. The rule is restated on screen: at least as good on every criterion, strictly better on at least one, **no weights involved** |

#### Publish, and prove where it came from — FR-19

| # | Do | Expect |
|---|---|---|
| 12 | Publish the top candidate, then open **Publications** | The trace in full: run id, **seed 42**, the **whole weight vector including S10's zero**, model version `weekly.h1-h12.s2-s10`, the deterministic budget, the author and the moment. A score is only recomputable by hand from *every* weight, so no summary is shown |
| 13 | **Kill the API process** (Ctrl-C) and restart it; reload Publications | The complete trace comes back. It survives a restart because it is **assembled from the run record on every read**, never stored beside the publication — a second copy of the seed would be a second answer, free to drift |

**Stop here for a 15-minute slot.** Steps 14–15 are the part that distinguishes this system from one
that merely produces a timetable, and they need their own time.

#### An instance with no solution — FR-8

| # | Do | Expect |
|---|---|---|
| 14 | Withdraw four computer laboratories from `data/instance/rooms.csv` (or run `pytest tests/acceptance/test_fr08.py`), then launch a run | The pre-analysis fails first and **names the resource and the quantity**: `Lab_Info` short by **48 periods / 36 two-period windows**. The run then reaches **`DIAGNOSED`** and the conflict report names **`H3`**, marked *irreducible* because each rule was withdrawn and re-solved |
| 15 | State the limit rather than waiting to be asked | On an infeasibility CP-SAT **cannot prove** — the pre-C-13 contiguity shape — the run lands in **`FAILED`** carrying *"neither a solution nor a proof"*, and **the pre-analysis is the only thing that says what is wrong**. That is honest and it is the recorded behaviour; the acceptance criterion is worded to include it |

⚠️ **Restore `rooms.csv` afterwards.** `scripts/verify-instance.ps1` will tell you if you forgot.

---

## 2 · The FR-2 timed walkthrough

**The one acceptance criterion no automated check can replace.**

> *"The availability grid is filled in under 5 minutes without training."*

It is about a **person**, so it is measured with one. Everything else in this project is verified by a
test; this is verified by a stopwatch, and recording the number is what turns it from an aspiration
into a result.

### Protocol

**Choose the participant properly.** A teacher, or someone standing in for one, who **has not seen the
screen before**. Not the author, not anyone who watched it being built. "Without training" is half the
criterion, and a participant who already knows where the save button is cannot measure it.

1. **Prepare** — application running, participant signed in as a teacher account, the grid open, and
   **nothing explained**. No tour, no "you just click here".
2. **Give the task, once, in these words:**
   > *"Mark the times in the week when you are not available to teach, and save."*
   Nothing more. If asked how, say *"as you think it works"* and start the clock.
3. **Start the stopwatch** when they take the mouse.
4. **Stay silent.** Answer nothing until they finish or ask to stop. A hint invalidates the run — and
   an unanswered question is itself a finding worth writing down.
5. **Stop the stopwatch** when the save confirms and they say they are done.
6. **Record below**, whatever the number. A failure recorded honestly is worth more than a pass
   obtained by coaching.

### What to write down besides the time

- Anything they hesitated over or asked about.
- Anything they expected to find and did not.
- Whether they noticed Saturday afternoon is absent, and whether that confused them.
- Whether they understood that grey cells are *generated* declarations rather than their own.

### Result

⚠️ **Not yet run.** The criterion is **built and unticked**, deliberately — it is the only one of the
nine outstanding, and nothing in this repository can close it.

| Date | Participant (role, seen it before?) | Time | Under 5 min? | Notes |
|---|---|---|---|---|
| *(to be filled)* | | | | |

**When it is run**, record the row above **and** tick the criterion in `docs/status.md`'s acceptance
list, with the time. Those two edits are the whole of what remains.

---

## 3 · What this demonstration does not show

**Read this before presenting.** Every item is a deliberate, recorded position — not an oversight — and
each has a one-sentence answer if asked.

| Not shown | The honest answer |
|---|---|
| **The AI assistant** — explanations, questions, reports (FR-22, FR-24, FR-25) | Scaffold only: interfaces, no implementation. ADR-010 commits it to increment 1; the 20-day plan allocates it to no phase. That is **C-1**, recorded since 2026-07-29 and still unscheduled |
| **Regeneration from an accepted recommendation** (FR-23) | Half-built. The closed three-action catalogue and its translation exist; turning an accepted recommendation into a new run does not. ⚠️ *H10's dormant gap — `lock_session`'s prerequisite — was filled on 2026-08-06 by Phase 7 M1 (C-19)* |
| **Calendar administration screen** (FR-9) | Not built. ⚠️ **The acceptance criterion is met** — closing a half-day in *configuration* removes those slots from every timetable with no code change, and that is tested. What is absent is the screen |
| **Data management** (FR-1) and **print/export** (FR-10) | Not built. Data arrives through the 13 CSVs and the loader |
| **Account management** | Not built. Accounts come from the seed command (C-18), and every one shares a password |
| **A deployment** | ⚠️ **Not deployable as it stands.** `OPTIEDT_SECRET_KEY` defaults to a value published in this repository, so tokens signed with it can be forged. Safe to demonstrate, not to expose |

⚠️ **If asked "where is the AI?"**, the answer is in `docs/ai-integration.md` and it is worth giving in
full rather than deflecting: **constraint programming is the AI here**, in the symbolic sense — CP-SAT
places every session and guarantees the twelve hard rules by construction. The language model was
deliberately confined to explaining figures it cannot change (ADR-006), because a model that scored or
ranked would produce a number the department could not recompute or defend. What is missing is that
explanatory layer, and it is missing for a scheduling reason, not a design one.

---

## Where the figures in this file come from

Every number above is measured and recorded elsewhere — none is an estimate written for the occasion:

| Figure | Source |
|---|---|
| 147–150 s, 3 distinct candidates, 0 duplicates | `docs/status.md`, Measurements |
| 90.9 % / 71.4 % occupancy, 12 periods, 11 free slots | `scripts/verify-instance.ps1`, run on every `run-checks.ps1` |
| `H3`, irreducible, on the area case | `tests/acceptance/test_fr08.py` |
| The trace surviving a restart | `docs/status.md`, FR-19 row — verified on a real solve |
| 47 accounts, one password | `optiedt/services/seed.py` |

If a figure here and a figure there ever disagree, **the measurement wins and this file is the bug**.
