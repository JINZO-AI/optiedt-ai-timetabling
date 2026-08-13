# OptiEDT — how to use it

A short guide to the screens. No technical background needed.

---

## 1 · What OptiEDT is

OptiEDT builds weekly timetables for a university department.

You give it the department's data — courses, teachers, rooms, groups and the hours in a week. It
produces several complete timetables that break none of the department's rules, puts them in order from
best to worst against quality criteria you can inspect, and explains in plain language why one is
better than another.

Three things it is worth knowing up front:

- **Every timetable it produces is valid.** No teacher is in two rooms at once, no group has two
  sessions at the same time, no room is double-booked. This is guaranteed, not checked afterwards.
- **It produces several, not one.** They differ in quality, not in validity, and you choose.
- **Every number it shows can be checked by hand.** Nothing about the ranking is hidden.

---

## 2 · Signing in

Open the address of the application. You will see a sign-in page.

Four buttons — Timetable Officer, Administrator, Teacher, Student — fill in the matching username for
you. **They only fill in a name.** What you are allowed to do comes from the account you actually sign
in with, not from the button you pressed.

Type the password and press **Sign in**.

---

## 3 · The four roles

| Role | What this person does |
|---|---|
| **Timetable Officer** | Loads the department's data, generates timetables, compares them and publishes the chosen one. This is the main role |
| **Administrator** | Manages the academic calendar (holidays, closed half-days) and the user accounts |
| **Teacher** | States when they are available to teach, and reads the timetables |
| **Student** | Reads the published timetable of their own group |

Each role sees only its own screens. A teacher signing in does not see the Generate screen at all.

---

## 4 · Finding your way around

The dark strip down the left is the navigation. It has three groups:

- **Timetabling** — producing and reading timetables
- **Inputs** — the information timetables are built from
- **Institution** — calendar and accounts

The white bar across the top always tells you **which screen you are on**, a line about what it is for,
and **the one main button for that screen**. That button stays visible while you scroll.

---

## 5 · Department data *(Timetable Officer)*

**Navigation → Inputs → Department Data**

This screen shows what the system is currently working from: how many sessions, groups, teachers,
courses, rooms, time slots and holidays.

To use a different department's data, upload the eleven expected files. The system **checks every line
before recording anything**. If something is wrong it records nothing, keeps the previous data, and
shows you a list of the exact lines at fault — the file, the line number, the column and the value.

You can withdraw an upload at any time and go back to the data the system shipped with.

---

## 6 · Teacher availability

**Navigation → Inputs → Availability**

A weekly grid. Green means available to teach; grey means the teacher has said they are not. Click a
cell — or drag across several — to change it, then press **Save availability**.

Hatched cells are closed by the academic calendar. Nothing is ever scheduled in them, so they cannot be
changed here.

A teacher sees only their own grid. The Timetable Officer can view any teacher's.

---

## 7 · Generating a timetable *(Timetable Officer)*

**Navigation → Timetabling → Generate**

Choose a **search effort** — Quick, Standard or Thorough — and press **Generate timetable**.

The screen shows three stages as they happen:

1. **Data checks** — a fast check that a timetable is possible at all
2. **Optimisation** — the actual work of placing every session
3. **Score & rank** — measuring the results and putting them in order

**This takes a few minutes.** You can leave the screen and come back; the run continues.

A longer search improves the *quality* of the result. It never affects whether the compulsory rules are
respected — those hold in every result, always.

⚠️ If a second run says **Queued**, it is waiting for the first to finish. Only one runs at a time,
because each uses the whole machine.

---

## 8 · Reading the candidates

When the run finishes you get a ranked list. Each row shows:

- its **position** — 1 is best
- the **approach** used to obtain it: Balanced, Student-friendly or Teacher-friendly
- a small **bar chart** — seven bars, one per quality criterion, taller is better
- its **score out of 100**

The bar chart is there for a reason: two timetables can score almost the same and still be very
different. The bars show that at a glance.

Press **Show terms** on any row to see the seven criteria in full, with the measured value beside the
score it produced.

Press **Publish** on the one the department adopts.

---

## 9 · Comparing two candidates

**Navigation → Timetabling → Compare**

Pick two timetables. The top of the screen puts them side by side with their scores and the difference
between them.

Below that is the heart of the product: **where the difference comes from**. One row per criterion,
with a bar to the right if the first timetable is better on that criterion and to the left if the
second is.

At the bottom, two figures: the **sum of the contributions** and the **difference in score**. They are
always identical, and the green line says so. That is what makes the ranking defensible — the
explanation is the calculation itself, not a summary of it.

**Dominance** below tells you whether one timetable is simply better than another on every single
criterion, or whether the ranking is settling a genuine trade-off.

**Improve this timetable** lets you change one thing — give a criterion more weight, fix a session in
place, or block a time slot — and run again. ⚠️ This never edits the timetable in front of you. It
starts a new run, so the guarantees still hold.

---

## 10 · The AI explanation

On the right of the Compare screen is a panel headed **OptiEDT AI**.

It writes explanations in ordinary language: why a candidate scored as it did, what trade-offs it
makes, where it is weakest. There are suggested questions, and you can type your own.

**Two things matter here, and the screen says both:**

- OptiEDT itself does all the calculation — the timetable, the scores, the ranking, the
  recommendation. The AI **only explains** results that already exist. It decides nothing.
- **It cannot invent a number.** Every figure it writes is checked against the figures the system
  calculated. If it produces one that does not match, the whole answer is thrown away and you are shown
  the system's own figures instead, with the reason.

Above every answer is a line saying who wrote it: *Written by the language service* or *Computed by the
application*. Read that line first.

If the AI is switched off, everything still works. You see the system's own figures — complete, just
not written as prose.

---

## 11 · Timetables

**Navigation → Timetabling → Timetables**

The week as a grid. Four views, on the tabs:

- **By teacher** — one teacher's week
- **By group** — one group's week
- **By room** — one room's week
- **Room occupancy** — how heavily each room is used

Colours mark the kind of session, and each cell also prints the code so the colour is never the only
clue:

- **CM** — a lecture, for the whole year group
- **TD** — a tutorial, for one small group
- **TP** — practical work, in a laboratory

**Print** and **Export CSV** are in the top bar. Both carry which run and which candidate they came
from, so a printed sheet can always be traced back.

---

## 12 · Examinations *(Timetable Officer)*

**Navigation → Timetabling → Examinations**

Builds the examination calendar: one examination per course, placed inside the examination period set
in Administration.

You supply nothing here. The candidates are the students of the year group concerned and the supervisor
is the teacher who gives the lecture — both taken from the department's data.

Choose an effort and press **Generate calendar**. It takes about half a minute. The result can be read
by day or by room.

---

## 13 · Publishing

Publishing is the moment the department says *this is the timetable people follow*.

Press **Publish** on a candidate from the Generate screen. It then appears under **Published**, with
the full record of what produced it — the run, the settings used and the exact version of the model.

**Nothing reaches students until it is published.**

---

## 14 · What a teacher and a student see

**A teacher** signs in and sees three entries: their availability, the timetables, and the comparison.
They can read a comparison and its explanation in full, but cannot start a new run — that belongs to
the Timetable Officer.

**A student** signs in and sees one screen: **My Timetable** — their own group's published week, which
they can print or export. They cannot see draft timetables, other groups, or anything else. Until the
department publishes, the screen says so plainly.

---

## 15 · In short

1. The Timetable Officer loads the data and teachers state their availability.
2. The officer generates — the system produces several valid timetables and ranks them.
3. The officer compares two, reads why they differ, and asks the AI if a plain-language explanation
   helps.
4. The officer publishes one.
5. Teachers and students read it, print it, or export it.
