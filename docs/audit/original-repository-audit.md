# Audit of the original OptiEDT repository

**Audited revision:** `4c9f933` (branch `main`, 2026-08-20), the state the reconstruction started from.
**Method:** every source file under `backend/src`, `frontend/src`, `data/`, `scripts/`, the
migrations, the thirteen instance CSVs, the three specification PDFs and the 9,500 lines of
`docs/` were read. Both test suites were run. The solver was timed on the reference instance.
Findings below are about what the code does, checked against what the documents say it does.

## 1. What the original project is

A four-week company-internship project (Cahier des Charges, cover page: "Duration 4 weeks")
that builds the weekly timetable of **one department of one Tunisian public faculty**. The
pipeline is:

```
13 CSV files ─► loader ─► 5 arithmetic pre-checks ─► CP-SAT, once per weight profile (3)
             ─► weighted-sum score /100 ─► ranking ─► pairwise decomposition ─► publication
```

plus an LLM that phrases explanations of already-computed figures, a teacher availability
grid, an administrator calendar editor, a student view of the published week, and an
examination calendar solved on demand.

Size: 17,153 lines of Python in `backend/src`, 11,666 lines of TSX/CSS in `frontend/src`,
9,525 lines of Markdown in `docs/`.

Baseline measurements taken during the audit (4 cores, 15 GB RAM):

| Check | Result |
|---|---|
| Backend tests (`-m "not solver and not database"`) | 635 passed, 9 skipped, 149 deselected, 56 s |
| Frontend tests (Vitest) | 197 passed |
| Frontend production build | succeeds, 306 kB JS |
| Feasibility solve, reference instance (218 sessions) | 2.6 s |
| One weight profile, deterministic budget 30, 4 workers | 50.7 s, not proven optimal |

## 2. What is sound and worth carrying forward (as ideas, not code)

1. **The solver never certifies itself.** Criteria are recomputed from the placements by an
   analysis layer that is forbidden (by `import-linter`) from importing the solver. This caught
   a real discrepancy: under `interleave_search`, `CpSolver.objective_value` was reported above
   the value of the returned solution (`solver/engine.py` docstring).
2. **Reproducibility was taken seriously:** fixed seed, `max_deterministic_time`,
   `interleave_search=True` for determinism across worker counts, all recorded per run.
3. **Pre-analysis before solving:** pigeonhole-style checks that name a resource and a missing
   quantity. The project learned the hard way (its "C-13") that a near-saturated instance
   reports `UNKNOWN` rather than `INFEASIBLE`, and that a necessary-but-not-sufficient check
   that passes misdirects debugging.
4. **Assumption literals were measured to damage presolve.** Putting enforcement literals on
   `NoOverlap`/`Cumulative` turned a 0.0 s infeasibility proof into `UNKNOWN` after 240 s
   ("C-17"). The replacement, withdrawing one rule at a time, only covered 4 of 12 rules and
   named rule *codes*, never the resources involved.
5. **The language model decides nothing.** It receives computed figures and every number in
   its output is checked against them.
6. Password hashing used bcrypt directly with an explicit 72-byte guard, and production start-up
   refuses the published default secret key.

## 3. Findings that make the codebase unsuitable as a commercial base

### 3.1 Academic data is not in the database

The department's data is 13 CSV files read once per process (`instance/loader.py`,
`api/deps.get_instance`). An "import" stores the **raw CSV texts as one JSON blob** in a
single-row table (`db/models.py`, `DepartmentDatasetRow`, fixed primary key) and re-parses
them on every request whose revision changed. There is no create, update or delete for any
room, teacher, course, group or session. The only way to change one room is to re-upload
eleven files.

### 3.2 One department, one calendar, one term, one week shape — by construction

- `calendar_overrides` and `department_dataset` are single-row tables with fixed keys.
- The Cahier des Charges (§3.2) puts "simultaneous treatment of several faculties" out of scope.
- Rooms are not shared between departments, so the most common real conflict (two departments
  wanting the same lecture theatre) cannot be represented.

### 3.3 Institution-specific assumptions are hardcoded as enumerations

`domain/enums.py`: `RoomType` has exactly four values (`Amphi`, `Salle`, `Lab_Info`,
`Lab_Sciences`); `SessionType` is `CM`/`TD`/`TP`; `TeacherRank` is the four Tunisian ranks;
`GroupLevel` admits exactly one chain `PROMO → TD → TP`. Day names are French literals in
`slots.csv` and in the frontend (`DAY_NAMES`). Session duration is 1 or 2 periods.
`occurrences_per_week` is read but every row is 1 and the model assumes it (H7).

### 3.4 The constraint system is closed

Twelve hard rules (`H1`–`H12`) and seven soft criteria (`S2`–`S10`) are fixed codes. The
catalogue CSV is declared "the software's own" and deliberately cannot be changed by a
department (ADR-003, "invariant 7"). There is no way to express a maximum daily load, a
consecutive-hours limit, a lunch break, a maximum number of teaching days, a lecture-before-lab
precedence, a campus travel time or a room preference.

`S5` ("teacher preference", second-highest weight) is a **proxy**: the data has no preference
column, so it counts sessions in the first or last period of any day (`docs/open-questions.md`,
C-12). The availability grid in the UI offers "preferred", but nothing stores it.

### 3.5 The score is a composite number

Seven criteria are normalised against instance-derived bounds and summed with weights into a
score out of 100. The comparison screen decomposes a difference by criterion, which is useful,
but the headline figure (`81.4384272710004` is quoted in the README) is an arbitrary
composite whose weights no administrator chose.

### 3.6 Solving runs inside the web process with no recovery

`tasks/executor.py` runs solves in a `ThreadPoolExecutor(max_workers=1)` inside the API
process. There is no cancellation, no heartbeat and no lease: a process restart during
`SOLVING` leaves the run non-terminal forever. Progress is not reported while solving —
`docs/architecture.md` states that all candidates appear at once after roughly 105–150 s.

### 3.7 Examination results are not persisted

`services/examinations.InMemoryExamRunStore` is the only store for the examination module;
the README states results "exist only while the server is running".

### 3.8 No manual editing, repair or revision workflow

Manual modification and re-solving after publication are explicitly out of scope (CdC §3.2).
The only way to influence a timetable is to accept one of three machine-proposed actions
(`weight_delta`, `lock_session`, `exclude_slot`) that launch a new run. Publication is a
pointer to a candidate: no approval step (the head of department "has no requirement, no
right, no screen", `docs/domain-model.md`), no version history, no diff between published
versions, no rollback, no date-level change (cancel or relocate one occurrence).

### 3.9 Security

- JWT (HS256, `python-jose`, a library with a history of advisories and little maintenance)
  kept in `sessionStorage`, readable by any injected script; 8-hour lifetime; no revocation.
- No login throttling or rate limiting anywhere (`grep` found none).
- All demonstration accounts share one password (README §10).
- No audit trail of data changes; only runs and the publication author are recorded.

### 3.10 Import, export, localisation, operations

- Import: exactly eleven CSV files with a fixed schema; no XLSX, no column mapping, no preview,
  no partial correction.
- Export: the browser's print stylesheet and a client-side CSV. No PDF, XLSX or iCalendar.
- Language: interface in English, assistant prose in French, data in French; no i18n layer;
  Arabic excluded (CdC §3.2).
- Observability: default logging, a static `/api/health` returning `ok`, no metrics.
- Deployment: Vercel + Render free tier + Supabase. No application Dockerfile, no CI
  workflow, and the helper scripts are PowerShell only.
- `scikit-learn` is a runtime dependency for an unbuilt feature (FR-21, weight fitting).

### 3.11 Demonstration data

218 synthetic sessions. All 157 availability rows are generated (`source=SYNTHETIC`). Course
titles repeat within one cohort (`INFOL1-02` and `INFOL1-04` are both "Systemes
d'exploitation L1"). There is no second department, campus, elective or shared room.

### 3.12 Code and documentation style

32% of all backend source lines are docstrings. Production modules carry 268 `⚠️` markers and
343 references to project-process identifiers (`C-13`, `Phase 7 M2`, `FR-22`) along with
dated measurements and retractions ("this docstring claimed until 2026-08-03…"). The result
reads as a development journal embedded in the code: the reasoning is often good, but the
next maintainer has to read history to find behaviour. The same pattern fills `docs/`, where
current state, superseded decisions and project management are interleaved.

## 4. End-to-end flow as actually implemented

| Stage | Where | Reality |
|---|---|---|
| Import | `api/routers/dataset.py`, `instance/validation.py` | Eleven CSV texts validated and stored as one JSON document |
| Validation | `instance/validation.py` (984 lines) | Row-level checks on the fixed file schema |
| Normalisation | loader | Parsing into frozen dataclasses with the enums above |
| Persistence | `DepartmentDatasetRow` | Raw text blob, re-parsed when its revision changes |
| Model | `solver/variables.py`, `constraints/` | Integer start + per-room optional intervals; cumulative encoding for interchangeable rooms |
| Solve | `services/portfolio.py` | Three sequential weighted-sum solves, budget split three ways |
| Validation of result | none separate | Placement validity is assumed from the model ("correct by construction") |
| Scoring | `analysis/` | Independent recomputation of 7 criteria |
| Comparison | `analysis/ranking.py` | Exact linear decomposition + Pareto dominance flag |
| Publication | `services/publications.py` | Row pointing at a candidate; no approval, versions or rollback |
| Consumption | `api/routers/student.py` | Student sees their group's published week |

Note the gap in row 7: a solution's hard-constraint validity was never checked independently of
the model that produced it. The scores were recomputed; the feasibility was trusted.

## 5. Verdict

Extending this code would mean replacing the domain model, the persistence layer, the solver
input layer, the job execution, the API surface and every screen — that is, all of it. The
reconstruction therefore **replaces the implementation** and keeps:

- the ideas listed in §2, restated as design principles in the new architecture documents;
- the original specifications, archived under `docs/archive/original-specifications/` as
  historical input describing the Tunisian LMD context;
- the git history, where the original implementation remains available at `4c9f933` on `main`.
