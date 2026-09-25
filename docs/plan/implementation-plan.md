# Implementation plan

Milestones are committed separately so the history shows the architecture being built.
Each milestone ends with its tests passing.

| # | Milestone | Content |
|---|---|---|
| M0 | Design | Audit, research, ADRs, requirements, domain, optimization, API and frontend designs |
| M1 | Foundation | New repository layout; backend package, settings, logging, error model, database session, Alembic, test harness against PostgreSQL; removal of the internship implementation |
| M2 | Identity and audit | Users, Argon2id, cookie sessions, CSRF, throttling, roles and scopes, permission checks, append-only audit log |
| M3 | Reference data | Institution, departments, campuses, buildings, room types, features, rooms, programmes, courses, activity types, instructors, calendar events — CRUD with validation, scope rules and audit |
| M4 | Term data | Terms, time grids, timing variants, student groups, activities, availability grids, rules, objective profiles, copy-from-term |
| M5 | Snapshot and validation | Snapshot compiler, problem model, conflict atoms, data validation report |
| M6 | Evaluation | Independent validator, metrics, placement explanations, move evaluation, suggestions |
| M7 | Solver | Domains, pre-checks, CP-SAT model, rules, objectives, tiered solving, warm start, cancellation, progress; solver and property tests |
| M8 | Runs and worker | Scenarios, run queue with leases, worker process, events, candidates, relaxation runs, crash recovery |
| M9 | Solutions and publication | Drafts, moves, locks, change log, compare, submit/approve/return, publish, versions, diff, restore, rebase, repair, exceptions and disruptions |
| M10 | Demo institution and benchmarks | Realistic seed institution; instance generator (small → stress); benchmark runner and recorded results |
| M11 | Frontend | Shell, auth, data screens, term setup, rules, validation, runs, workspace, compare, publication, portal, administration, i18n (en/fr/ar) |
| M12 | Imports and exports | Upload, mapping, validation preview, commit; PDF, XLSX, CSV, iCalendar |
| M13 | Assistant | Tool-grounded queries, providers, degradation |
| M14 | Operations | Metrics, readiness, structured logs, Dockerfiles, Compose, Caddy, backups, CI |
| M15 | Verification | End-to-end tests, security review and fixes, performance review, UX review, documentation, final audit |

Examination timetabling is decided after M9 against one criterion: it ships only if it can be
built to the same standard (persistent, validated, published, exported); otherwise it is
recorded as excluded.
