"""The examination session — FR-20, increment 2.

Parallel to `optiedt.solver`, never a widening of it. The two share the domain
and nothing else: an examination occupies **one or more rooms** (R-6, SRS §6.8)
and is indexed over the days of the examination period rather than the week, so
a shared variable schema would mean forcing one of the two models into a shape
that does not fit it.

Two modules:

- `derive`  — builds an `ExamSession` from an `Instance`. Examinations are
  DERIVED, never supplied: FR-20 names them among its inputs and SRS Table 25
  defines no Examination entity, so the rule is a project decision (C-23,
  ADR-013).
- `solver`  — the CP-SAT model of SRS §6.8: X1-X4 hard, SX1 soft.

⚠️ `optiedt.api` may not import this package directly, exactly as it may not
import `optiedt.solver`; the sanctioned path is through `optiedt.services`. A
solve inside a request handler is what ADR-005 and the run lifecycle exist to
prevent.
"""
