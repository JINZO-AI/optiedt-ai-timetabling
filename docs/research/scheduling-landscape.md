# Research: academic scheduling systems and optimization methods

Purpose: decide what a credible institutional scheduling product must do, and which
optimization techniques are worth their complexity. Written before the architecture was
chosen; the decisions it led to are in `docs/adr/`.

## 1. The problem family

Educational timetabling splits into problem classes that share techniques but not models:

| Class | Unit placed | Conflict source | Reference benchmark |
|---|---|---|---|
| Curriculum-based course timetabling | lectures of courses | curricula (fixed cohorts) | ITC-2007 track 3 |
| Post-enrolment course timetabling | events | individual student enrolments | ITC-2007 track 2 |
| Real-world university course timetabling | classes with time/room options | student sectioning + distribution constraints | ITC-2019 |
| High-school timetabling | lessons | classes, divisions, teachers | XHSTT |
| Examination timetabling | exams, possibly multi-room | individual students | ITC-2007 track 1 |

Programme-based universities (the LMD system in Tunisia, most of francophone Africa and
Europe, business and engineering schools, secondary schools) schedule **cohort groups**:
conflicts come from group membership, not from individual course choices. US-style
institutions with free elective choice need **student sectioning** — assigning individual
students to sections — which is a separate optimization problem (UniTime's main strength).

### ITC-2019 as a map of real requirements

ITC-2019 was built from real data of ten universities. Its model is the best public
catalogue of what institutions actually ask for:

- classes with a list of allowed (time, penalty) and (room, penalty) options;
- times as day and week bit patterns with start and length;
- room unavailability and travel times between rooms;
- **distribution constraints**, hard or soft, of nineteen types: `SameStart`, `SameTime`,
  `DifferentTime`, `SameDays`, `DifferentDays`, `SameWeeks`, `DifferentWeeks`, `Overlap`,
  `NotOverlap`, `SameRoom`, `DifferentRoom`, `SameAttendees`, `Precedence`, `WorkDay(S)`,
  `MinGap(G)`, `MaxDays(D)`, `MaxDayLoad(S)`, `MaxBreaks(R,S)`, `MaxBlock(M,S)`;
- student sectioning with course configurations and parent-child class links;
- a weighted objective over time, room, distribution and student-conflict penalties.

The winning approaches were a fix-and-optimize MIP matheuristic (1st), a MIP with strong
preprocessing (2nd) and simulated annealing (3rd). Exact solvers win when the model is
reduced aggressively; local search wins on raw scale.

Sources: [ITC 2019 results](https://www.itc2019.org/results),
[Real-world university course timetabling at ITC 2019 (J. Scheduling)](https://link.springer.com/article/10.1007/s10951-023-00801-w),
[Winning ITC 2019 (DTU)](https://orbit.dtu.dk/en/publications/winning-the-international-timetabling-competition-2019/),
[A MIP formulation of the ITC 2019 problem](https://backend.orbit.dtu.dk/ws/files/221992887/A_MIP_Formulation_of_the_International_Timetabling_Competition_2019_Problem.pdf).

## 2. Existing products

### UniTime (open source, Purdue University)

The most complete open system: course timetabling, student sectioning, examinations, event
management. The solver (`cpsolver`) is an **iterative forward search**: a local search over
feasible but possibly incomplete assignments, with conflict-based statistics guiding which
variable to reassign. Two properties matter commercially:

- it can start, stop and continue from any partial solution, which makes it naturally
  interactive;
- it solves the **minimal perturbation problem** — re-solving after data changes while staying
  close to the previous solution — which is what schedulers need after publication.

Unassigned classes are a normal, visible state in UniTime, reported with the conflicts that
prevent assignment. That is the behaviour users trust: the system shows what it could not do
instead of failing as a whole.

Sources: [UniTime cpsolver](https://github.com/UniTime/cpsolver),
[Minimal Perturbation Problem in Course Timetabling (PATAT 2005)](https://www.unitime.org/papers/patat05.pdf),
[University Course Timetabling & Student Sectioning System (ICAPS 2007)](https://www.unitime.org/papers/icaps07.pdf).

### Commercial systems

Scientia (Syllabus Plus), CELCAT, TimeEdit, Infosilem, Semestry, Ad Astra, Coursedog, Kuali,
Untis and aSc Timetables. Recurring capabilities across them:

1. **Interactive editing with live conflict display** is the most valued capability in
   reviews — planners spend more time adjusting than generating.
2. Separate exam timetabling workflows (Semestry, TimeEdit, Scientia).
3. Publication to staff and students, including calendar feeds.
4. Room inventories with features and capacities shared across departments.
5. Recurring meeting patterns and term calendars with holidays.
6. Integration with student information systems (imports/exports).

Weak spots repeatedly cited, including by the original OptiEDT specification: automatic
generation whose compromises are not explained, heavy implementation and training cost,
and poor fit for local rules (lunar calendars, shortened working days, six-day weeks, the
CM/TD/TP hierarchy). Pricing is quote-based and bundled with implementation services.

Sources: [CELCAT](https://celcat.com/), comparison listings such as
[gitnux higher-education scheduling software](https://gitnux.org/best/higher-education-course-scheduling-software/).

## 3. Optimization methods evaluated

### CP-SAT (OR-Tools)

A lazy-clause-generation solver combining SAT search, constraint propagation (including
`NoOverlap` and `Cumulative` on interval variables), linear relaxations and a portfolio of
parallel workers, several of which run **large neighbourhood search** internally. It proves
optimality and infeasibility, accepts solution hints, reports incumbent solutions through
callbacks, can be stopped cooperatively, and supports assumptions with
`SufficientAssumptionsForInfeasibility` (a heuristic, not necessarily minimal, core).
Current stable release: 9.15 (January 2026).

Measured during this research on the original reference instance (218 sessions, 20 rooms,
28 open slots), with a time-indexed boolean formulation for time and optional intervals for
rooms: complete feasible timetable proven in **1.8 s**, student idle periods minimised to a
proven optimum of 0 in **3.9 s** (4 workers). The original model spent 50 s on one weighted
profile without proving optimality.

Sources: [CP-SAT documentation](https://developers.google.com/optimization/cp/cp_solver),
[The CP-SAT Primer](https://d-krupke.github.io/cpsat-primer/),
[CP-SAT Primer — LNS](https://d-krupke.github.io/cpsat-primer/lns.html).

### Mixed integer programming

Competitive on ITC-2019 after heavy preprocessing, but the best solvers are commercial
(Gurobi, CPLEX) and licence costs would fall on each institution. Open MIP solvers (HiGHS,
CBC) are markedly weaker on large combinatorial scheduling models. CP-SAT already embeds
LP relaxations. **Rejected as the primary engine** on licensing and performance grounds.

### Local search and metaheuristics (IFS, simulated annealing, tabu, Timefold)

Scale well and handle soft constraints gracefully. Timefold (formerly OptaPlanner) offers
incremental score calculation with "constraint streams" and is widely deployed for school
timetabling. Weaknesses for this product: no proofs of infeasibility or optimality, so
diagnosis must be heuristic; Java-centric (its Python binding is not a first-class target);
quality depends on hand-tuned move selectors.

### Hybrids and LNS

The state of the art on large real instances combines an exact solver on sub-problems with
a neighbourhood loop (fix-and-optimize won ITC-2019). CP-SAT already runs LNS internally; a
problem-specific outer LNS (free one department, one day, or one resource's sessions; fix
the rest; re-solve) is the natural extension when a monolithic model is too large.

### Decision

CP-SAT as the engine, with: a constructive warm start; tiered (lexicographic) objectives;
elastic placement so a run always returns its best partial timetable; problem-specific LNS
reserved for sizes where benchmarks show the monolithic model stalls.

## 4. Multi-objective handling

A weighted sum over incommensurable criteria (student gaps, preference violations, room
fit) forces users to pick weights whose effect they cannot predict. Lexicographic
optimization — optimize the most important objective, constrain it to its optimum, then the
next — matches how administrators state priorities ("instructor availability wishes first,
then student comfort, then rooms") and is standard practice with CP-SAT: solve, fix the
achieved value, hint the solution, move to the next level.

Pure lexicographic order can be too rigid, so objectives are grouped into **priority tiers**,
weighted within a tier and ordered between tiers. Candidates are compared per objective in
natural units, and Pareto dominance between candidates is reported; no composite score is
shown. Sources: [Lexicographic optimization](https://en.wikipedia.org/wiki/Lexicographic_optimization),
[OR-Tools discussion on blocking constraints for multiple objectives](https://github.com/google/or-tools/discussions/4183).

## 5. Infeasibility diagnosis

Formal tools: minimal unsatisfiable subsets (MUS, a minimal explanation) and minimal
correction sets (MCS, a minimal set of constraints whose removal restores feasibility), which
are hitting-set duals. For an administrator the MCS is the actionable object: "if these two
things change, a timetable exists".

Assumption-based cores in CP-SAT are cheap to request but the original project measured
that enforcement literals on scheduling globals disable presolve reasoning (0.0 s proof
became `UNKNOWN` after 240 s). The approach chosen instead is **elastic relaxation**: hard
requirements get explicit, costed relaxation variables (a session may stay unscheduled; an
instructor may be used in an unavailable period at a cost), and minimizing total relaxation
cost yields an MCS-like answer with a partial timetable, while presolve keeps working on the
remaining hard constraints. Deletion-based narrowing and per-session blocking analysis then
explain each remaining conflict in terms of named resources.

Sources: [Algorithms for computing MUS](https://www.researchgate.net/publication/220532549_Algorithms_for_Computing_Minimal_Unsatisfiable_Subsets_of_Constraints),
[Using MCS to compute MUS](https://link.springer.com/chapter/10.1007/978-3-319-21668-3_5),
[CPMpy: unsat cores with assumptions](https://cpmpy.readthedocs.io/en/stable/unsat_core_extraction.html).

## 6. Incremental scheduling and repair

Research on the minimal perturbation problem models repair as optimization with a distance
term to the previous solution (UniTime's MPP, integer programming and MaxSAT formulations,
bi-objective perturbation vs. quality). In a CP model the distance term is linear in the
placement variables, so repair is the ordinary model with a **stability objective in the
highest tier**, locked sessions, and the previous solution as hint.

Sources: [Integer programming for minimal perturbation problems (Annals of OR)](https://link.springer.com/article/10.1007/s10479-015-2094-z),
[Minimal perturbation in university timetabling with MaxSAT (CPAIOR 2020)](https://link.springer.com/chapter/10.1007/978-3-030-58942-4_21),
[Quality recovering of university timetables (EJOR)](https://www.sciencedirect.com/science/article/abs/pii/S0377221719300451).

## 7. Examination timetabling

ITC-2007 track 1 captures the practical core: per-student conflicts, period durations,
multi-exam rooms with capacity, period spread, front-loading of large exams, room and
period penalties. It shares infrastructure with course timetabling (jobs, validation,
publication) but not its model: conflicts are per student and rooms are shared by several
exams. It is therefore a separate bounded module. Sources:
[ITC 2007 exam track (Timefold docs)](https://docs.timefold.ai/timefold-solver/0.8.x/use-cases-and-examples/exam-timetabling/exam-timetabling),
[Survey of exam timetabling methodologies](https://www.graham-kendall.com/papers/siewetal2024a.pdf).

## 8. What buyers need, what differentiates, what to leave out

**Must have:** a real relational data model with CRUD and imports; shared rooms across
departments; configurable week structure; hard/soft constraint configuration; asynchronous
generation with progress; clear handling of unplaceable sessions; interactive editing with
live conflicts; versioned publication; staff and student views; PDF/XLSX/iCal exports;
role-based access; audit trail.

**Differentiators within reach:** explanation of *why* a session cannot go somewhere, with
ranked alternatives; minimal-change repair after disruptions, including date-level
relocation; per-objective comparison of candidates instead of a score; local calendar
realities (six-day weeks, Friday timings, Ramadan timing variants, lunar holidays) as
configuration; trilingual interface (English, French, Arabic with right-to-left layout).

**Deliberately out of scope for this release:** US-style student sectioning (individual
enrolment optimization); automatic instructor assignment (who teaches what); alternating-week
patterns in the weekly solver; natural-language constraint entry; mobile applications.
Each is recorded in `docs/product/known-limitations.md` with the reason.

**Impressive but commercially useless:** an LLM that "generates timetables"; a single AI
quality score; machine-learned weights from a handful of comparisons (the original FR-21);
microservices for a workload of a few solves per day.

## 9. Data-handling lessons from the original project

- Pre-checks must say which kind they are (necessary, sufficient) and name resources.
- An `UNKNOWN` status is not evidence of feasibility or infeasibility.
- Scores or objective values reported by the solver are not trusted; they are recomputed.
- Wall-clock time limits make parallel CP-SAT runs non-reproducible; deterministic time
  limits and recorded seeds are required when reproducibility is claimed.
