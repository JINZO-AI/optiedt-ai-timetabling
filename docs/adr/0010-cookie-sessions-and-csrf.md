# ADR 0010 — Server-side sessions in HttpOnly cookies with CSRF tokens

**Status:** Accepted

## Decision

- Passwords hashed with Argon2id (`argon2-cffi`), minimum length 12, common-password denylist.
- On login the server creates a session row and sets an opaque random token in a `Secure`,
  `HttpOnly`, `SameSite=Lax` cookie; only its SHA-256 hash is stored. Idle and absolute
  expiry; logout and administrator revocation delete access immediately.
- State-changing requests must carry `X-CSRF-Token` equal to the session's CSRF token.
- Login attempts are throttled per account and per client address in the database.
- Calendar feeds use separate, revocable, per-user feed tokens scoped to that user's timetable.

## Alternatives considered

- JWT in browser storage (the original design): readable by injected scripts, not revocable.

## Consequences

- The SPA and API are served from the same origin (reverse proxy); cross-origin API use is
  not supported by default.
- Single sign-on (OIDC/SAML) is not in this release; identities are local accounts. The user
  table separates identity from credentials so an external identity provider can be added.
