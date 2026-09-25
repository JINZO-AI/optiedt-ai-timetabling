# Frontend information architecture

## Principles

- **The timetable is the main surface.** Everything else prepares, explains or publishes it.
- **Dense and quiet.** Tables, grids and short labels; colour for meaning (conflict, locked,
  changed, activity type), not decoration.
- **Every figure is explained on demand.** Metrics open their breakdown; conflicts name the
  resources and sessions involved.
- **One term at a time.** The term selector in the top bar sets the working context.
- **Staff and portal are different products.** Instructors and students see a simple published
  timetable, never the scheduling workspace.

## Staff navigation

| Section | Screens |
|---|---|
| Overview | Term dashboard: readiness checklist (data, validation, availability declarations), latest runs, candidates awaiting review, current publication, open disruptions |
| Data | Rooms (with campuses, buildings, types, features), Instructors, Courses, Programmes, Student groups (tree editor), Activities (teaching load table), Availability (grid editor per instructor/group/room), Import |
| Term setup | Term details, Time grid (periods, weekdays, closed slots, per-day times, slot penalties), Timing variants, Holidays and closures |
| Rules | Constraint rules (catalogue-driven forms), Objective profiles (tier board) |
| Validation | Data errors and warnings with links; feasibility pre-checks |
| Scheduling | Scenarios, Run detail (live progress, tier timeline, log, result), Candidates list |
| Workspace | Timetable of a solution: view switcher (group / instructor / room / course / day), filters and search, grid with conflicts, unscheduled tray, session inspector, move dialog and suggestions, lock toggles, metrics panel, change history |
| Compare | Metrics side by side, dominance, changed sessions grouped by resource |
| Publication | Approval queue, publication history, version diff, restore, exceptions and disruption assistant |
| Reports | Exports and printable reports |
| Administration | Institution settings, Users and roles, Audit log, System status |

## Portal (instructors and students)

- **My timetable:** week view with previous/next week and date picker, today list, session
  details (room with building, instructors, groups), date-level changes highlighted.
- **Availability** (instructors, while the declaration window is open): weekly grid with four
  states.
- **Calendar subscription:** personal iCalendar link with regenerate.
- **Print / PDF.**

## Timetable grid behaviour

- Columns are days, rows are periods; a session spans its duration.
- Parallel sessions in one cell (e.g. a group view showing subgroup labs) are laid out side by
  side within the cell.
- Conflicts: red outline and icon; hovering or selecting lists the conflicting sessions.
- Locked sessions show a lock; changed sessions (relative to a base) show a change marker.
- Drag a session to a cell: the cell highlights green (valid), amber (valid, worse quality),
  red (invalid) while hovering; dropping opens the confirmation with the full evaluation.
- Keyboard: arrow keys move the selection; Enter opens the inspector; M opens the move dialog.
- Right-to-left languages mirror the grid (first day on the right).

## Internationalisation

English, French, Arabic. Labels from translation catalogues; institution data (room names,
course titles) shown as entered. Dates, times and numbers formatted with the institution's
locale settings and the user's language.
