# ADR 0012 — Versioned publications with base-version checks

**Status:** Accepted

## Decision

- A solution moves `draft → approved → published`. Approval freezes it; any later change
  starts a new draft derived from it.
- Publishing creates an immutable, numbered **publication** for the term (assignments copied,
  snapshot referenced). Exactly one publication per term is current.
- A draft records the publication it was derived from. Publishing is refused when that base is
  no longer current; the user rebases (re-applies the draft's differences onto the current
  publication, then re-validates).
- Restoring an old version creates a new publication with the old content.

## Consequences

- Two departments editing the same term cannot silently overwrite each other.
- "Why is today's version different from yesterday's?" is answered by the diff between
  publications plus the change log of the draft that produced the newer one.
