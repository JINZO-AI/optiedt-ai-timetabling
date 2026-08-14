# OptiEDT

Automatic generation, ranking and explanation of university timetables for a Tunisian public
faculty.

**Live demo:** https://optiedt-ai-timetabling.vercel.app

---

## 1. What is OptiEDT?

OptiEDT builds a university department's weekly timetable automatically. Give it the courses,
teachers, rooms, groups and available time slots, and it produces several complete, conflict-free
timetables, ranks them by quality, and explains in plain language why one is better than another.

## 2. The problem

A department normally builds its timetable by hand in a spreadsheet: 44 teachers, 51 student
groups, 20 rooms, 218 sessions and 30 weekly time slots, all with rules that must not be broken — a
teacher cannot teach two sessions at once, a room cannot host two sessions at once, a group cannot
be in two places at once, and so on. Doing this by hand takes two to three weeks, depends on one
person who knows how, and conflicts are usually discovered only after the timetable is published.

## 3. What OptiEDT does

```
Data  →  Check  →  Solve  →  3 candidates  →  Score & rank  →  Compare  →  Publish  →  Student view
```

1. **Check** — five quick checks confirm a timetable is even possible before any solving starts.
2. **Solve** — the optimizer places all 218 sessions under twelve rules that can never be broken.
3. **Candidates** — it runs three times with different priorities, so there are three valid
   timetables to choose between, not one.
4. **Score & rank** — each is scored out of 100 on seven quality measures and put in order.
5. **Compare** — the department head sees exactly why one timetable outranks another.
6. **Publish** — the chosen timetable becomes visible to teachers and students.

## 4. How the optimization works

The scheduling itself is done by **OR-Tools CP-SAT**, a constraint solver made by Google. Given the
rules and the data, it searches for an arrangement that breaks none of them. If a rule cannot be
satisfied, no timetable is produced at all — it is not a "close enough" result, it is refused.

The **scoring** is separate and much simpler: a plain weighted sum of seven quality measures (how
spread out a group's day is, whether teachers get their preferred hours, and so on). Because it is
just a sum, the difference between any two timetables can be broken down criterion by criterion and
checked with a calculator — nothing about the ranking is hidden.

**These two things never mix.** The optimizer decides what is *valid*. The score decides what is
*better*. Keeping them apart means a bug in the ranking can only produce a worse order, never an
invalid timetable.

## 5. Where the AI is

An AI assistant explains the results in ordinary language. It does **not**:

- generate the timetable
- decide the score or the ranking
- move or change a single session
- touch the database

It only reads figures OptiEDT already calculated and puts them into sentences. Every number it
writes is checked against those figures — if it ever states one that doesn't match, the whole
answer is thrown away and the plain figures are shown instead. And if the AI is switched off
entirely, everything else keeps working; only the written explanations disappear.

## 6. Main screens

| Screen | What it's for |
|---|---|
| **Generate** | Start a run and watch the three candidates get built and ranked |
| **Timetables** | See a candidate's week by teacher, by group, by room, or by room occupancy |
| **Compare** | See two candidates side by side, with the score difference explained term by term, and ask the AI about them |
| **Examinations** | Build the examination calendar for the term |
| **Published** | The timetable currently adopted, with a full record of how it was produced |
| **Department Data** | Load or replace the department's dataset |
| **Availability** | A teacher's weekly declaration of when they can teach |
| **Administration** | The academic calendar and user accounts |
| **My Timetable** | A student's own group's published week |

## 7. Architecture

```
Browser  →  Vercel (React interface)  →  Render (FastAPI backend)  →  Supabase (PostgreSQL)
```

And from the backend:

```
FastAPI  →  OR-Tools CP-SAT   (places every session)
FastAPI  →  AI Assistant      (explains, never decides)
```

| Technology | Why it was chosen |
|---|---|
| **React + Vite** | A fast, simple frontend, and it builds to static files anyone can host for free |
| **FastAPI** | A Python backend, so it sits naturally next to the Python solver |
| **OR-Tools CP-SAT** | Built specifically for problems like this — assign things under hard rules |
| **PostgreSQL (Supabase)** | A reliable, managed relational database |
| **Vercel** | Serves the static frontend worldwide, free, and redeploys on every push |
| **Render** | The solver needs a server that stays alive for minutes at a time — Vercel's functions get stopped after seconds, so the backend runs here instead |
| **Groq (AI provider)** | Used only to write the plain-language explanations — nothing else |

## 8. Problems I ran into

**A reassuring number turned out to be the wrong measure.** Checking how full the week was overall
showed 71% occupancy — comfortable. The real risk was in two-hour windows, which were at 91% with
almost no spare room. I had trusted the easy number instead of trying to disprove it, and it cost
several days before I caught it.

**The solver's own reported score didn't match its answer.** A separate part of the system
recomputes the score independently from the actual placements rather than trusting the solver's
internal number, and that separation is what caught a real bug in the solver library — nothing in
the product broke.

**Docker looked successful while connecting to the wrong database.** Another PostgreSQL was already
running on the same port. The container reported "healthy", but every connection reached the other
server instead. Now the port is configurable and I check the version to confirm which one I'm
actually talking to.

**One hard-coded setting made the whole app impossible to deploy.** The list of websites allowed to
call the API was a fixed value in the code. It worked perfectly on my machine and nowhere else.
Making it configurable was the one change that unblocked deployment.

**Vercel looked like the obvious place for everything.** It isn't — its functions get stopped after
a few seconds, and the solver runs for minutes. I checked this against Vercel's own documentation
before assuming, and split the deployment instead: the interface on Vercel, the backend on a server
that stays running. It took one small configuration file, no changes to the actual application.

## 9. Testing and verification

At the last full check: **196/196** frontend tests, **644** backend tests passing (**74** skipped —
these need a live database and are excluded unless one is running), full typecheck clean on both
sides, production build clean, and **0** tracked secrets.

The ranking is independently verifiable: the top-ranked timetable in the live system scores
**81.4384272710004**, and recomputing it by hand from its seven published criterion values gives the
identical number to the last digit.

## 10. Current limitations

Honest, and specific to the free hosting tier — none of these are limits of the software itself:

- **First page load can take up to a minute.** The free server sleeps when idle and has to wake up.
- **Generating a brand-new timetable is slow here.** The free server has a fraction of a CPU core;
  the same code produces all three candidates in under 5 minutes on a normal machine.
- **Examination results are not saved.** They exist only while the server is running, by design —
  generate and view one in the same sitting.
- **All demo accounts share one password.** This is a demonstration setup, not how real accounts
  would work.

## 11. How to test the demo

1. Open the live demo link above.
2. Sign in — pick a role, it fills in the username; type the shared demo password.
3. As **Timetable Officer**: open **Generate** — a completed run with three candidates is already
   loaded.
4. Open **Timetables** and look at the different views of the same week.
5. Open **Compare**, pick two candidates, and read the score breakdown.
6. Ask the AI assistant a question — try a suggested one, then something it clearly can't know; it
   should decline rather than guess.
7. Open **Published** to see the adopted timetable and its full record.
8. Sign out and sign back in as **Student** to see the same week from a student's side.
9. Sign back in as **Timetable Officer** and try **Examinations**, if you'd like to see a fresh
   calendar generated (takes about half a minute).

## 12. Project documentation

- [`docs/architecture.md`](docs/architecture.md) · [`docs/domain-model.md`](docs/domain-model.md) — how it's built
- [`docs/constraint-model.md`](docs/constraint-model.md) — the solver's rules
- [`docs/scoring-and-explanation.md`](docs/scoring-and-explanation.md) — how the score works
- [`docs/AI_BEHAVIOR.md`](docs/AI_BEHAVIOR.md) — exactly what the AI may and may not do
- [`docs/deployment.md`](docs/deployment.md) — how and why it's deployed this way
- [`docs/specifications/`](docs/specifications/) — the original requirements documents

## 13. Author

Mohamed Jawad Touir — company internship project, academic year 2025–2026.
