# The API

**33 endpoints under `/api`.** This list was read from the live OpenAPI schema
(`GET /api/openapi.json`) on 2026-08-13, not transcribed from source — so it is what the application
actually serves. Regenerate it the same way rather than editing by hand:

```bash
curl -s http://localhost:8000/api/openapi.json | python -c "import sys,json;[print(m.upper(),p) for p,o in json.load(sys.stdin)['paths'].items() for m in o if m in ('get','post','put','delete')]"
```

Interactive docs: **`/api/docs`** (Swagger UI) while the API is running.

---

## Conventions that hold everywhere

- **Bearer tokens.** `POST /api/auth/token` is form-encoded with snake_case fields — the OAuth2
  password flow's shape, so FastAPI's own `/api/docs` can sign in too. Every other endpoint takes
  `Authorization: Bearer …` and speaks camelCase JSON.
- **RBAC is checked per endpoint**, in the router (FR-11). ⚠️ The interface hides controls a role
  cannot use, but hiding is not authorisation. If the client and the API disagree, the API is right.
- **Long work answers 202 and is polled.** A solve takes minutes; no HTTP request is held open for one
  (ADR-005).
- **A refused import is a 200.** `POST /api/dataset` answers `accepted: false` with the report, because
  the report is the requirement's output — an error status would lose it.
- **`DELETE` may answer 204 with no body.** `DELETE /accounts/{u}` does; `DELETE /calendar` returns the
  calendar it restored.

---

## Authentication

| | |
|---|---|
| `POST /api/auth/token` | Sign in; returns a bearer token |
| `GET /api/auth/me` | The signed-in account |

⚠️ The refusal message is identical for an unknown username and a wrong password. Telling them apart
tells an attacker which accounts exist.

## Reference data

| | |
|---|---|
| `GET /api/instance` | The reference instance — slots, rooms, groups, teachers, courses, the constraint catalogue |

## Generation and candidates

| | |
|---|---|
| `POST /api/runs` | Launch a generation; returns immediately with a run id |
| `GET /api/runs` | Runs, newest first |
| `GET /api/runs/{run_id}` | One run, polled — state, pre-analysis, candidates, diagnosis, weights, timings |
| `GET /api/runs/{run_id}/candidates` | Candidates of a run, best first |
| `GET /api/runs/{run_id}/candidates/{candidate_id}` | One candidate with its placements and sub-scores |
| `POST /api/runs/{run_id}/candidates/{candidate_id}/publish` | Publish a candidate; returns it with its full trace |
| `POST /api/runs/{run_id}/candidates/{candidate_id}/regenerate` | Accept a recommendation; launches a **new run through the same solver** |

⚠️ **Regeneration never edits a candidate** (invariant 6). It changes one input — a weight, a lock or
an exclusion — and starts a new run, so the twelve hard rules hold in the result for the same reason
they held before.

## Analysis

| | |
|---|---|
| `GET /api/runs/{run_id}/comparison` | FR-15 — the difference between two candidates, criterion by criterion |
| `GET /api/runs/{run_id}/dominance` | FR-17 — candidates another improves on across the board |
| `GET /api/runs/{run_id}/recommendation` | FR-16 — the candidate put forward, and the rule that chose it |

## Examinations — FR-20

| | |
|---|---|
| `POST /api/examinations` | Generate the timetable of an examination session |
| `GET /api/examinations` | Examination runs, newest first |
| `GET /api/examinations/{run_id}` | One examination run, polled |

⚠️ Examinations are **derived** from the instance, never supplied (C-23, ADR-013). ⚠️ Examination runs
are held **in memory** and do not survive a process restart.

## Availability — FR-2

| | |
|---|---|
| `GET /api/teachers/{teacher_id}/availability` | A teacher's declaration, generated rows included |
| `PUT /api/teachers/{teacher_id}/availability` | Replace a teacher's declaration |

⚠️ A teacher may read and write **their own** grid only; the API refuses another teacher's with 403
regardless of the path. The person in charge has read and write on all data (SRS Table 2).

## Publication — FR-19

| | |
|---|---|
| `GET /api/publications` | Published timetables, newest first, each with its trace |

## Department data — FR-1

| | |
|---|---|
| `GET /api/dataset` | The data in force, and where it came from |
| `POST /api/dataset` | Replace it from a set of files |
| `DELETE /api/dataset` | Withdraw the import; the reference files govern again |

⚠️ Eleven files, not the thirteen in `data/instance/`. `constraint_catalogue.csv` is the software's own
rule catalogue and is refused (invariant 7); `students.csv` belongs to the examination model. ⚠️ A
replacement that would orphan an FR-2 declaration or an FR-9 closure is **refused**, never allowed to
delete one (ADR-012).

## Administration — FR-9, FR-11

| | |
|---|---|
| `GET` / `PUT` / `DELETE /api/calendar` | The calendar in force; state it; withdraw every edit |
| `GET` / `POST /api/accounts`, `DELETE /api/accounts/{username}` | Accounts |

⚠️ The calendar is **layered over a pristine instance** at run assembly, so a closure can be withdrawn —
`DELETE` restores the 13 shipped CSVs. Calendar rules are configuration, never CP-SAT constraints
(ADR-003, invariant 7).

## The student's surface

| | |
|---|---|
| `GET /api/me/timetable` | The published timetable of the signed-in student's group |

⚠️ This exists because a run carries **every** group's drafts. A student is refused the run, candidate,
comparison, assistant and availability endpoints and is given their own published week, filtered on the
server.

## The assistant — FR-22, FR-24, FR-25

| | |
|---|---|
| `GET /api/assistant/runs/{run_id}/candidates/{candidate_id}/explanation` | Explain a candidate's quality |
| `POST /api/assistant/runs/{run_id}/question` | Answer a question about a run |
| `GET /api/assistant/runs/{run_id}/report` | A readable report on a run |

⚠️ **Registered unconditionally, even when the service is off.** Gating the routes on
`assistant_enabled` would make the interface 404 rather than fall back — and the fallback *is* the
specified behaviour (invariant 5). They answer 200 with the computed form and a `fallbackReason`.

## Meta

| | |
|---|---|
| `GET /api/health` | Liveness — `{"status": "ok"}` |
| `GET /api/openapi.json`, `/api/docs` | Schema and Swagger UI |
