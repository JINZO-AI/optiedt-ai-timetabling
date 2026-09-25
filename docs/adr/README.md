# Architecture decision records

Each record states one decision, the alternatives that were weighed, and what the decision
costs. Records are immutable once accepted; a changed decision gets a new record that
supersedes the old one.

| # | Decision | Status |
|---|---|---|
| [0001](0001-rebuild-instead-of-extend.md) | Rebuild the product instead of extending the internship code | Accepted |
| [0002](0002-modular-monolith-and-solver-worker.md) | Python modular monolith with a separate solver worker process | Accepted |
| [0003](0003-postgresql-system-of-record-and-queue.md) | PostgreSQL as system of record and as the job queue | Accepted |
| [0004](0004-single-tenant-deployment.md) | One institution per deployment; department-scoped access | Accepted |
| [0005](0005-cp-sat-engine-and-formulation.md) | CP-SAT engine with a time-indexed formulation | Accepted |
| [0006](0006-tiered-lexicographic-objectives.md) | Tiered lexicographic objectives; no composite score | Accepted |
| [0007](0007-elastic-placement-and-diagnosis.md) | Elastic placement and relaxation-based infeasibility diagnosis | Accepted |
| [0008](0008-immutable-problem-snapshots.md) | Immutable problem snapshots as the basis of every result | Accepted |
| [0009](0009-independent-validation.md) | Independent validator and metrics, separate from the solver | Accepted |
| [0010](0010-cookie-sessions-and-csrf.md) | Server-side sessions in HttpOnly cookies with CSRF tokens | Accepted |
| [0011](0011-student-groups-with-partitions.md) | Student groups as a tree with partitions and conflict atoms | Accepted |
| [0012](0012-publication-versions-and-rebase.md) | Versioned publications with base-version checks | Accepted |
| [0013](0013-date-level-exceptions.md) | Date-level exceptions on published timetables | Accepted |
| [0014](0014-tool-grounded-assistant.md) | Optional, tool-grounded, read-only assistant | Accepted |
| [0015](0015-frontend-stack.md) | React SPA, own design system, i18n with right-to-left support | Accepted |
| [0016](0016-server-side-documents.md) | Server-side PDF (WeasyPrint), XLSX, and iCalendar feeds | Accepted |
| [0017](0017-weekly-recurring-model.md) | Weekly-recurring timetables; no alternating-week patterns in v1 | Accepted |
| [0018](0018-reproducible-solving-modes.md) | Two solving modes: fastest (default) and reproducible | Accepted (revised) |
