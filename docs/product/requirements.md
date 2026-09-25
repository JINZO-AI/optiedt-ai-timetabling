# Product requirements — OptiEDT

OptiEDT is an academic scheduling and optimization platform. It lets an institution build,
validate, optimize, compare, publish and continuously manage the weekly teaching timetable of
each term under its own rules, and gives staff and students a clean view of the result.

This document defines the product that is built. Every requirement here has an
implementation and tests; anything not implemented is listed in
[`known-limitations.md`](known-limitations.md) instead.

## 1. Users and roles

| Role | Who | Purpose |
|---|---|---|
| System administrator | IT staff running the deployment | Everything, including system status and all settings |
| Institution administrator | Registrar / academic affairs | Institution settings, campuses, buildings, rooms, departments, terms and calendars, user accounts |
| Scheduling officer | Person who builds timetables | Academic data, availability, rules, scenarios, runs, editing, exceptions, imports, exports, publication |
| Department head | Head of a department or faculty | Reviews and approves timetables for their department; manages availability of their staff |
| Instructor | Teaching staff | Own published timetable, own availability and preferences, calendar feed |
| Student | Enrolled student (optional accounts) | Published timetable of their group(s), calendar feed |
| Viewer | Read-only staff (e.g. facilities, deanery) | Published timetables and reference data |
| Public | Unauthenticated | Published timetables by group, room or instructor — only if the institution enables it |

A user may hold several roles. Every role except System administrator and Institution
administrator can be **scoped to a department**; the scope includes all descendant
departments (a faculty scope covers its departments).

## 2. Permissions

Authorization is enforced on the server for every request. The interface hides what a role
cannot do, but hiding is never the control.

| Permission | Sys admin | Inst admin | Officer | Dept head | Instructor | Student | Viewer |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Read reference data (rooms, departments, courses, instructors) | ✓ | ✓ | ✓ | ✓ | – | – | ✓ |
| Manage institution settings, campuses, buildings, rooms, room types/features | ✓ | ✓ | – | – | – | – | – |
| Manage departments, programmes, activity types | ✓ | ✓ | – | – | – | – | – |
| Manage terms, time grids, holidays, timing variants | ✓ | ✓ | – | – | – | – | – |
| Manage instructors, courses | ✓ | ✓ | ✓ (scope) | – | – | – | – |
| Manage student groups and activities of a term | ✓ | – | ✓ (scope) | – | – | – | – |
| Manage availability of any instructor / group / room | ✓ | – | ✓ (scope) | ✓ (own dept instructors) | – | – | – |
| Declare own availability and preferences | – | – | – | – | ✓ (while term open for declarations) | – | – |
| Manage constraint rules and objective profiles | ✓ | – | ✓ | – | – | – | – |
| Create scenarios, start and cancel solver runs | ✓ | – | ✓ (scope) | – | – | – | – |
| Read drafts, candidates, run reports | ✓ | ✓ | ✓ | ✓ | – | – | – |
| Edit drafts (move, lock, repair, rebase) | ✓ | – | ✓ (sessions in scope) | – | – | – | – |
| Approve a draft | ✓ | – | – | ✓ (changes within scope) | – | – | – |
| Publish, restore a publication | ✓ | – | ✓ | – | – | – | – |
| Date-level exceptions on the published timetable | ✓ | – | ✓ (scope) | – | – | – | – |
| Read published timetables (all) | ✓ | ✓ | ✓ | ✓ | – | – | ✓ |
| Read own published timetable | – | – | – | – | ✓ | ✓ | – |
| Imports | ✓ | ✓ | ✓ | – | – | – | – |
| Exports (any published or draft timetable readable by the user) | ✓ | ✓ | ✓ | ✓ | own | own | ✓ |
| Manage users and role assignments | ✓ | ✓ | – | – | – | – | – |
| Read audit log | ✓ | ✓ | ✓ (scope) | ✓ (scope) | – | – | – |
| System status | ✓ | – | – | – | – | – | – |
| Use the assistant (if enabled) | ✓ | ✓ | ✓ | ✓ | – | – | – |

"Scope" means the entity belongs to a department inside the user's scope (instructor and
course by their department, activity by its course, student group by its programme).
Rooms are institution-wide resources.

Approval rule: a department head may approve a draft only if every session that differs from
the draft's base publication belongs to their scope. The first publication of a term needs an
approver with institution-wide scope. The institution may disable the approval step, in which
case a valid draft can be published directly by a scheduling officer.

## 3. Core workflows

### 3.1 Set up the institution (once)
Institution name, timezone, languages, week start, date and time formats; campuses and travel
times between them; buildings; room types (e.g. lecture hall, classroom, computer lab) and room
features (projector, computers, accessibility); rooms with capacity, type, features and owning
department; departments as a tree; programmes; activity types (e.g. Lecture / CM, Tutorial / TD,
Lab / TP) with their default room type; users and roles.

### 3.2 Prepare a term
1. Create the term (dates, teaching weekdays such as Monday–Saturday or Sunday–Thursday).
2. Define the period grid: any number of periods with their times and whether a session may
   run across into the next period (no running across lunch); close individual slots
   (e.g. Saturday afternoon); override times per weekday (e.g. Friday afternoon); add timing
   variants for date ranges (e.g. Ramadan hours); holidays and closures by date.
3. Build student groups: cohorts with their partitions (tutorial groups, lab subgroups,
   language options) and sizes. Can be copied from a previous term.
4. Define activities: course, activity type, student groups, instructors (co-teaching allowed),
   duration in periods, sessions per week, delivery mode, room type, required features,
   capacity, campus or building restriction, allowed/preferred/avoided rooms, time preferences,
   fixed placements, whether sessions must be on different days.
5. Collect availability: instructors declare unavailable / undesirable / preferred periods
   during a declaration window; officers can edit any grid. Rooms and groups can be blocked.
6. Configure rules (section 4).
7. **Validate:** a data validation report lists errors (block solving) and warnings, with links
   to the offending records, followed by feasibility pre-checks.

### 3.3 Generate candidates
Create a scenario (name, objective profiles to run, scope such as one department with
everything else held fixed, optional reference solution for stability, solving mode and time
budget). Start a run. The run is queued, then shows live progress: phase, current priority
tier, incumbent quality per tier, unscheduled sessions. The user can leave and return, or
cancel. The run produces one candidate per selected profile.

A candidate is **complete** (every session placed, no hard violation) or **incomplete** (best
partial timetable; each unscheduled session comes with the reasons it could not be placed and,
on request, suggested minimal data changes).

### 3.4 Inspect and edit
Open a candidate in the timetable workspace: week grid by student group, instructor, room,
course, or a day view across rooms; filters and search ("every session of Dr. X",
"everything in Room B", "conflicts of group G2"). Selecting a session shows its details,
constraints and quality contributions.

Moving a session (drag or dialog) is validated immediately: hard conflicts with named
resources, soft-quality changes per objective, affected resources. The user confirms or
cancels. "Suggest placements" ranks every feasible option for the session with its effect on
each objective, and lists impossible options with their reasons. Sessions can be locked. Every
edit is logged with author, time, before/after and optional reason. "Re-optimize from here"
starts a run seeded with the draft, keeping locked sessions fixed.

### 3.5 Compare
Select two or more candidates. The comparison shows, per objective and in natural units, each
candidate's value and the difference; which candidate is better on which objective; Pareto
dominance; and the list of sessions placed differently, grouped by the resources affected.

### 3.6 Approve and publish
A complete, valid draft is submitted for approval; an approver approves (with note) or returns
it. Publishing an approved solution creates a numbered, immutable publication that becomes the
term's current timetable. Earlier versions stay readable; any version can be restored as a new
version; any two versions can be diffed.

### 3.7 Operate during the term
- **Disruptions:** choose a room, instructor or group and a date range; the system lists affected
  occurrences and proposes the least disruptive valid alternative for each (another room at the
  same time first). Applying creates date-level exceptions visible immediately in dated views
  and calendar feeds.
- **Structural changes:** edit data (e.g. a room is closed for the rest of the term), rebase the
  current publication onto the new data to see violations, run a repair that minimizes changes,
  review the diff, approve and publish a new version.

### 3.8 Consume
Instructors and students see the published timetable only: today, this week, any week, with
room and instructor details and date-level changes; print or download PDF; subscribe to an
iCalendar feed. If enabled, a public page lets anyone browse published timetables by group,
instructor or room.

### 3.9 Exports and reports
PDF (weekly grids per group, instructor, room; booklets per department; conflict report; run
report; change report), XLSX, CSV, iCalendar.

### 3.10 Assistant (optional)
Natural-language questions answered from application data through read-only queries, with the
underlying data shown. Disabled by default.

## 4. Constraints

**Structural requirements** (always hard): each session placed once; within one day; never
across a non-joinable period boundary; only in open slots; instructor, student group and room
never double-booked; room type, features and capacity satisfied; unavailability of
instructors, groups and rooms respected; campus/building restrictions and allowed rooms
respected; fixed placements respected; sessions of one activity on different days when
required.

**Configurable rules** (each instance hard or soft, with priority tier and weight, targeted at
chosen instructors, groups, activities or everyone):

| Rule | Parameters |
|---|---|
| Maximum periods per day | limit |
| Maximum consecutive periods | limit |
| Maximum teaching days per week | limit |
| Break within a window (e.g. lunch) | window periods, minimum free periods |
| Avoid periods | set of slots |
| Earliest start / latest end per day | period |
| Minimum days between sessions of an activity | days |
| Activities not at the same time | activities |
| Activities at the same time | activities |
| Activities on the same day / different days | activities |
| Activity A before activity B in the week | activities |
| Consecutive activities (B immediately after A, same day) | activities |
| Campus travel time between consecutive sessions | minutes per campus pair (from institution data) |

**Built-in soft objectives** (tier and weight set by the objective profile): student idle
periods; instructor idle periods; instructor preferences (undesirable and preferred periods);
institution-wide undesirable periods (e.g. late evening) weighted by students affected; room
capacity fit; room stability across an activity's sessions; same start time across an
activity's sessions; instructor teaching days; daily load balance for students; stability
relative to a reference solution.

## 5. Non-functional requirements

| Area | Requirement |
|---|---|
| Correctness | No solver result is stored as valid without independent validation. No incomplete or invalid solution can be approved or published. |
| Performance | Medium institution (≈1,200 sessions) complete timetable in under 2 minutes on 4 cores; interactive move validation under 200 ms; timetable view render under 1 s. Measured in `docs/benchmarks/`. |
| Reliability | Worker crash or restart never leaves a run in a non-terminal state for longer than the lease timeout. |
| Security | See `docs/operations/security.md`: Argon2id, HttpOnly cookie sessions, CSRF tokens, login throttling, server-side authorization, audit log, security headers, upload limits. |
| Auditability | Every data change, run, approval, publication, restore and exception is recorded with actor, time, before/after and reason. |
| Reproducibility | Every run records snapshot hash, configuration, seed, versions; reproducible mode re-derives the same result. |
| Localization | English, French, Arabic (right-to-left); configurable timezone, weekdays, date and time formats. |
| Operability | Health and readiness endpoints, Prometheus metrics, structured JSON logs, documented backup and restore. |
| Deployability | Docker Compose deployment with TLS reverse proxy, migrations, worker, backups. |
