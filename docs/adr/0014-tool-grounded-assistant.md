# ADR 0014 — Optional, tool-grounded, read-only assistant

**Status:** Accepted

## Decision

- The assistant answers questions by calling deterministic query functions (find sessions,
  free rooms, explain a placement, compare solutions, list changes between versions). The
  language model chooses functions and phrases the answer; every fact comes from function
  results, which are shown alongside the answer.
- It has no write access and no database handle.
- It is disabled until an administrator configures a provider and accepts the data-flow notice;
  every capability it offers is also available through the regular interface.
- Providers: Anthropic Messages API, or an OpenAI-compatible endpoint for self-hosted models.

## Consequences

- When the provider is unavailable the assistant reports that and nothing else degrades.
