"""ITC-2007 Track 3 — curriculum-based course timetabling.

Five modules, in dependency order:

| Module | Role |
|---|---|
| `problem.py` | The ITC-2007 entities. Nothing in common with `optiedt.domain` |
| `reader.py` | `.ctt` instances and `.sol` solutions, token-based |
| `cost.py` | The four hard constraints and the four soft costs |
| `model.py` | The CP-SAT encoding, and the solve |
| `published.py` | Competition results, transcribed with their citation |
| `runner.py` | Solve → evaluate → compare → report |

⚠️ **This is a SEPARATE model of a DIFFERENT problem, not `optiedt.solver` run on
foreign data**, and the report must say so. ITC-2007 has room capacities where
OptiEDT has room *types*, curricula where OptiEDT has a promotion → TD → TP
hierarchy, per-course lecture counts and minimum working days where OptiEDT has
individual sessions, and four soft costs none of which is one of S2-S10. Forcing
the reference instance's schema onto it would validate the adapter, not the
engine — and a plausible claim nobody tried to falsify is exactly what cost this
project three sessions on C-13.

**What is therefore genuinely validated**: the modelling approach (ADR-001,
CP-SAT for assignment), the solve configuration established in ADR-011
(deterministic budget, `interleave_search`, fixed seed), and the methodology of
re-deriving every constraint independently from the raw data instead of trusting
the solver's own status. **What is not**: `optiedt.solver`'s H1-H12 code paths.
State both when quoting a result.
"""

from __future__ import annotations
