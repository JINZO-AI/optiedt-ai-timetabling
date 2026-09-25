# ADR 0004 — One institution per deployment; department-scoped access

**Status:** Accepted

## Context

The initial buyer is a single institution (university, faculty, school) purchasing a licence.
Public universities in the target markets commonly require data to stay on their own
infrastructure. Inside an institution, departments share rooms but schedule and approve
their own teaching.

## Decision

- A deployment serves exactly one institution. Institution settings are a single-row table.
- Access control is scoped **within** the institution by department (a department tree:
  faculty → department). Role assignments carry an optional department scope that includes
  descendants.
- Identifiers are UUIDs and every data access goes through service functions that receive
  the caller's scope, so a tenant column and PostgreSQL row-level security can be added later
  without changing call sites.

## Alternatives considered

- **Multi-tenant SaaS now.** Rejected for the first release: adds a cross-tenant leakage
  class of defects and per-tenant upgrade coordination for no current buyer.

## Consequences

- Hosting is per institution (on-premise VM or dedicated cloud instance).
- "Tenant isolation" reduces to deployment isolation; the security review instead focuses on
  department scoping.
