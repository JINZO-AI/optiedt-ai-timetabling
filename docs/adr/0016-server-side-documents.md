# ADR 0016 — Server-side PDF (WeasyPrint), XLSX, and iCalendar feeds

**Status:** Accepted

## Decision

- PDFs are rendered on the server from Jinja2 HTML templates with WeasyPrint (CSS paged media,
  Pango/HarfBuzz shaping, correct Arabic). No headless browser in production images.
- XLSX with openpyxl; CSV with the standard library; iCalendar (RFC 5545) with dated occurrences
  that apply holidays, timing variants and exceptions.
- Large document batches (a booklet of all groups) are generated synchronously up to a size
  limit, measured in `docs/benchmarks/`.
