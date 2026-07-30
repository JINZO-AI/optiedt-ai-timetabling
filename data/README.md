# Data

```
generator/      Produces the 13 instance files. Imports NOTHING from backend/
instance/       The 13 CSVs + constraint_catalogue.csv — the data the app runs on
reference/      ITC-2007, XHSTT — gitignored, validation only, never loaded
verification/   The five checks and their expected results
```

## The generator must reproduce *the* instance, not *an* instance

The three specification documents **state the instance's verification results as
facts** — 0 sessions without a suitable room, 95% laboratory occupancy, a
heaviest load of 12 periods, 425 students matching declared group sizes.

Those are claims about files that do not exist yet. **If the generator produces a
different instance, the delivered documentation becomes false.** It must
reproduce the content of `docs/data-and-instance.md` and satisfy the five
verifications with the stated results.

This is C-11 in `docs/open-questions.md`.

⚠️ **With one correction the generator must honour.** The room mix is now
`Amphi 2 / Salle 7 / Lab_Info 8 / Lab_Sciences 3` (total still 20), not the
`2 / 10 / 6 / 2` the PDFs record, and laboratory occupancy is **91% of
two-period windows**, not 95% of periods. The original mix made the instance
**infeasible**: all 104 laboratory sessions span two periods, a two-period
session must fit inside one day, and a 5-period day gives a room only two such
windows — so 6 computer laboratories offered 66 against 80 needed. The "95%"
was measured correctly and measured the wrong thing. See C-13 in
`docs/open-questions.md`; the errata list carries the replacement figures.

## Why the generator imports nothing from `backend/`

**The 13 files are the contract between the generator and the application.** If
the generator imported the ORM, the file schema would stop being the interface
and the instance would become an implementation detail of the backend — which
would make it impossible to hand the instance to anyone, or to validate it
independently of the code that consumes it.

## `constraint_catalogue.csv`

19 rows — 12 hard (H1–H12) and 7 soft (S2–S10) — each with its corresponding
XHSTT constraint type where one exists. This file is the **authority** for
constraint codes, default weights and XHSTT references; the tables in the
documentation restate it and do not replace it.

`S1`, `S8` and `S9` are **retired**. Codes are permanent identifiers used in the
catalogue, in the conflict report and in `weight_delta` parameters — never reuse
them.

The examination constraints X1–X4 and SX1 are **not** among the 19.

## `reference/` is gitignored

ITC-2007 and XHSTT archives carry their own licences and, per ADR-008, have a
**validation role only** — they are never loaded into the database.

**Three of the four are present and verified.** Run
`scripts/check-reference-data.ps1` to see what is there and re-measure the known
Kaggle defects; the full record is in
[`reference/PROVENANCE.md`](reference/PROVENANCE.md).

⚠️ **The Kaggle archive describes itself as clean and is not.** 44% of its
timeslot rows have an end time at or before their start time, and 83% of its
room+slot pairs are double-booked. Its `students.csv` also carries names, emails,
phone numbers and addresses — read PROVENANCE.md before touching it.

**ITC-2007 Track 1 is not present and has not been opened.** Its verification is
placed at the start of increment 2, and **no property of it is assumed before
then**.

## Marking generated data

Every generated availability row carries `SYNTHETIC` in its source column.

This matters for the honesty of the demonstration: the application collects
availability from a web form, and generated declarations exist only so the
instance is solvable before any teacher has connected. A generated declaration
and a real one must be distinguishable at any moment.
