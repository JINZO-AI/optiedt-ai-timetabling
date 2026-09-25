# API design

The API is a JSON HTTP API under `/api/v1`, served by FastAPI. The generated OpenAPI
document (`/api/v1/openapi.json`, browsable at `/api/v1/docs` for authenticated
administrators) is the authoritative reference for every endpoint and schema; this document
states the conventions and the resource map.

## Conventions

| Topic | Convention |
|---|---|
| Naming | Plural kebab-case collections (`/room-types`), UUID identifiers, snake_case JSON fields |
| Term-scoped data | Nested under the term: `/terms/{term_id}/activities` |
| Lists | `?page=1&page_size=50` (max 500), `?sort=code,-capacity`, field filters and `?q=` text search. Response: `{"items": [...], "total": n, "page": 1, "page_size": 50}` |
| Create | `POST` collection → `201` with the resource |
| Update | `PATCH` with a `version` field; stale version → `409` |
| Delete | `DELETE` → `204`; referenced records → `409` with the referencing records named |
| Long operations | `POST` creates a job resource (`202`), polled at its URL |
| Idempotency | `POST` endpoints that create runs, publications or exceptions accept `Idempotency-Key`; a replay returns the original response |
| Errors | RFC 9457 problem details (`application/problem+json`): `type`, `title`, `status`, `detail`, `code`, `errors[]` (field, message), `request_id` |
| Authentication | Session cookie; state-changing requests need `X-CSRF-Token` |
| Authorization failures | `401` when not signed in, `403` when signed in without permission, `404` when the resource is outside the caller's scope |
| Time | ISO 8601; dates as `YYYY-MM-DD`, times as `HH:MM`; timestamps in UTC with offset |

## Resource map

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/password` |
| Institution | `GET/PATCH /institution` |
| Organisation | `/departments`, `/campuses`, `/campuses/{id}/travel-times`, `/buildings`, `/room-types`, `/room-features`, `/rooms` |
| Academic reference | `/programmes`, `/courses`, `/activity-types`, `/instructors`, `/calendar-events` |
| Users | `/users`, `/users/{id}/roles`, `/users/{id}/sessions` (revoke) |
| Terms | `/terms`, `/terms/{id}`, `/terms/{id}/time-grid`, `/terms/{id}/timing-variants` |
| Term data | `/terms/{id}/groups`, `/terms/{id}/activities`, `/terms/{id}/availability/{kind}/{resource_id}`, `/terms/{id}/rules`, `/terms/{id}/objective-profiles`, `/terms/{id}/copy-from` |
| Validation | `GET /terms/{id}/validation` (data report + pre-checks) |
| Scenarios and runs | `/terms/{id}/scenarios`, `/scenarios/{id}`, `POST /scenarios/{id}/archive`, `POST /scenarios/{id}/runs` (idempotent, `202`), `/terms/{id}/runs`, `/runs/{id}`, `/runs/{id}/events?after=`, `POST /runs/{id}/cancel`, `/runs/{id}/log`, `/runs/{id}/diagnosis` |
| Solutions | `/terms/{id}/solutions`, `/solutions/{id}`, `/solutions/{id}/timetable`, `/solutions/{id}/evaluation`, `POST /solutions/{id}/moves` (`dry_run` for preview), `/solutions/{id}/suggestions`, `/solutions/{id}/unscheduled/{session_id}` (why a session is not placed), `/solutions/{id}/locks`, `/solutions/{id}/changes`, `POST /solutions/{id}/duplicate`, `POST /solutions/{id}/rebase`, `POST /solutions/{id}/submit`, `POST /solutions/{id}/approve`, `POST /solutions/{id}/return`, `POST /solutions/{id}/publish`, `POST /solutions/{id}/reoptimize`, `POST /solutions/{id}/relaxation`, `GET /solutions/compare` |
| Publications | `/terms/{id}/publications`, `/publications/{id}`, `/publications/{id}/timetable` (weekly pattern), `/publications/{id}/occurrences?from=&to=&group_id=&instructor_id=&room_id=` (dated, exceptions applied), `/publications/{id}/diff?against=`, `POST /publications/{id}/restore`, `GET/POST /publications/{id}/exceptions`, `DELETE /exceptions/{id}` (revoke), `POST /publications/{id}/disruptions` (plan, changes nothing), `POST /publications/{id}/disruptions/apply` |
| Portal | `GET /portal/timetable` (the caller's own published timetable, dated), `GET/PUT /portal/availability` (instructors), `/portal/feed-token` |
| Public (if enabled) | `/public/terms`, `/public/timetable` |
| Imports | `POST /imports` (multipart upload), `/imports/{id}`, `PUT /imports/{id}/mapping`, `POST /imports/{id}/commit`, `DELETE /imports/{id}` |
| Exports | `GET /exports/timetable.{pdf,xlsx,csv}`, `GET /exports/report/{kind}.pdf`, `GET /ical/{token}.ics` |
| Audit | `GET /audit-events` |
| Assistant | `POST /assistant/ask` |
| Operations | `GET /health/live`, `GET /health/ready`, `GET /metrics`, `GET /system/status` |

## Timetable payload

Both solutions and publications serve timetables in one shape so every view (group,
instructor, room, course, day) is a filter on the same data:

```json
{
  "grid": {"days": [...], "periods": [...], "closed": [[0, 4], ...]},
  "sessions": [{"id": "…", "activity_id": "…", "course_code": "ALG201", "type": "TD",
                "groups": ["…"], "instructors": ["…"], "duration": 2,
                "day": 1, "period": 0, "room_id": "…", "locked": false}],
  "unscheduled": ["…"],
  "resources": {"groups": {...}, "instructors": {...}, "rooms": {...}},
  "violations": [...]
}
```

## Runs

A run request copies everything the worker needs besides the snapshot into the run's
configuration: the profiles with their tiers and weights, pinned placements (locked sessions
and, for a scenario limited to some departments, the other departments' sessions as in the
base timetable), sessions that must stay out, the stability reference and the warm-start
hint. The run is therefore reproducible after its base timetable is edited. A scenario can
have one queued or running run at a time (`409 run_active` otherwise).

`progress` on a run holds the latest event from the solver (`phase`, `profile`, `tier`,
`objective`, `bound`, `elapsed`), refreshed at most once a second; `/runs/{id}/events` returns
the full history after a given event id for incremental polling. A finished optimization
run's `result` names the candidate timetable created per profile with the solver's tier
outcomes; every candidate is evaluated independently and carries `solver_agrees`.

## Editing and publishing

`POST /solutions/{id}/moves` takes the solution `version` and a list of moves applied
together (`day`/`period` `null` takes a session out). With `dry_run` it only reports the
violations the moves would introduce or resolve and the change of every objective, rule and
tier. Without it, moves that introduce hard violations are refused with `409 move_invalid`
(the preview is in `details`) unless `force` is set; a forced draft cannot be submitted until
the violations are resolved. Locked sessions must be unlocked first (`409 locked`). Every
applied move and lock change is a numbered entry in `/solutions/{id}/changes` with before,
after, author, reason and affected resources, and bumps the solution `version`.

Only `draft` solutions are editable; `duplicate` makes an editable copy of any timetable and
records it as derived from the publication it came from. `submit` → `approve` (or `return`
with a note) → `publish` follow the approval rule of `docs/product/requirements.md` §2;
`publish` refuses a draft whose base publication is no longer current (`409 rebase_needed`)
or that no longer fits the term's current data (`409 data_changed`); `rebase` creates a new
draft on the current data and publication that keeps the draft's own changes.
