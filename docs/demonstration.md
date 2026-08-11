# Demonstration

**A script anyone can execute, where every step states its expected result.**

That last clause is the point. A demonstration whose steps say only what to *do* can fail silently —
the presenter improvises around a blank screen and nobody watching knows whether they saw the product
or a recovery. Every step below says what should appear, so **a failed demonstration is visible**.

Two things live here:

- **§1 The demonstration script** — the whole path, twelve steps, about 12 minutes plus one solve.
- **§2 The FR-2 walkthrough** — the one acceptance criterion no automated check can replace, its
  protocol, and the table recording the result. **Run 2026-08-07, and the criterion was reworded
  rather than met as written** — read §2's Result before quoting it.

And **§4** records the first live language-provider call, **performed 2026-08-07**. That was FR-24's
last outstanding condition; it is a deployment step rather than a step of the script above.

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

#### Hand the timetable out — FR-10

| # | Do | Expect |
|---|---|---|
| 14 | Open **Emplois du temps**, pick a group, press **Exporter (CSV)** | A file named for what it holds — `optiedt-par-groupe-…-cand-2.csv`. Open it: **above the table sit the run, the candidate, the seed, the model version and the whole weight vector**, so a timetable that has left the application still traces back to what produced it. ⚠️ Pick a **TP subgroup** and point out that the file carries the promotion's `CM` rows too — a subgroup shown only its own sessions would hand a student a week with holes they do not have |
| 15 | Press **Imprimer** on the same view, and stop at the preview | The navigation, the selectors, the tabs and the buttons are gone; **a header appears that is on paper only**, naming the view, the resource, the run and the candidate. Say why it exists: without it the sheet is a correct print of an **unidentifiable** document, and two candidates of one run are indistinguishable once printed |

⚠️ **Do not present FR-10 as finished on the requirement sheet.** The software is done and tested; the
requirement is **`WIP`**, because **C-9** leaves it with no acceptance criterion to verify against. If
asked why, that is the whole answer — and it is a specification gap, not unfinished work.

**Stop here for a 15-minute slot.** Steps 16–17 are the part that distinguishes this system from one
that merely produces a timetable, and they need their own time.

#### Room occupancy, and what the figure means — FR-18

| # | Do | Expect |
|---|---|---|
| O1 | On **Emplois du temps**, choose the **Occupation des salles** view | Every one of the 20 rooms, grouped by type — **including any room no session was placed in, at 0 %**. That row is the most actionable one in the table |
| O2 | Read the note above the table | It states the figure: **périodes occupées / créneaux ouverts**. ⚠️ **Say this out loud**: it measures *time*, not seat fill. In the international space-management vocabulary this is a *frequency* rate; a room can be lightly booked and full every session |
| O3 | Compare `Lab_Info` with `Salle` | The laboratories run far tighter. ⚠️ **And the note's second half is the C-13 lesson**: for the laboratories the bound that really binds is two-period *windows*, not periods |
| O4 | Export the CSV | The header names the quantity in full, and the caveat travels with the file — a rate arriving in a spreadsheet without the sentence that qualifies it is how the wrong bound gets quoted in a meeting |

#### The administrator configures the calendar — FR-9

⚠️ **Do this AFTER publishing, not before.** Closing a half-day changes what every later run can
produce, and on this instance it takes `Lab_Info` to exactly 100.0 % of its two-period windows.

| # | Do | Expect |
|---|---|---|
| A1 | Sign out; sign in as **`administrateur`** | The navigation offers **Administration** and nothing else it should not — no Génération, no Publications |
| A2 | Open **Administration → Calendrier** | The whole week, each slot marked **Ouvert** or **Fermé**. Saturday afternoon already reads **Fermé** — that comes from `slots.csv`, and it carries no *modifié* tag, because it is the institution's decision rather than this administrator's |
| A3 | Close Wednesday afternoon (two cells) | Both cells flip and gain a **`modifié`** tag. **The open-slot count drops from 28 to 26 before you save** — the margin you are spending, shown while you spend it |
| A4 | Save, then open **Génération** as `responsable` and launch a run | The pre-analysis now reports **`80/80 2-period windows = 100.0%`** for `Lab_Info`. ⚠️ **Say this out loud:** the next closure has nowhere to come from. The run still completes and every session is still placed |
| A5 | Open any timetable view | Wednesday afternoon is drawn **fermé** and holds nothing, in every candidate. **No code changed** — the constraint catalogue still holds exactly H1–H12 |
| A6 | Back in **Administration**, press **Réinitialiser** | The week returns to the one the 13 CSVs describe. The edit was layered, never written into the instance, which is what makes withdrawal possible at all |

#### The administrator manages accounts — FR-11

| # | Do | Expect |
|---|---|---|
| A7 | Open **Administration → Comptes** | Every account with its role and its link. **No password is shown for any of them** — the account payload has no field that could carry one |
| A8 | Create a **STUDENT** account, choosing a group | The form asks for a group only for a student, and for a teacher only for a teacher. Creating one without its link is refused **by the API**, and the refusal is displayed as the API worded it |
| A9 | Try to remove your own account | Refused. Nothing else could then manage the accounts or the calendar, and no screen creates an administrator |

#### A student sees their own week, and only that — SRS Table 2

| # | Do | Expect |
|---|---|---|
| A10 | Sign in as **`etudiant`** | **One** navigation entry: *Mon emploi du temps*. Landing goes straight there |
| A11 | Read the timetable | The published week of their group, **including the promotion's CM sessions** — a subgroup's week is not only the sessions addressed to it. It names when it was published and by whom |
| A12 | Print it, or export the CSV | The same print sheet and spreadsheet FR-10 gives every other view, carrying the group and the publication |
| A13 | Try `/api/runs`, `/api/publications` or another teacher's grid | **403** on each. A run carries every group's *drafts*; Table 2 gives the student the published timetable of **their** group and nothing more |

#### An instance with no solution — FR-8

| # | Do | Expect |
|---|---|---|
| 16 | Withdraw four computer laboratories from `data/instance/rooms.csv` (or run `pytest tests/acceptance/test_fr08.py`), then launch a run | The pre-analysis fails first and **names the resource and the quantity**: `Lab_Info` short by **48 periods / 36 two-period windows**. The run then reaches **`DIAGNOSED`** and the conflict report names **`H3`**, marked *irreducible* because each rule was withdrawn and re-solved |
| 17 | State the limit rather than waiting to be asked | On an infeasibility CP-SAT **cannot prove** — the pre-C-13 contiguity shape — the run lands in **`FAILED`** carrying *"neither a solution nor a proof"*, and **the pre-analysis is the only thing that says what is wrong**. That is honest and it is the recorded behaviour; the acceptance criterion is worded to include it |

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

**Run 2026-08-07, and the criterion was REWORDED rather than met as written.** Read the rewording
before the row, because the row does not mean what the original wording asked for.

| Date | Participant (role, seen it before?) | Time | Under 5 min? | Notes |
|---|---|---|---|---|
| **2026-08-07** | **Project owner**, acting as teacher then as person in charge. **Had not seen the interface before** — the frontend was not written by them | **not measured** | **not established** | Completed the grid unaided. Reported the *navigation* confusing, looked for a registration flow that does not exist (C-18), and said sections do not explain their purpose |

#### The rewording, and why

The criterion read *"the availability grid is filled in under 5 minutes without training."* Two of its
three clauses were satisfiable and one was not, so it was **reworded by project-owner decision** rather
than ticked against wording the run did not meet — the same treatment as **C-5** and as acceptance
criterion 5, and for the same reason: *the wording moved, the implementation did not.*

> **Reworded criterion:** *the availability grid is completed without assistance by a user who had not
> previously seen it.*

**What the run established.** The participant reached the grid, understood the task, marked
unavailability and saved, with **no assistance and no explanation given**. On the grid specifically the
verdict was that the functionality is acceptable.

⚠️ **What it did NOT establish, stated plainly so nobody quotes this row for more than it holds:**

- **No time was measured.** *"Under 5 minutes"* is therefore unverified, and the reworded criterion
  drops it rather than pretending otherwise.
- **The participant is the project owner.** They had not seen the *screen* — which is what the protocol
  above actually requires — but they know the domain, the calendar and the `SYNTHETIC` convention, so
  the four comprehension questions above could not be asked of them fairly.
- **The task was not isolated.** Navigation, sign-in and other screens were exercised in the same
  sitting, so nothing here is a clean single-task measurement.
- **No naive participant was available**, and the owner declined to involve one. That is a recorded
  constraint on the evidence, not an oversight.

⚠️ **The findings point the other way on the application as a whole**, and that tension is left visible
on purpose: the same session reported that navigation is confusing and that pages do not explain their
purpose. The grid passes; **the product around it did not**, and those findings are usability work, not
FR-2 evidence.

**If a naive participant ever becomes available, run the protocol above as written and add a second
row.** A measured time against the original wording would be strictly better evidence than this row.

---

## 3 · What this demonstration does not show

**Read this before presenting.** Every item is a deliberate, recorded position — not an oversight — and
each has a one-sentence answer if asked.

| Not shown | The honest answer |
|---|---|
| ~~**The AI assistant** — explanations, questions, reports (FR-22, FR-24, FR-25)~~ | ✅ **Built 2026-08-06, Phase 7 M3–M5**, and reachable from the comparison screen. ⚠️ **A LIVE model is still not shown BY THIS SCRIPT**: the service is off by default and no test calls a provider (**C-21**), so what a demonstration shows is the **computed form** — complete figures, no prose. Say so plainly. A first live call **was** performed once, on 2026-08-07, and §4 records it; that is a deployment step, not a step of this script |
| ~~**Regeneration from an accepted recommendation** (FR-23)~~ | ✅ **Built 2026-08-06, Phase 7 M2.** Reachable from the comparison screen: choose one of the three catalogue actions, accept, and a **new run** is launched through the same solver. The candidate on screen is unchanged. H10's dormant gap — `lock_session`'s prerequisite — was filled by M1 (C-19) |
| **Calendar administration screen** (FR-9) | Not built. ⚠️ **The acceptance criterion is met** — closing a half-day in *configuration* removes those slots from every timetable with no code change, and that is tested. What is absent is the screen |
| **Data management** (FR-1) | Not built. Data arrives through the 13 CSVs and the loader |
| **Print / export** (FR-10) | ✅ **Built 2026-08-10** — steps 14–15 above. ⚠️ Still shows as **`WIP`** on the requirement sheet: **C-9** leaves it with no acceptance criterion, so there is nothing to verify a `✓` against. Say *"the software is finished and the specification row is missing"*, which is exactly what it is |
| **Account management** | Not built. Accounts come from the seed command (C-18), and every one shares a password |
| **A deployment** | ⚠️ **Not deployable as it stands**, though it can no longer fail silently: `OPTIEDT_SECRET_KEY` defaults to a value published in this repository, and **since 2026-08-07 `OPTIEDT_ENVIRONMENT=production` makes start-up REFUSE that default** (`Settings.require_deployable`, verified to fire). Account management is still unbuilt and every seeded account shares one password. Safe to demonstrate, not to expose |

⚠️ **If asked "where is the AI?"**, the answer is in `docs/ai-integration.md` and it is worth giving in
full rather than deflecting: **constraint programming is the AI here**, in the symbolic sense — CP-SAT
places every session and guarantees the twelve hard rules by construction. The language model is
deliberately confined to explaining figures it cannot change (ADR-006), because a model that scored or
ranked would produce a number the department could not recompute or defend. **That explanatory layer
now exists** (Phase 7), and every number it writes is checked against the context it was given; an
answer containing a figure nobody computed is discarded and the computed form shown instead.

---

## 4 · The step this demonstration cannot perform by itself: a live model call

⚠️ **Not a defect, and not optional either.** `assistant_enabled` is False by default and **no test in
this repository calls a live provider** — a model's output is not fixed by a seed, so such a test would
report the machine and the day rather than the software (**C-21**). Everything the suite proves is
about the application's behaviour *around* a provider. **That is still true, and performing the call
below did not change it** — the suite is exactly as provider-free as it was.

**So the first live call is a deployment step, and it is what FR-24 was waiting on.** Perform it once,
deliberately, and record the result here:

1. Set `OPTIEDT_ASSISTANT_ENABLED=true`, `OPTIEDT_ASSISTANT_BASE_URL`, `OPTIEDT_ASSISTANT_API_KEY` and
   `OPTIEDT_ASSISTANT_MODEL` in `backend/.env` — which is gitignored. ⚠️ **The key must never be
   committed.**
2. Open a completed run's comparison screen and read the explanation.
3. Record three things: whether the answer was **generated** or fell back, whether any answer was
   **discarded** for an ungrounded figure, and whether the figures quoted match the screen.

| Date | Provider and model | Generated? | Discarded any? | Figures matched? |
|---|---|---|---|---|
| **2026-08-07** | Groq · `llama-3.3-70b-versatile` | **Yes — 3 of 3** | **No — none discarded** | **Yes** |

**What was actually done**, so the row above can be checked rather than believed. A real run through
the API at production settings (seed 42, deterministic budget 90) reached `COMPLETED` with **3 distinct
candidates**; the top one scored **80.30714644396436** under `student-favouring`. Three live calls
followed, all HTTP 200 with `generated: true` and `fallbackReason: null`:

| Call | Endpoint | Result |
|---|---|---|
| Explanation (FR-22) | `GET …/assistant/runs/{id}/candidates/{id}/explanation` | Quoted the score and the normalised values **exactly as the application displays them** — `0.9773936170212766` (S3), `0.6453488372093024` (S4), `0.8539144471347861` (S6), plus seed 42, budget 90 and 218 placements |
| A question it can answer (FR-24) | `POST …/assistant/runs/{id}/question` | *"Le candidat avec le meilleur score est le candidat 1, avec un score de 80.307."* — **80.307 is the top candidate's score to three decimals** |
| A question it **cannot** answer (FR-24's criterion) | `POST …/assistant/runs/{id}/question` | *"Le contexte ne fournit pas d'informations sur le nombre d'étudiants inscrits en deuxième année."* — **declined, and invented no figure** |

⚠️ **One imprecision, recorded rather than smoothed over.** The second answer calls the winner *"le
candidat 1"*. The top candidate is `…-cand-2`; "1" is defensible as *first in the ranked list*, and the
digit is grounded, but a reader could take it for candidate id `cand-1`, which scores 79.65. **The
grounding check cannot catch this and does not claim to** — it verifies that every number appears in
the context, never that the surrounding sentence is right (`assistant/verifier.py`). This is precisely
the class of defect C-21 says no test can fence off, and it is why nothing the department must defend
rests on this service.

⚠️ **A defect in `assistant/adapter.py` was found by performing this step, and no reading would have
found it.** The adapter sent no `User-Agent`, so `urllib` supplied `Python-urllib/<version>`, which
Groq's CDN refuses with **HTTP 403 / Cloudflare `error code: 1010`** — a client-signature refusal that
names neither key nor model, so it reads like an authentication fault it is not. Every explanation fell
back to its computed form with an honest reason, which is degraded mode working correctly, and which is
also why nothing failed loudly. Fixed by having the client identify itself; pinned by
`tests/unit/test_assistant.py::test_the_adapter_identifies_itself_rather_than_sending_the_urllib_default`,
which intercepts `urlopen` and calls no provider.

⚠️ **What this row does and does not establish.** It establishes that the application can obtain a
grounded answer from a real provider, and that a question the context cannot answer produces no
invented figure. **It does not establish that any provider answers well in general** — one call on one
day with one model, which is the whole of C-21. Do not quote this row as evidence about a model.
**And note the configuration it required:** `OPTIEDT_ASSISTANT_ENABLED` was returned to `false`
afterwards, because that is the documented default and the suite's FR-22 degraded-mode test asserts it.

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
