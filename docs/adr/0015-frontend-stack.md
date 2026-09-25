# ADR 0015 — React SPA, own design system, i18n with right-to-left support

**Status:** Accepted

## Decision

- React + TypeScript + Vite single-page application, served as static files from the same
  origin as the API.
- TanStack Query for server state, TanStack Table for data grids, React Router, i18next.
- A small in-house design system (CSS custom properties, dense layouts) rather than a generic
  component kit; accessibility via native elements (`dialog`, `button`, form controls) and
  ARIA where needed. `@dnd-kit` for drag-and-drop in the timetable grid.
- English, French and Arabic from the first release; Arabic switches the document to `dir="rtl"`
  and all layout uses logical CSS properties.
- API types are generated from the OpenAPI document (`openapi-typescript`); CI fails if they
  are stale.
